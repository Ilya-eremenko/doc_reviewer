import json
from pathlib import Path

from jsonschema import ValidationError, validate


SCHEMAS = Path(__file__).resolve().parents[3] / "contracts" / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_gate_and_localization_contracts_accept_yellow_and_reject_unknown_status():
    schemas = [
        _schema("main-analysis-result.schema.json")["$defs"]["stage_checklist_item"],
        _schema("main-analysis-summary-result.schema.json")["$defs"]["stage_checklist_item"],
        _schema("summary-localization.schema.json")["properties"]["stage_checklist"]["items"],
    ]
    for schema in schemas:
        item = {"id": "check", "label": "Required item", "status": "yellow", "evidence": "Only planned."}
        validate(item, schema)
        item["status"] = "unknown"
        try:
            validate(item, schema)
        except ValidationError:
            continue
        raise AssertionError("Unknown checklist status passed validation")


def test_ai_summary_contract_accepts_three_statuses_and_hypothesis_fraction():
    schema = _schema("new-summary.schema.json")["$defs"]["required_element"]
    item = {
        "id": "gate2_hypothesis_results",
        "label": "Hypothesis results",
        "status": "есть",
        "evidence": "Two validated hypotheses.",
    }
    for status in ("есть", "частично подтверждено", "нет", "2/5"):
        item["status"] = status
        validate(item, schema)
    item["status"] = "yellow"
    try:
        validate(item, schema)
    except ValidationError:
        return
    raise AssertionError("Raw Gate status must not be stored as an AI Summary status")
