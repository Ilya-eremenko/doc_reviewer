from docx import Document as DocxDocument
from docx.shared import RGBColor
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

from app.services import new_summary_exports as exports


def test_required_element_statuses_match_in_pdf_and_word():
    statuses = [
        ("есть", "Есть", RGBColor(15, 163, 107), exports._SUCCESS),
        ("частично подтверждено", "Частично подтверждено", RGBColor(199, 120, 0), exports._WARNING),
        ("нет", "Нет", RGBColor(217, 45, 32), exports._DANGER),
        ("2/5", "2/5", RGBColor(17, 24, 39), exports._TEXT),
    ]
    content = {
        "required_elements": [
            {"id": str(index), "label": "Criterion", "status": status, "evidence": "Source evidence."}
            for index, (status, *_rest) in enumerate(statuses)
        ]
    }
    labels = exports._labels("ru")

    document = DocxDocument()
    exports._append_docx_required(document, content, labels)
    status_runs = [run for paragraph in document.paragraphs for run in paragraph.runs if run.text.startswith(" — ")]
    assert [(run.text.strip(" —"), run.font.color.rgb) for run in status_runs] == [
        (label, color) for _status, label, color, _pdf_color in statuses
    ]

    story = []
    normal = getSampleStyleSheet()["Normal"]
    exports._append_pdf_required(story, content, labels, {"heading": normal, "required": normal, "evidence": normal})
    required_paragraphs = [item.text for item in story if isinstance(item, Paragraph) and "Criterion" in item.text]
    assert len(required_paragraphs) == len(statuses)
    for paragraph, (_status, label, _word_color, pdf_color) in zip(required_paragraphs, statuses, strict=True):
        assert label in paragraph
        assert f'color="{pdf_color}"' in paragraph
