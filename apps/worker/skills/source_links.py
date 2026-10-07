from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from markdown_it import MarkdownIt


MAX_LINKS = 200
MAX_CATALOG_CHARS = 60000
_DESIGN = re.compile(r"mock[ -]?ups?|prototype|design|user.?flow|video|макет|мокап|прототип|дизайн|видео|\bMLP\b", re.I)


def safe_source_url(value: Any) -> bool:
    if not isinstance(value, str) or re.search(r"[\s<>\x00-\x1f]", value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def source_link_catalog(text: str, *, extra_links: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    """Keep link identity outside the model; include context, not fetched content."""
    lines = text.splitlines()
    links: dict[str, dict[str, str]] = {}
    parser = MarkdownIt("commonmark", {"linkify": True}).enable("linkify")
    # Do not percent-encode Unicode or otherwise rewrite the original destination.
    parser.normalizeLink = lambda url: url
    for token in parser.parse(text):
        if token.type != "inline" or not token.children:
            continue
        context = " ".join(lines[slice(*token.map)]) if token.map else token.content
        children = token.children
        for index, child in enumerate(children):
            if child.type != "link_open":
                continue
            url = child.attrGet("href")
            if not safe_source_url(url):
                continue
            label_parts = []
            for following in children[index + 1:]:
                if following.type == "link_close":
                    break
                if following.type in {"text", "code_inline"}:
                    label_parts.append(following.content)
            label = "".join(label_parts).strip() or "Source link"
            # Center on this link even in long paragraphs and table rows.
            position = context.find(url)
            if position < 0:
                position = max(0, context.find(label))
            excerpt = context[max(0, position - 160):position + len(url) + 160]
            candidate = {"label": label[:200], "url": url, "context": excerpt[:600]}
            if url not in links or (_DESIGN.search(excerpt) and not _DESIGN.search(links[url]["context"])):
                links[url] = candidate
    for item in extra_links or []:
        if safe_source_url(item.get("url")) and item["url"] not in links:
            links[item["url"]] = item
    # Prioritize potentially relevant links before applying the independent catalog budget.
    ordered = sorted(links.values(), key=lambda item: not bool(_DESIGN.search(item["label"] + " " + item["context"])))
    result = []
    remaining = MAX_CATALOG_CHARS
    for item in ordered:
        cost = sum(len(value) for value in item.values())
        if cost > remaining or len(result) >= MAX_LINKS:
            continue
        result.append({"id": f"source-link-{len(result) + 1:04d}", **item})
        remaining -= cost
    return result


def pdf_source_links(path: Path) -> list[dict[str, str]]:
    """Extract URI annotations and neighboring text locally; never follow targets."""
    import pdfplumber

    result = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            for link in page.hyperlinks:
                url = link.get("uri")
                if not safe_source_url(url):
                    continue
                x0, top, x1, bottom = (float(link[key]) for key in ("x0", "top", "x1", "bottom"))
                label = page.crop((x0, top, x1, bottom), strict=False).extract_text() or "Source link"
                context = page.crop((page.bbox[0], max(page.bbox[1], top - 30), page.bbox[2],
                                     min(page.bbox[3], bottom + 30)), strict=False).extract_text() or label
                result.append({"url": url, "label": label.strip()[:200],
                               "context": f"PDF page {page_number}: {context}"[:600]})
    return result


def provider_source_links(payload: dict[str, Any]) -> dict[str, Any]:
    """Called after anonymization: the provider selects IDs, never reconstructs URLs."""
    document = payload.get("source_document")
    if isinstance(document, dict) and isinstance(document.get("links"), list):
        document["links"] = [
            {key: item[key] for key in ("id", "label", "context") if key in item}
            for item in document["links"] if isinstance(item, dict)
        ]
    return payload
