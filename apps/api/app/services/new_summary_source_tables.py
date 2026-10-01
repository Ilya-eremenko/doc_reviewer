from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.document import Document


_YEAR = re.compile(r"20\d{2}")
_TOTAL_RANGE = re.compile(
    r"(?P<start>20\d{2})\s*[-–—]\s*(?P<end>(?:20)?\d{2})\s*(?:total|ttl|итого)",
    re.IGNORECASE,
)
_TOBE = re.compile(r"\btobe\b", re.IGNORECASE)
_REVENUE = re.compile(r"(?:revenue|выручк[а-я]*)", re.IGNORECASE)


@dataclass(frozen=True)
class VerifiedRevenueTotal:
    value: str
    source_block_id: str | None
    source_page: int | None


def verified_table_blocks(document: Document) -> list[dict[str, Any]]:
    """Return structured tables only when the artifact still matches the owned document."""
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
    blocks = artifact.get("blocks")
    return [block for block in blocks if isinstance(block, dict) and block.get("type") == "table"] if isinstance(blocks, list) else []


def block_rows(block: dict[str, Any]) -> list[list[str]]:
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


def verified_revenue_total(
    periods: list[str], values: list[str], blocks: list[dict[str, Any]],
) -> VerifiedRevenueTotal | None:
    """Borrow an explicit ToBe P&L Total only when every full-year Revenue value matches."""
    source_years = {
        int(period.strip()): _number(values[index])
        for index, period in enumerate(periods)
        if isinstance(period, str) and _YEAR.fullmatch(period.strip()) and index < len(values)
    }
    if len(source_years) < 2 or any(value is None for value in source_years.values()):
        return None
    years = sorted(source_years)
    if years != list(range(years[0], years[-1] + 1)):
        return None

    matches: list[VerifiedRevenueTotal] = []
    for block in blocks:
        rows = block_rows(block)
        for header_index, header in enumerate(rows):
            if not header or not _TOBE.search(header[0]):
                continue
            candidate_years = {
                int(cell.strip()): index for index, cell in enumerate(header)
                if _YEAR.fullmatch(cell.strip())
            }
            if not all(year in candidate_years for year in years):
                continue
            for total_index, total_period in enumerate(header):
                total_range = _total_range(total_period)
                if total_range != (years[0], years[-1]):
                    continue
                for row in rows[header_index + 1:]:
                    if not row or not _REVENUE.fullmatch(row[0].strip()):
                        continue
                    if total_index >= len(row) or _number(row[total_index]) is None:
                        continue
                    if all(
                        candidate_years[year] < len(row)
                        and _number(row[candidate_years[year]]) == source_years[year]
                        for year in years
                    ):
                        matches.append(VerifiedRevenueTotal(
                            value=row[total_index].strip(),
                            source_block_id=block.get("id") if isinstance(block.get("id"), str) else None,
                            source_page=block.get("page") if isinstance(block.get("page"), int) else None,
                        ))
    if not matches or len({_number(match.value) for match in matches}) != 1:
        return None
    return matches[0]


def _total_range(value: str) -> tuple[int, int] | None:
    match = _TOTAL_RANGE.search(value)
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end"))
    return start, end if end >= 100 else (start // 100) * 100 + end


def _number(value: Any) -> Decimal | None:
    cleaned = str(value or "").strip().replace("\u00a0", "").replace(" ", "").replace("−", "-").replace(",", ".")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
