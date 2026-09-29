from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.document import Document


_PERIOD = re.compile(r"(?:^|\b)(?:20\d{2}|CY\s*['’]?\d{2}|Q[1-4])(?:\b|$)", re.IGNORECASE)
_TOTAL = re.compile(r"\b(?:total|ttl|итого|всего)\b", re.IGNORECASE)
_INCREMENT = re.compile(r"\b(?:increment(?:al)?|incr\.?|uplift|прирост|инкремент)\b", re.IGNORECASE)
_EXCLUDED = re.compile(r"\b(?:tobe|to.be|baseline|before|previous|prior|historical|alternative|illustrative|maximum|diff|delta|разниц|до\s+изменен|предыдущ|прошл|альтернативн|иллюстративн)\w*\b", re.IGNORECASE)
_METRICS = {"revenue": re.compile(r"\b(?:revenue|выручк[а-я]*)\b", re.IGNORECASE), "dtb": re.compile(r"\bDTB\b", re.IGNORECASE)}


def source_traction_tables(document: Document) -> list[dict[str, Any]]:
    """Read only the parsed artifact owned by this document; never infer missing figures."""
    from app.core.config import get_settings
    from app.storage.local import LocalDocumentStorage
    path = LocalDocumentStorage(get_settings().storage_root).parsed_artifact_dir(
        owner_id=document.owner_id, document_id=document.id
    ) / "structured.json"
    if not path.is_file():
        return []
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(artifact, dict) or not isinstance(document.parsed_text, str):
        return []
    if (artifact.get("source") or {}).get("sha256") != document.file_hash_sha256:
        return []
    text_hash = hashlib.sha256(document.parsed_text.encode("utf-8")).hexdigest()
    if (artifact.get("outputs") or {}).get("plain_text_sha256") != text_hash:
        return []

    best: dict[str, tuple[int, dict[str, Any]]] = {}
    ambiguous: set[str] = set()
    for block in artifact.get("blocks") or []:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        rows = _block_rows(block)
        if not rows:
            continue
        for score, table in _incremental_rows(rows):
            metric = table["metric"]
            candidate = {
                **table,
                "source_page": block.get("page"),
                "source_block_id": block.get("id"),
                "source_block_hash": block.get("hash"),
            }
            if metric not in best or score > best[metric][0]:
                best[metric] = (score, candidate)
                ambiguous.discard(metric)
            elif score == best[metric][0]:
                selected = best[metric][1]
                if selected["source_block_id"] == block.get("id") and selected["periods"] == table["periods"]:
                    for row in table["rows"]:
                        if any(existing["label"] == row["label"] and existing["values"] != row["values"]
                               for existing in selected["rows"]):
                            ambiguous.add(metric)
                            continue
                        if row not in selected["rows"]:
                            selected["rows"].append(row)
                else:
                    ambiguous.add(metric)
    return [best[metric][1] for metric in ("revenue", "dtb") if metric in best and metric not in ambiguous]


def _block_rows(block: dict[str, Any]) -> list[list[str]]:
    metadata = block.get("metadata") or {}
    rows = metadata.get("rows") if isinstance(metadata, dict) else None
    if isinstance(rows, list) and all(isinstance(row, list) for row in rows):
        return [[str(cell or "").strip() for cell in row] for row in rows]
    markdown = block.get("markdown")
    if not isinstance(markdown, str):
        return []
    parsed: list[list[str]] = []
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().replace("<br>", " ") for cell in re.split(r"(?<!\\)\|", line.strip("|"))]
        if cells and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue
        parsed.append([cell.replace(r"\|", "|") for cell in cells])
    return parsed


def _incremental_rows(rows: list[list[str]]) -> list[tuple[int, dict[str, Any]]]:
    found: list[tuple[int, dict[str, Any]]] = []
    active_header: list[str] = []
    active_context = ""
    header_row_index = -1
    for row_index, row in enumerate(rows):
        if not row:
            continue
        first = row[0].strip()
        if not first:
            continue
        period_cells = [i for i, cell in enumerate(row[1:], 1) if _PERIOD.search(cell) or _TOTAL.search(cell)]
        if len(period_cells) >= 2:
            active_header = row
            active_context = first
            header_row_index = row_index
            continue
        if not active_header or _EXCLUDED.search(active_context):
            continue
        context_incremental = bool(_INCREMENT.search(active_context))
        row_incremental = bool(_INCREMENT.search(first))
        if not (context_incremental or row_incremental):
            continue
        if _EXCLUDED.search(first):
            continue
        metric = next((name for name, pattern in _METRICS.items() if pattern.search(first)), None)
        if metric is None:
            metric = next((name for name, pattern in _METRICS.items() if pattern.search(active_context)), None)
            if metric is None or not _TOTAL.search(first):
                continue
        indices = [i for i, cell in enumerate(active_header[1:], 1) if _PERIOD.search(cell) or _TOTAL.search(cell)]
        if len(indices) < 2:
            continue
        values = [row[i].strip() if i < len(row) else "" for i in indices]
        if not any(values):
            continue
        periods = [active_header[i].strip() for i in indices]
        score = 10 if context_incremental else 5
        if _TOTAL.search(first):
            score += 3
        if "p&l" in active_context.lower():
            score += 3
        if re.search(r"20\d{2}\s*[-–]\s*(?:20)?\d{2}\s*(?:total|ttl)", " ".join(periods), re.IGNORECASE):
            score += 1
        found.append((score, {
            "metric": metric,
            "metric_label": metric.upper() if metric == "dtb" else "Revenue",
            "unit": _unit(active_context, first),
            "source_header_text": active_context,
            "periods": periods,
            "rows": [{
                "label": "Total incremental output uplifts" if _TOTAL.search(first) or first.lower() in {"revenue", "dtb"} else first,
                "values": values,
                "source_row_label": first,
                "source_row_index": row_index,
                "source_header_row_index": header_row_index,
                "source_column_indices": indices,
            }],
        }))
    return found


def _unit(context: str, label: str) -> str:
    text = f"{context} {label}"
    if re.search(r"\b(?:mR|млн\s*₽)\b", text, re.IGNORECASE):
        return "млн ₽"
    if "%" in text:
        return "%"
    return ""


def display_traction_tables(source_tables: list[dict[str, Any]], *, language: str) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    for source in source_tables:
        metric = source["metric"]
        unit = source.get("unit") or ""
        name = "DTB" if metric == "dtb" else ("Выручка" if language == "ru" else "Revenue")
        metric_label = f"{name} (инкр.)" if language == "ru" else f"{name} (incr)"
        if unit:
            metric_label += f", {unit if language == 'ru' else ('mR' if unit == 'млн ₽' else unit)}"
        tables.append({
            "metric": metric,
            "metric_label": metric_label,
            "periods": source["periods"],
            "rows": [{
                "label": (
                    "Итоговый инкрементальный прирост" if language == "ru" else "Total incremental output uplifts"
                ) if row["label"] == "Total incremental output uplifts" else row["label"],
                "values": row["values"],
            } for row in source["rows"]],
        })
    return {"tables": tables}
