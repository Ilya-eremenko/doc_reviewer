from copy import deepcopy

import pytest

from app.services.new_summary_traction import with_traction_totals
from skills.new_summary_generation import _new_summary_schema, _validated_source_dependent_report
from skills.traction_tables import _cumulative_dtb_rows, display_traction_tables


def test_new_rules_survive_bilingual_validation_without_changing_source():
    source = {"document_type": "gate_2", "document_stage": "Gate 2", "source_document": {
        "parsed_text_excerpt": "[Mockup](https://example.com/design)",
    }, "gate_challenger": {"stage_checklist": [
        {"id": "gate2_user_flow", "status": "red"}, {"id": "gate2_stop_criteria", "status": "red"},
    ]}}
    original = deepcopy(source)
    metric = {"metric": "Activation", "binding": "insufficient", "evidence": "Different objective."}
    report = {"versions": [{"language": language, "context": "Context.", "required_elements": [
        {"id": "gate2_metric_linkage", "detail": {"type": "metric_binding", "input_metrics": [
            metric, {**metric, "metric": " ACTIVATION. "},
            {"metric": "Conversion", "binding": "confirmed", "evidence": "Measures the objective."}],
            "output_metrics": [metric]}},
        {"id": "gate2_user_flow", "status": "нет", "detail": {"type": "source_links", "availability": "provided",
            "links": [{"label": "Mockup", "url": "https://example.com/design"}]}},
        {"id": "gate2_stop_criteria", "status": "частично подтверждено", "evidence": "Stop-loss after pilot failure. Wording is unclear.",
            "detail": {"type": "stop_criteria", "primary_criterion": "Stop after pilot failure",
                       "criteria": ["Stop after pilot failure.", "Stop if funding ends", "Stop if funding ends."]}},
    ]} for language in ("en", "ru")]}
    result = _validated_source_dependent_report(payload=report, source_payload=source, response_schema=_new_summary_schema())
    assert result["schema_version"] == "new-summary-v7"
    for version in result["versions"]:
        items = {item["id"]: item for item in version["required_elements"]}
        assert items["gate2_user_flow"]["status"] == "есть"
        assert items["gate2_stop_criteria"]["status"] == "есть"
        assert "stop-loss" not in items["gate2_stop_criteria"]["evidence"].lower()
        assert items["gate2_stop_criteria"]["detail"]["criteria"] == ["Stop if funding ends."]
        metrics = items["gate2_metric_linkage"]["detail"]
        assert [item["metric"] for item in metrics["input_metrics"]] == ["Conversion", "Activation"]
        assert metrics["output_metrics"] == []
    assert source == original


def test_unknown_source_link_cannot_confirm_mockup_and_missing_stops_stay_missing():
    result = _validated_source_dependent_report(payload={"versions": [{"required_elements": [{
        "id": "gate2_user_flow", "status": "есть", "detail": {"type": "source_links", "availability": "provided",
        "links": [{"label": "Invented", "url": "https://example.com/not-in-source"}]},
    }]}] * 2}, source_payload={"document_type": "gate_2", "document_stage": "Gate 2"}, response_schema=_new_summary_schema())
    for version in result["versions"]:
        items = {item["id"]: item for item in version["required_elements"]}
        assert items["gate2_user_flow"]["status"] == "нет"
        assert items["gate2_stop_criteria"]["status"] == "нет"


def test_cumulative_dtb_is_verified_without_changing_source_numbers_or_summing_total():
    rows = [["Output metrics, %", "2026", "2027", "2028", "Total"],
            ["DTB", "1,20%", "1,70%", "2,40%", "5,30%"],
            ["Incremental DTB", "1,20%", "0,50%", "0,70%", "2,40%"]]
    original = deepcopy(rows)
    candidates = _cumulative_dtb_rows(rows)
    assert len(candidates) == 1
    table = candidates[0][1]
    assert table["cumulative_basis"] == "verified_recurrence"
    for language in ("ru", "en"):
        content = with_traction_totals({"language": language, "traction_summary": display_traction_tables([table], language=language)})
        displayed = content["traction_summary"]["tables"][0]
        assert displayed["rows"][0]["values"] == ["1,20%", "1,70%", "2,40%", "—"]
        assert "cummul" in displayed["metric_label"]
    assert rows == original


@pytest.mark.parametrize("rows", [
    [["Output %", "2026", "2027", "2028"], ["DTB", "1%", "2%", "4%"], ["Incremental DTB", "1%", "1%", "1%"]],
    [["Previous scenario %", "2026", "2027"], ["DTB", "1%", "2%"], ["Incremental DTB", "1%", "1%"]],
    [["Output %", "2026", "2028"], ["DTB", "1%", "2%"], ["Incremental DTB", "1%", "1%"]],
    [["Output", "2026", "2027"], ["DTB", "1%", "2%"], ["Incremental DTB", "1", "1"]],
    [["Output %", "2026", "2027"], ["DTB A", "1%", "2%"], ["Incremental DTB B", "1%", "1%"]],
    [["Output %", "2026", "2027"], ["DTB", "1%", "2%"], ["Incremental DTB", "1%", "1%"], ["Incremental DTB", "1%", "2%"]],
    [["Output %", "2026", "2027"], ["DTB", "1%", "#REF!"], ["Incremental DTB", "1%", "1%"]],
])
def test_cumulative_dtb_rejects_mismatch_gaps_scenarios_units_and_ambiguity(rows):
    assert _cumulative_dtb_rows(rows) == []


def test_explicit_cumulative_dtb_needs_no_increment_row():
    tables = _cumulative_dtb_rows([["Output %", "CY26", "CY27"], ["DTB cumulative", "1%", "2%"]])
    assert tables[0][1]["cumulative_basis"] == "explicit"


def test_cumulative_header_does_not_relabel_incremental_row():
    tables = _cumulative_dtb_rows([["Cumulative output %", "2026", "2027"],
                                   ["DTB", "1%", "2%"], ["Incremental DTB", "1%", "1%"]])
    assert len(tables) == 1
    assert tables[0][1]["rows"][0]["values"] == ["1%", "2%"]


def test_source_revenue_does_not_replace_new_metric_rows():
    source = {"document_type": "gate_2", "document_stage": "Gate 2", "source_traction_tables": [
        {"metric": "revenue", "periods": ["2026", "2027", "Total"],
         "rows": [{"label": "Revenue", "values": ["10", "20", "30"]}]},
    ]}
    model_table = {"periods": ["2026", "2027", "Total"], "rows": [
        {"label": "DTB Uplift (Cumul)", "values": ["1%", "2%", "—"]},
        {"label": "Revenue from DTB", "values": ["4", "5", "9"]},
        {"label": "Revenue non-DTB", "values": ["6", "15", "21"]},
        {"label": "Total Revenue", "values": ["10", "20", "30"]},
    ]}
    payload = {"versions": [{"language": language, "traction_summary": model_table} for language in ("en", "ru")]}
    result = _validated_source_dependent_report(payload=payload, source_payload=source, response_schema=_new_summary_schema())
    for version in result["versions"]:
        table = version["traction_summary"]
        assert table["rows"][0]["values"] == ["1%", "2%", "—"]
        assert table["rows"][1]["values"] == ["4", "5", "9"]
