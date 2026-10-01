from copy import deepcopy

from app.services.new_summary_traction import with_traction_totals


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
