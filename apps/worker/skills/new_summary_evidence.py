from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from jsonschema import validate

from skills.context_relevance import decision_context_score
from skills.traction_tables import display_traction_tables


_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_STRUCTURAL_NUMBER = re.compile(r"\b(?:Gate|Гейт|Stream Review|Progress Review|FAQ|Appendix|Приложение)\s*\d+\+?\b", re.IGNORECASE)
_NARRATIVE_LISTS = ("confirmed", "insufficiently_confirmed", "critical_problems", "other")


def ground_new_summary_numbers(
    *,
    report: dict[str, Any],
    source_text: str,
    source_file_sha256: str,
    source_tables: list[dict[str, Any]],
    source_checklist: list[dict[str, Any]] | None = None,
    response_schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fail closed for numeric prose; source tables are already hash-checked by their loader."""
    result = deepcopy(report)
    parsed_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    evidence: list[dict[str, Any]] = []
    suppressed: list[dict[str, str]] = []
    for version_index, version in enumerate(result["versions"]):
        language = version["language"]
        prefix = f"versions[{version_index}]"
        version["context"] = _ground_paragraph(
            version["context"], f"{prefix}.context", source_text, evidence, suppressed, language
        )
        for name in _NARRATIVE_LISTS:
            retained = []
            for index, item in enumerate(version[name]):
                path = f"{prefix}.{name}[{index}]"
                if _verify_numbered_quote(item, path, source_text, evidence, suppressed):
                    retained.append(item)
            version[name] = retained
        for index, item in enumerate(version["required_elements"]):
            item["evidence"] = _ground_paragraph(
                item["evidence"], f"{prefix}.required_elements[{index}].evidence",
                source_text, evidence, suppressed, language,
            )
        for item_id, detail in list(version.get("required_details", {}).items()):
            path = f"{prefix}.required_details.{item_id}"
            detail_evidence: list[dict[str, Any]] = []
            if not _verify_detail(detail, path, source_text, detail_evidence, suppressed):
                del version["required_details"][item_id]
                for item in version["required_elements"]:
                    if item.get("id") == item_id:
                        item["evidence"] = (
                            "Детали не показаны: числовые значения не подтверждены исходным документом."
                            if language == "ru" else
                            "Details are omitted because numeric values are not verified against the source document."
                        )
            else:
                evidence.extend(detail_evidence)
        for index, item in enumerate(version["required_elements"]):
            status = item.get("status", "")
            if not isinstance(status, str) or not re.fullmatch(r"\d+/\d+", status):
                continue
            path = f"{prefix}.required_elements[{index}].status"
            detail = version.get("required_details", {}).get(item.get("id"))
            entries = detail.get("items") if isinstance(detail, dict) and detail.get("type") == "solution_validation" else None
            if isinstance(entries, list) and entries:
                numerator = sum(entry.get("verdict") == "confirmed" for entry in entries)
                item["status"] = f"{numerator}/{len(entries)}"
                evidence.append({"path": path, "kind": "derived_from_model_detail",
                                 "input_path": f"{prefix}.required_details.{item['id']}.items",
                                 "formula": "count(confirmed)/count(all)"})
            else:
                gate_item = next((entry for entry in source_checklist or [] if entry.get("id") == item.get("id")), {})
                gate_status = str(gate_item.get("status") or "").lower()
                item["status"] = {
                    "green": "есть", "present": "есть", "yellow": "частично подтверждено",
                    "partial": "частично подтверждено",
                }.get(gate_status, "нет")
                suppressed.append({"path": path, "reason": "fraction_without_verifiable_detail_count"})

        trusted_tables = [
            table for table in source_tables
            if isinstance(table, dict) and table.get("source_block_id")
            and all(row.get("source_row_index") is not None and row.get("source_column_indices")
                    for row in table.get("rows", []))
        ]
        if len(trusted_tables) != len(source_tables):
            suppressed.append({"path": f"{prefix}.traction_summary", "reason": "table_cell_coordinates_missing"})
        if not trusted_tables or len(trusted_tables) != len(source_tables):
            version["traction_summary"] = {"tables": []}
        else:
            version["traction_summary"] = display_traction_tables(trusted_tables, language=language)
            for table_index, table in enumerate(trusted_tables):
                for row_index, row in enumerate(table["rows"]):
                    for period_index, value in enumerate(row["values"]):
                        if not value:
                            continue
                        columns = row.get("source_column_indices") or []
                        evidence.append({
                            "path": f"{prefix}.traction_summary.tables[{table_index}].rows[{row_index}].values[{period_index}]",
                            "kind": "parsed_table_cell",
                            "metric": table["metric"],
                            "period": table["periods"][period_index],
                            "source_page": table.get("source_page"),
                            "source_block_id": table.get("source_block_id"),
                            "source_block_hash": table.get("source_block_hash"),
                            "source_header_text": table.get("source_header_text"),
                            "source_row_label": row.get("source_row_label"),
                            "source_row_index": row.get("source_row_index"),
                            "source_header_row_index": row.get("source_header_row_index"),
                            "source_column_index": columns[period_index] if period_index < len(columns) else None,
                            "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                        })
    validate(instance=result, schema=response_schema)
    return result, {
        "version": 1,
        "source_file_sha256": source_file_sha256,
        "parsed_text_sha256": parsed_sha256,
        "verified": evidence,
        "suppressed": suppressed,
    }


def _ground_paragraph(
    value: str,
    path: str,
    source_text: str,
    evidence: list[dict[str, Any]],
    suppressed: list[dict[str, str]],
    language: str,
) -> str:
    sentences = _SENTENCE_BREAK.split(value)
    retained = [
        sentence for index, sentence in enumerate(sentences)
        if _verify_numbered_quote(sentence, f"{path}.sentence[{index}]", source_text, evidence, suppressed)
    ]
    result = " ".join(retained).strip()
    if result:
        return result
    return (
        "Числовое утверждение не подтверждено исходным документом."
        if language == "ru" else "The numeric claim is not verified against the source document."
    )


def _verify_detail(
    value: Any,
    path: str,
    source_text: str,
    evidence: list[dict[str, Any]],
    suppressed: list[dict[str, str]],
) -> bool:
    if isinstance(value, dict):
        return all(_verify_detail(item, f"{path}.{key}", source_text, evidence, suppressed)
                   for key, item in value.items() if key not in {"type", "verdict", "binding"})
    if isinstance(value, list):
        return all(_verify_detail(item, f"{path}[{index}]", source_text, evidence, suppressed)
                   for index, item in enumerate(value))
    if isinstance(value, str):
        return _verify_numbered_quote(value, path, source_text, evidence, suppressed)
    return True


def _verify_numbered_quote(
    value: str,
    path: str,
    source_text: str,
    evidence: list[dict[str, Any]],
    suppressed: list[dict[str, str]],
) -> bool:
    has_number = bool(re.search(r"\d", _STRUCTURAL_NUMBER.sub("", value)))
    if not has_number and len(value.strip()) < 24:
        return True
    words = re.split(r"\s+", value.strip())
    pattern = re.compile(
        r"(?<!\d)" + r"\s+".join(re.escape(word) for word in words) + r"(?!\d|[.,]\d)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(source_text)) if words else []
    if len(matches) == 1:
        match = matches[0]
        line_start = source_text.rfind("\n", 0, match.start()) + 1
        line_end = source_text.find("\n", match.end())
        context = source_text[line_start:line_end if line_end >= 0 else len(source_text)]
        if decision_context_score(context) >= 0:
            evidence.append({
                "path": path,
                "kind": "exact_source_quote",
                "source_start": match.start(),
                "source_end": match.end(),
                "claim_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            })
            return True
    if has_number:
        suppressed.append({"path": path, "reason": "numeric_claim_without_unique_current_source_quote"})
        return False
    return True
