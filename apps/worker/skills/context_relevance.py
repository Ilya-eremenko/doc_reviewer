from __future__ import annotations

import re


CURRENT_DECISION_MARKERS = re.compile(
    r"\bcurrent\s+(?:defen[cs]e|gate|review|scenario|plan|focus|scope)\b"
    r"|\b(?:selected|chosen|approved|committed|updated|latest)\s+"
    r"(?:scenario|case|plan|ltm|bank|partner|scope|focus)\b"
    r"|\b(?:текущ\w*|выбран\w*|утвержд\w*|актуальн\w*|действующ\w*)\s+"
    r"(?:защит\w*|гейт\w*|ревью|сценар\w*|план\w*|банк\w*|партн\w*|фокус\w*|вертикал\w*)",
    re.IGNORECASE,
)
CURRENT_DEFENSE_MARKERS = re.compile(
    r"\bcurrent\s+(?:defen[cs]e|gate|review)\b"
    r"|\bтекущ\w*\s+(?:защит\w*|гейт\w*|ревью)\b",
    re.IGNORECASE,
)
CONTEXT_TOPICS = re.compile(
    r"\b(?:ltm|scenario|bank|partner|vertical|focus|scope|current gate|current defense)\b"
    r"|\b(?:сценар\w*|банк\w*|партн\w*|вертикал\w*|фокус\w*|защит\w*)",
    re.IGNORECASE,
)
NON_CURRENT_ALTERNATIVE_MARKERS = re.compile(
    r"\b(?:previous|prior|historical|legacy|obsolete|deprecated|rejected|hypothetical|unselected|alternative|illustrative|maximum)\s+"
    r"(?:\w+\s+){0,2}(?:scenario|case|plan|bank|partner|option)\b"
    r"|\b(?:прошл\w*|предыдущ\w*|устаревш\w*|отклон\w*|гипотетич\w*|альтернативн\w*|иллюстративн\w*|максимальн\w*)\s+"
    r"(?:\w+\s+){0,2}(?:сценар\w*|кейс\w*|план\w*|банк\w*|партн\w*|вариант\w*)",
    re.IGNORECASE,
)
SELECTED_SCENARIO_MARKERS = re.compile(
    r"\b(?:selected|chosen|approved|committed|current)\s+(?:ltm\s+)?scenario\b"
    r"|\b(?:выбран\w*|утвержд\w*|текущ\w*)\s+(?:ltm[- ]?)?сценар\w*",
    re.IGNORECASE,
)
CONTEXT_CANDIDATE_MARKERS = re.compile(
    r"\b(?:current|selected|chosen|approved|committed|updated|latest|ltm|scenario|bank|partner|vertical|focus|scope)\b"
    r"|\b(?:текущ\w*|выбран\w*|утвержд\w*|актуальн\w*|действующ\w*|сценар\w*|банк\w*|партн\w*|вертикал\w*|фокус\w*)",
    re.IGNORECASE,
)


def decision_context_score(text: str) -> int:
    score = 0
    if CURRENT_DECISION_MARKERS.search(text):
        score += 14
    if SELECTED_SCENARIO_MARKERS.search(text):
        score += 8
    if CONTEXT_TOPICS.search(text):
        score += 4
    if NON_CURRENT_ALTERNATIVE_MARKERS.search(text):
        score -= 16
    return score
