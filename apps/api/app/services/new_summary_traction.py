from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.services.new_summary_source_tables import verified_revenue_total


_TOTAL_PERIOD = re.compile(r"\b(?:total|ttl|итого|всего)\b", re.IGNORECASE)
_YEAR = re.compile(r"\b20\d{2}\b")
_REVENUE_LABEL = re.compile(r"\b(?:revenue|выручк[а-я]*)\b", re.IGNORECASE)


def _table_metric(table: dict[str, Any]) -> str | None:
    metric = table.get("metric")
    if metric in {"revenue", "dtb"}:
        return metric
    label = table.get("metric_label")
    if metric is None and isinstance(label, str) and _REVENUE_LABEL.search(label) and "dtb" not in label.lower():
        return "revenue"
    return None


def needs_verified_revenue_total(payload: dict[str, Any]) -> bool:
    summary = payload.get("traction_summary")
    if not isinstance(summary, dict):
        return False
    tables = summary.get("tables") if isinstance(summary.get("tables"), list) else [summary]
    for table in tables:
        if not isinstance(table, dict) or _table_metric(table) != "revenue":
            continue
        periods = table.get("periods")
        if not isinstance(periods, list):
            continue
        index = next((i for i, period in enumerate(periods) if isinstance(period, str) and _TOTAL_PERIOD.search(period)), None)
        if index is None:
            return True
        if any(
            isinstance(row, dict)
            and isinstance(row.get("values"), list)
            and (index >= len(row["values"]) or _missing_total(row["values"][index]))
            for row in table.get("rows") or []
        ):
            return True
    return False


def with_traction_totals(
    payload: dict[str, Any], *, source_tables: list[dict[str, Any]] | None = None,
    source_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fill only missing Total cells; never calculate a total from period values."""
    summary = payload.get("traction_summary")
    if not isinstance(summary, dict):
        return payload
    tables = summary.get("tables") if isinstance(summary.get("tables"), list) else [summary]
    language = payload.get("language")
    absent = "отсутствуют данные в документе защиты" if language == "ru" else "no data in the defense document"
    unavailable = "невозможно извлечь данные" if language == "ru" else "could not extract data"
    updated = deepcopy(payload)
    updated_tables = []
    for table in tables:
        if not isinstance(table, dict):
            updated_tables.append(table)
            continue
        periods = table.get("periods")
        rows = table.get("rows")
        if not isinstance(periods, list) or not periods or not isinstance(rows, list) or not rows:
            updated_tables.append(table)
            continue
        metric = _table_metric(table)
        total_index = next(
            (index for index, period in enumerate(periods)
             if isinstance(period, str) and _TOTAL_PERIOD.search(period)), None
        )
        source_periods_without_total = [
            period for period in periods if not isinstance(period, str) or not _TOTAL_PERIOD.search(period)
        ]
        matching_source = next(
            (
                source for source in source_tables or []
                if isinstance(source, dict)
                and source.get("metric") == metric
                and source.get("periods") in (periods, source_periods_without_total)
            ), None
        ) if metric in {"revenue", "dtb"} else None
        if total_index is not None:
            amended = deepcopy(table)
            if total_index != len(periods) - 1:
                total_period = amended["periods"].pop(total_index)
                amended["periods"].append(total_period)
            for row in amended["rows"]:
                values = row.get("values") if isinstance(row, dict) else None
                if not isinstance(values, list):
                    continue
                if total_index >= len(values):
                    values.extend([unavailable] * (total_index + 1 - len(values)))
                if _missing_total(values[total_index]):
                    verified = verified_revenue_total(periods, values, source_blocks or []) if metric == "revenue" else None
                    values[total_index] = verified.value if verified else (absent if matching_source is not None else unavailable)
                if total_index != len(periods) - 1:
                    total_value = values.pop(total_index)
                    values.append(total_value)
            updated_tables.append(amended)
            continue
        missing_reason = absent if matching_source is not None else unavailable
        years = [year for period in periods if isinstance(period, str) for year in _YEAR.findall(period)]
        label = f"Total {years[0]}–{years[-1]}" if len(years) > 1 else "Total"
        amended = deepcopy(table)
        amended["periods"].append(label)
        for row in amended["rows"]:
            if isinstance(row, dict) and isinstance(row.get("values"), list):
                verified = verified_revenue_total(periods, row["values"], source_blocks or []) if metric == "revenue" else None
                row["values"].append(verified.value if verified else missing_reason)
        updated_tables.append(amended)
    updated["traction_summary"] = {**summary, "tables": updated_tables} if "tables" in summary else updated_tables[0]
    return updated


def _missing_total(value: Any) -> bool:
    return not str(value or "").strip() or str(value).strip().casefold() in {
        "отсутствуют данные в документе защиты",
        "невозможно извлечь данные",
        "no data in the defense document",
        "could not extract data",
        "не смог получить данные",
        "нет данных в документе",
        "no data in the document",
    }
