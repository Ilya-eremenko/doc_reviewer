from __future__ import annotations

import re


_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)", re.IGNORECASE)
_SOURCE_LINK = re.compile(r"(?:3\s*sigma|tri\s*sigma|три\s*сигм|ссылка|\blink\b)", re.IGNORECASE)
_TRAILING_SOURCE = re.compile(
    r"(?:\s*\((?:3\s*sigma|tri\s*sigma|три\s*сигм|ссылка|link)[^)]*\)\s*)+$",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_SUMMARY_SUFFIX = re.compile(r"\s*[-–—]\s*AI Summary\s*$", re.IGNORECASE)


def clean_initiative_title(value: str) -> str:
    title = value.strip()
    if title.lower().startswith("ai summary "):
        title = title[len("AI Summary "):]
    title = _SUMMARY_SUFFIX.sub("", title)
    title = _MARKDOWN_LINK.sub(
        lambda match: "" if _SOURCE_LINK.search(match.group(1)) else match.group(1),
        title,
    )
    title = _URL.sub("", title)
    title = _TRAILING_SOURCE.sub("", title)
    title = re.sub(r"\s+", " ", title).strip(" \t-–—,;:()[]")
    return title or "Untitled initiative"


def display_new_summary_title(value: str) -> str:
    return f"{clean_initiative_title(value)} - AI Summary"
