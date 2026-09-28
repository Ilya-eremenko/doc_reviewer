from __future__ import annotations

import re


CURRENT_DECISION_MARKERS = re.compile(
    r"\bcurrent\s+(?:defen[cs]e|gate|review|scenario|plan|focus|scope)\b"
    r"|\b(?:selected|chosen|approved|committed|updated|latest)\s+"
    r"(?:scenario|case|plan|ltm|bank|partner|scope|focus)\b"
    r"|\b(?:текущ\w*|выбран\w*|утвержд\w*|актуальн\w*|действующ\w*)\s+"
    r"(?:защит\w*|гейт\w*|ревью|сценар\w*|план\w*|банк\w*|партн\w*|фокус\w*|охват\w*|вертикал\w*)",
    re.IGNORECASE,
)
CURRENT_DEFENSE_MARKERS = re.compile(
    r"\bcurrent\s+(?:defen[cs]e|gate|review)\b"
    r"|\bтекущ\w*\s+(?:защит\w*|гейт\w*|ревью)\b",
    re.IGNORECASE,
)
CURRENT_SCOPE_MARKERS = re.compile(
    r"\bcurrent\s+(?:scope|focus)\b"
    r"|\bтекущ\w*\s+(?:охват\w*|фокус\w*|вертикал\w*)\b",
    re.IGNORECASE,
)
CONTEXT_TOPICS = re.compile(
    r"\b(?:ltm|scenario|bank|partner|vertical|focus|scope|current gate|current defense)\b"
    r"|\b(?:сценар\w*|банк\w*|партн\w*|вертикал\w*|фокус\w*|охват\w*|защит\w*)",
    re.IGNORECASE,
)
NON_CURRENT_ALTERNATIVE_MARKERS = re.compile(
    r"\b(?:previous|prior|historical|legacy|obsolete|deprecated|rejected|hypothetical|unselected|alternative|illustrative|maximum)\s+"
    r"(?:\w+\s+){0,2}(?:scenario|case|plan|bank|partner|option)\b"
    r"|\b(?:selected|chosen|approved|committed|current)\s+"
    r"(?:(?:base|baseline|target|ltm|actual|conservative|upside)\s+){0,2}scenario\b\s+"
    r"(?:in\s+(?:19|20)\d{2}\b|from\s+(?:the\s+)?(?:previous|prior|historical)\s+period\b|(?:was\s+)?retired\b)"
    r"|\b(?:прошл\w*|предыдущ\w*|устаревш\w*|отклон\w*|гипотетич\w*|альтернативн\w*|иллюстративн\w*|максимальн\w*)\s+"
    r"(?:\w+\s+){0,2}(?:сценар\w*|кейс\w*|план\w*|банк\w*|партн\w*|вариант\w*)",
    re.IGNORECASE,
)
SELECTED_SCENARIO_MARKERS = re.compile(
    r"\b(?:selected|chosen|approved|committed|current)\s+"
    r"(?:(?:base|baseline|target|ltm|actual|conservative|upside)\s+){0,2}scenario\b"
    r"|\b(?:выбран\w*|утвержд\w*|текущ\w*)\s+"
    r"(?:(?:базов\w*|целев\w*|консервативн\w*|ltm)\s+){0,2}сценар\w*",
    re.IGNORECASE,
)
CONTEXT_CANDIDATE_MARKERS = re.compile(
    r"\b(?:current|selected|chosen|approved|committed|updated|latest|ltm|scenario|bank|partner|vertical|focus|scope)\b"
    r"|\b(?:текущ\w*|выбран\w*|утвержд\w*|актуальн\w*|действующ\w*|сценар\w*|банк\w*|партн\w*|вертикал\w*|фокус\w*|охват\w*)",
    re.IGNORECASE,
)


def decision_context_score(text: str) -> int:
    score = 0
    alternatives = list(NON_CURRENT_ALTERNATIVE_MARKERS.finditer(text))
    active_selected = any(
        not any(match.start() < alternative.end() and match.end() > alternative.start() for alternative in alternatives)
        for match in SELECTED_SCENARIO_MARKERS.finditer(text)
    )
    if CURRENT_DECISION_MARKERS.search(text) or active_selected:
        score += 14
    if active_selected:
        score += 8
    if CONTEXT_TOPICS.search(text):
        score += 4
    if alternatives and not active_selected:
        score -= 16
    return score
