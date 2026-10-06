from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.services.new_summary_source_tables import (
    block_rows as _block_rows,
    verified_revenue_total,
    verified_table_blocks,
)

if TYPE_CHECKING:
    from app.models.document import Document


_PERIOD = re.compile(r"(?:^|\b)(?:20\d{2}|CY\s*['’]?\d{2}|Q[1-4])(?:\b|$)", re.IGNORECASE)
_TOTAL = re.compile(r"\b(?:total|ttl|итого|всего)\b", re.IGNORECASE)
_INCREMENT = re.compile(r"\b(?:increment(?:al)?|incr\.?|uplift|прирост|инкремент)\b", re.IGNORECASE)
_EXCLUDED = re.compile(r"\b(?:tobe|to.be|baseline|before|previous|prior|diff|delta|разниц|до\s+изменен)\b", re.IGNORECASE)
_METRICS = {"revenue": re.compile(r"\b(?:revenue|выручк[а-я]*)\b", re.IGNORECASE), "dtb": re.compile(r"\bDTB\b", re.IGNORECASE)}


def source_traction_tables(document: Document) -> list[dict[str, Any]]:
    """Read only the parsed artifact owned by this document; never infer missing figures."""
    blocks = verified_table_blocks(document)
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for block in blocks:
        rows = _block_rows(block)
        if not rows:
            continue
        for score, table in _incremental_rows(rows):
            metric = table["metric"]
            candidate = {
                **table,
                "source_page": block.get("page"),
                "source_block_id": block.get("id"),
            }
            if metric not in best or score > best[metric][0]:
                best[metric] = (score, candidate)
            elif score == best[metric][0]:
                selected = best[metric][1]
                if selected["source_block_id"] == block.get("id") and selected["periods"] == table["periods"]:
                    for row in table["rows"]:
                        if row not in selected["rows"]:
                            selected["rows"].append(row)
    tables = [best[metric][1] for metric in ("revenue", "dtb") if metric in best]
    for table in tables:
        if table["metric"] != "revenue":
            continue
        total_index = next((index for index, period in enumerate(table["periods"]) if _TOTAL.search(period)), None)
        if total_index is not None and all(
            total_index < len(row["values"]) and row["values"][total_index]
            for row in table["rows"]
        ):
            continue
        totals = [
            verified_revenue_total(table["periods"], row["values"], blocks)
            if total_index is None or total_index >= len(row["values"]) or not row["values"][total_index]
            else None
            for row in table["rows"]
        ]
        if not any(totals):
            continue
        if total_index is None:
            years = [period for period in table["periods"] if re.fullmatch(r"20\d{2}", period)]
            table["periods"].append(f"Total {years[0]}–{years[-1]}")
        for row, total in zip(table["rows"], totals, strict=True):
            if total_index is None:
                row["values"].append(total.value if total else "")
            elif total:
                row["values"][total_index] = total.value
        matched = next(total for total in totals if total is not None)
        table["total_source_block_id"] = matched.source_block_id
        table["total_source_page"] = matched.source_page
    return tables


def _incremental_rows(rows: list[list[str]]) -> list[tuple[int, dict[str, Any]]]:
    found: list[tuple[int, dict[str, Any]]] = []
    active_header: list[str] = []
    active_context = ""
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if not first:
            continue
        period_cells = [i for i, cell in enumerate(row[1:], 1) if _PERIOD.search(cell) or _TOTAL.search(cell)]
        if len(period_cells) >= 2:
            active_header = row
            active_context = first
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
        if any(_TOTAL.search(period) for period in periods):
            score += 2
        if "p&l" in active_context.lower():
            score += 3
        if re.search(r"20\d{2}\s*[-–]\s*(?:20)?\d{2}\s*(?:total|ttl)", " ".join(periods), re.IGNORECASE):
            score += 1
        found.append((score, {
            "metric": metric,
            **({"cumulative": True} if metric == "dtb" and re.search(r"\b(?:cum(?:ulative)?|накоплен\w*)\b", f"{active_context} {first}", re.IGNORECASE) else {}),
            "metric_label": metric.upper() if metric == "dtb" else "Revenue",
            "unit": _unit(active_context, first),
            "periods": periods,
            "rows": [{
                "label": "Total incremental output uplifts" if _TOTAL.search(first) or first.lower() in {"revenue", "dtb"} else first,
                "values": values,
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
            **({"cumulative": True} if source.get("cumulative") is True else {}),
            "metric_label": metric_label,
            "periods": source["periods"],
            "rows": [{
                "label": (
                    "Итоговый инкрементальный прирост" if language == "ru" else "Total incremental output uplifts"
                ) if row["label"] == "Total incremental output uplifts" else row["label"],
                "values": [
                    _display_source_cell(value, source["periods"][index], language=language)
                    for index, value in enumerate(row["values"])
                ],
            } for row in source["rows"]],
        })
    return {"tables": tables}


def _display_source_cell(value: str, period: str, *, language: str) -> str:
    if value:
        return value
    if _TOTAL.search(period):
        return "отсутствуют данные в документе защиты" if language == "ru" else "no data in the defense document"
    return "Нет данных в документе" if language == "ru" else "No data in the document"
