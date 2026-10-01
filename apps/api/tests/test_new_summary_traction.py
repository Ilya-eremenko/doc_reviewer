from copy import deepcopy

from app.services.new_summary_traction import needs_verified_revenue_total, with_traction_totals
from app.services.new_summary_exports import _confirmed_first, _gate2_hypothesis_heading, _labels
from app.services.new_summaries import with_verified_source_totals
from app.schemas.analyses import NewSummaryRead, NewSummaryVariantRead
from uuid import uuid4


def _payload(language: str = "ru") -> dict:
    return {
        "language": language,
        "traction_summary": {"tables": [
            {"metric": "revenue", "metric_label": "Revenue", "periods": ["2026", "2027"],
             "rows": [{"label": "Incremental revenue", "values": ["10", "20"]}]},
            {"metric": "dtb", "metric_label": "DTB", "periods": ["CY26", "CY27"],
             "rows": [{"label": "DTB uplift", "values": ["1%", "2%"]}]},
        ]},
    }


def test_missing_total_is_explicit_and_never_calculated():
    payload = _payload()
    original = deepcopy(payload)
    tables = with_traction_totals(payload)["traction_summary"]["tables"]
    assert tables[0]["periods"] == ["2026", "2027", "Total 2026–2027"]
    assert tables[0]["rows"][0]["values"] == ["10", "20", "невозможно извлечь данные"]
    assert tables[1]["periods"][-1] == "Total"
    assert payload == original


def test_verified_source_without_total_uses_document_absence_reason():
    payload = _payload()
    source = [{"metric": "revenue", "periods": ["2026", "2027"]}]
    tables = with_traction_totals(payload, source_tables=source)["traction_summary"]["tables"]
    assert tables[0]["rows"][0]["values"][-1] == "отсутствуют данные в документе защиты"
    assert tables[1]["rows"][0]["values"][-1] == "невозможно извлечь данные"


def test_existing_total_values_are_preserved_in_both_languages():
    for language in ("ru", "en"):
        payload = _payload(language)
        table = payload["traction_summary"]["tables"][0]
        table["periods"].append("2026–2027 total")
        table["rows"][0]["values"].append("17")
        result = with_traction_totals(payload)["traction_summary"]["tables"]
        assert result[0] == table
        assert len(result[0]["periods"]) == len(result[0]["rows"][0]["values"])
        assert result[1]["rows"][0]["values"][-1] == (
            "невозможно извлечь данные" if language == "ru" else "could not extract data"
        )


def test_existing_total_moves_to_last_column_with_matching_value():
    payload = _payload()
    table = payload["traction_summary"]["tables"][0]
    table["periods"] = ["2026", "Total", "2027"]
    table["rows"][0]["values"] = ["10", "30", "20"]
    result = with_traction_totals(payload)["traction_summary"]["tables"][0]
    assert result["periods"] == ["2026", "2027", "Total"]
    assert result["rows"][0]["values"] == ["10", "20", "30"]


def test_saved_summary_placeholder_is_enriched_only_by_verified_source_total():
    payload = _payload()
    table = payload["traction_summary"]["tables"][0]
    table["periods"].append("Total 2026–2027")
    table["rows"][0]["values"].append("невозможно извлечь данные")
    source = [{"id": "faq6", "metadata": {"rows": [
        ["ToBe P&L", "2026", "2027", "2026-27 total"],
        ["Revenue", "10", "20", "30"],
    ]}}]
    enriched = with_traction_totals(payload, source_blocks=source)
    assert enriched["traction_summary"]["tables"][0]["rows"][0]["values"][-1] == "30"
    assert payload["traction_summary"]["tables"][0]["rows"][0]["values"][-1] == "невозможно извлечь данные"
    source[0]["metadata"]["rows"][1][2] = "21"
    assert with_traction_totals(payload, source_blocks=source)["traction_summary"]["tables"][0]["rows"][0]["values"][-1] == "невозможно извлечь данные"


def test_old_bilingual_report_reads_verified_total_without_mutating_saved_payload(monkeypatch):
    import app.services.new_summaries as summaries

    source = [{"id": "faq6", "metadata": {"rows": [
        ["ToBe P&L", "2026", "2027", "2026-27 total"],
        ["Revenue", "10", "20", "30"],
    ]}}]
    monkeypatch.setattr(summaries, "verified_table_blocks", lambda _document: source)
    ru = _payload("ru")
    en = _payload("en")
    report = NewSummaryRead(
        analysis_id=uuid4(), ru=NewSummaryVariantRead(status="completed", payload=ru),
        en=NewSummaryVariantRead(status="completed", payload=en),
    )
    updated = with_verified_source_totals(report, object())
    for language in ("ru", "en"):
        assert getattr(updated, language).payload["traction_summary"]["tables"][0]["rows"][0]["values"][-1] == "30"
        assert getattr(report, language).payload["traction_summary"]["tables"][0]["periods"] == ["2026", "2027"]


def test_gate2_hypothesis_heading_uses_actual_items_and_confirmed_first():
    item = {"id": "gate2_hypothesis_results", "detail": {"type": "solution_validation", "items": [
        {"text": "a", "verdict": "insufficient"}, {"text": "b", "verdict": "confirmed"},
        {"text": "c", "verdict": "insufficient"},
    ]}}
    assert _gate2_hypothesis_heading(item, _labels("ru")) == (
        "Результаты проверки гипотез из Gate: 1 гипотез из 3 подтверждены, 2 гипотез из 3 недостаточно подтверждены."
    )
    assert [entry["text"] for entry in _confirmed_first(item["detail"]["items"], "verdict")] == ["b", "a", "c"]


def test_legacy_single_revenue_table_without_metric_can_receive_verified_total():
    payload = {"language": "ru", "traction_summary": {
        "metric_label": "Revenue (incr)", "periods": ["2026", "2027", "Total"],
        "rows": [{"label": "Revenue", "values": ["10", "20", "Не смог получить данные"]}],
    }}
    source = [{"metadata": {"rows": [
        ["ToBe P&L", "2026", "2027", "2026-27 total"], ["Revenue", "10", "20", "30"],
    ]}}]
    assert needs_verified_revenue_total(payload)
    assert with_traction_totals(payload, source_blocks=source)["traction_summary"]["rows"][0]["values"][-1] == "30"
