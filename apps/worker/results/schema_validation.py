import json
from pathlib import Path

from jsonschema import validate


def parse_and_validate_json_output(*, structured_text: str, schema_path: str) -> dict:
    payload = json.loads(structured_text)
    schema = json.loads(_resolve_schema_path(schema_path).read_text(encoding="utf-8"))
    validate(instance=payload, schema=schema)
    return payload


def _resolve_schema_path(schema_path: str) -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / schema_path
