import pytest
from jsonschema import validate

from skills.new_summary_generation import (
    _new_summary_schema, _normalized_required_detail, _required_element_status,
    _required_elements_from_source, _verified_source_links,
)


@pytest.mark.parametrize("detail", [
    {"type": "plan_fact", "launches": [{"output": "Pilot", "status": "partial", "comment": "One region."}],
     "metrics": [{"metric": "Users", "planned": "100", "actual": "80"}]},
    {"type": "source_links", "availability": "provided", "links": [{"label": "Mockup", "url": "https://example.com/prototype"}]},
    {"type": "stop_criteria", "criteria": []},
])
def test_new_details_survive_normalization_and_validate(detail):
    normalized = _normalized_required_detail(detail)
    assert normalized == detail
    schema = _new_summary_schema()
    validate(normalized, {"$ref": "#/$defs/required_detail", "$defs": schema["$defs"]})


def test_mockup_links_are_exact_source_urls_not_model_inventions():
    source = {"source_document": {"parsed_text_excerpt": "Mockup [View](https://example.com/design?a=1&b=2)."}}
    detail = {"type": "source_links", "availability": "provided", "links": [
        {"label": "Actual", "url": "https://example.com/design?a=1&b=2"},
        {"label": "Invented", "url": "https://example.com/other"},
        {"label": "Prefix", "url": "https://example.com/design"},
        {"label": "Script", "url": "javascript:alert(1)"},
    ]}
    normalized = _normalized_required_detail(detail)
    result = _verified_source_links(normalized, source)
    assert result["links"] == [detail["links"][0]]
    assert result["availability"] == "provided"
    assert _verified_source_links(normalized, {})["availability"] == "unavailable"
    assert _verified_source_links({"links": [], "availability": "absent"}, source)["availability"] == "absent"


def test_empty_hypotheses_do_not_reuse_a_stale_fraction_or_green_checklist():
    for document_type, item_id in (("gate_2", "gate2_hypothesis_results"), ("stream_review_1", "stream_review_1_solution_validation")):
        for language in ("ru", "en"):
            elements = _required_elements_from_source(
                source_payload={"document_type": document_type, "gate_challenger": {"stage_checklist": [{"id": item_id, "status": "green"}]}},
                target_language=language,
                generated_payload={"required_elements": [{"id": item_id, "status": "3/3"}]}, required_details={},
            )
            element = next(item for item in elements if item["id"] == item_id)
            assert element["status"] == "нет"
            assert element["evidence"].startswith("В кейсе не найдена информация" if language == "ru" else "No information")
            assert "detail" not in element


def test_single_stop_criterion_in_evidence_does_not_need_a_duplicate_list():
    for generated_status, expected in (("есть", "есть"), ("частично подтверждено", "частично подтверждено")):
        assert _required_element_status(
            {"status": "red"}, item_id="progress_review_stop_criteria",
            generated_item={"status": generated_status, "evidence": "Stop if the pilot exceeds the cost limit."},
            required_details={},
        ) == expected


def test_validation_counts_deduplicate_exact_hypotheses_and_remove_old_detail_fields():
    normalized = _normalized_required_detail({"type": "solution_validation", "items": [
        {"text": "Pilot", "verdict": "confirmed", "test": "Legacy detail"},
        {"text": " pilot ", "verdict": "confirmed"},
        {"text": "Rollout", "verdict": "insufficient"},
    ]})
    assert normalized["items"] == [{"text": "Pilot", "verdict": "confirmed"}, {"text": "Rollout", "verdict": "insufficient"}]
    assert _required_element_status(
        None, item_id="gate2_hypothesis_results", generated_item={},
        required_details={"gate2_hypothesis_results": normalized},
    ) == "1/2"
