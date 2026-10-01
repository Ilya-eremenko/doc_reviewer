from __future__ import annotations

import re
from typing import Any


_FRACTION = re.compile(r"^(\d+)\s*/\s*(\d+)$")
_PRESENT = {"есть", "present"}
_PARTIAL = {"частично подтверждено", "partially confirmed"}


def document_quality_percent(payload: dict[str, Any]) -> int | None:
    """Score the final checklist, counting rated children instead of their parent."""
    elements = payload.get("required_elements")
    if not isinstance(elements, list):
        return None
    legacy_details = payload.get("required_details")
    legacy_details = legacy_details if isinstance(legacy_details, dict) else {}
    earned = maximum = 0
    for element in elements:
        if not isinstance(element, dict):
            continue
        detail = element.get("detail") or legacy_details.get(element.get("id"))
        child_scores = _rated_children(detail)
        if child_scores:
            earned += sum(child_scores)
            maximum += len(child_scores)
            continue
        status = str(element.get("status") or "").strip().lower()
        fraction = _FRACTION.fullmatch(status)
        if fraction and int(fraction.group(2)) > 0:
            earned += min(int(fraction.group(1)), int(fraction.group(2)))
            maximum += int(fraction.group(2))
        else:
            earned += 2 if status in _PRESENT else 1 if status in _PARTIAL else 0
            maximum += 2
    if maximum == 0:
        return None
    return (200 * earned + maximum) // (2 * maximum)


def with_document_quality(payload: dict[str, Any], *, recompute: bool = False) -> dict[str, Any]:
    existing = payload.get("document_quality_percent")
    if not recompute and isinstance(existing, int) and not isinstance(existing, bool) and 0 <= existing <= 100:
        return payload
    percent = document_quality_percent(payload)
    if percent is None:
        return payload
    return {**payload, "document_quality_percent": percent}


def with_bilingual_document_quality(
    ru_payload: dict[str, Any], en_payload: dict[str, Any], *, recompute: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ru = with_document_quality(ru_payload, recompute=recompute)
    en = with_document_quality(en_payload, recompute=recompute)
    percent = ru.get("document_quality_percent")
    if not isinstance(percent, int) or isinstance(percent, bool):
        percent = en.get("document_quality_percent")
    if not isinstance(percent, int) or isinstance(percent, bool):
        return ru, en
    return {**ru, "document_quality_percent": percent}, {**en, "document_quality_percent": percent}


def _rated_children(detail: Any) -> list[int]:
    if not isinstance(detail, dict):
        return []
    if detail.get("type") == "solution_validation":
        items = detail.get("items")
        if isinstance(items, list):
            return [int(item["verdict"] == "confirmed") for item in items
                    if isinstance(item, dict) and item.get("verdict") in {"confirmed", "insufficient"}]
    if detail.get("type") == "metric_binding":
        scores: list[int] = []
        for key in ("input_metrics", "output_metrics"):
            items = detail.get(key)
            if isinstance(items, list):
                scores.extend(int(item["binding"] == "confirmed") for item in items
                              if isinstance(item, dict) and item.get("binding") in {"confirmed", "insufficient"})
        return scores
    return []
