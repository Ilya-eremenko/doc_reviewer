import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from app.core.config import get_settings
from privacy.model_anonymization import anonymize_value_for_model
from providers.base import AnalysisProviderResult
from skills.new_summary_generation import (
    _generation_prompt, _new_summary_schema, _normalized_required_detail,
    _source_document_payload, _validated_new_summary, _verified_source_links,
)
from skills.source_links import pdf_source_links, provider_source_links, source_link_catalog


@pytest.mark.parametrize("scheme", ["https", "HTTPS"])
def test_design_link_survives_anonymization_model_selection_and_bilingual_validation(monkeypatch, scheme):
    monkeypatch.setenv("DOCUMENT_ANONYMIZATION_ENABLED", "true")
    get_settings.cache_clear()
    try:
        url = f"{scheme}://design.example/prototype?node-id=12&mode=design#frame"
        text = f"## FAQ 1\nSee full design [here]({url}).\n[Financial model](https://example.com/budget)"
        source = {"document_type": "gate_2", "document_stage": "Gate 2", "source_document": {
            "parsed_text_excerpt": text, "links": source_link_catalog(text),
        }}
        before = deepcopy(source)
        anonymization = anonymize_value_for_model(source)
        safe = provider_source_links(anonymization.value)
        prompt = _generation_prompt(source_payload=safe, response_schema=_new_summary_schema())
        assert url not in prompt
        assert all("url" not in entry for entry in safe["source_document"]["links"])
        link_id = safe["source_document"]["links"][0]["id"]
        assert link_id == source["source_document"]["links"][0]["id"]
        report = {"title": "AI Summary Example", "versions": [
            {"language": language, "context": "Context.", "required_elements": [{
                "id": "gate2_user_flow", "status": "частично подтверждено", "evidence": "A design link is supplied.",
                "detail": {"type": "source_links", "availability": "provided", "links": [
                    {"label": "Design", "source_link_id": link_id},
                ]},
            }]} for language in ("en", "ru")
        ]}
        result = _validated_new_summary(
            AnalysisProviderResult(structured_text=json.dumps(report), raw_output="mock", latency_ms=1),
            _new_summary_schema(), source_payload=source, anonymization_metadata=anonymization.metadata,
        )
        for variant in result["versions"]:
            detail = next(item["detail"] for item in variant["required_elements"] if item["id"] == "gate2_user_flow")
            assert detail == {"type": "source_links", "availability": "provided", "links": [{"label": "Design", "url": url}]}
        assert source == before
    finally:
        get_settings.cache_clear()


def test_catalog_keeps_late_document_links_and_rejects_unknown_or_unsafe_targets():
    url = "https://example.com/design_(final)?node=1&view=2"
    text = "Background.\n" * 10000 + f"See full design [here](<{url}>)"
    document = SimpleNamespace(parsed_text=text, title="Example", original_filename="case.docx",
                               detected_document_type="gate_2", manual_document_type=None)
    source = {"source_document": _source_document_payload(document)}
    assert url not in source["source_document"]["parsed_text_excerpt"]
    assert source["source_document"]["links"][0]["url"] == url
    detail = _normalized_required_detail({"type": "source_links", "availability": "provided", "links": [
        {"label": "Actual", "source_link_id": "source-link-0001"},
        {"label": "Duplicate", "source_link_id": "source-link-0001"},
        {"label": "Invented", "source_link_id": "source-link-9999", "url": url},
        {"label": "Wrong", "url": "https://example.com/other"},
        {"label": "Unsafe", "url": "javascript:alert(1)"},
    ]})
    assert _verified_source_links(detail, source)["links"] == [{"label": "Actual", "url": url}]


def test_catalog_uses_full_markdown_link_syntax_and_deduplicates():
    url = "https://example.com/design_(a)?one=1&two=2"
    catalog = source_link_catalog(f"See full design [here](<{url}>)\n\n[here][design]\n\n[design]: <{url}>\n\n[bad](javascript:alert(1))")
    assert len(catalog) == 1
    assert catalog[0]["url"] == url
    assert "full design" in catalog[0]["context"]
    unicode_url = "https://example.com/макет?view=видео"
    assert source_link_catalog(f"[Design]({unicode_url})")[0]["url"] == unicode_url
    assert source_link_catalog(f"See full design: {url}.")[0]["url"] == url
    assert _verified_source_links({"links": [{"label": "Design", "url": url}], "availability": "provided"},
                                  {"source_document": {"parsed_text_excerpt": f"See design: {url}."}})["links"] == [{"label": "Design", "url": url}]


def test_pdf_hidden_uri_annotation_is_available_without_changing_parsed_text(tmp_path, monkeypatch):
    path = tmp_path / "defense.pdf"
    url = "https://example.com/prototype?node-id=1&mode=design"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 750, "FAQ 1. Product idea")
    pdf.drawString(50, 700, "See full design here")
    pdf.linkURL(url, (130, 695, 158, 713))
    pdf.save()
    links = pdf_source_links(path)
    assert links[0]["url"] == url
    assert "See full design" in links[0]["context"]
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    try:
        document = SimpleNamespace(id="test", parsed_text="See full design here", title="Example",
            original_filename="defense.pdf", storage_path=str(path), detected_document_type="gate_2", manual_document_type=None)
        payload = _source_document_payload(document)
        assert payload["parsed_text_excerpt"] == document.parsed_text
        assert payload["links"][0]["url"] == url
        assert payload["link_extraction"] == "parsed_text_and_pdf_annotations"
        document.storage_path = str(tmp_path.parent / "outside.pdf")
        payload = _source_document_payload(document)
        assert payload["links"] == []
        assert payload["link_extraction"] == "pdf_annotations_unavailable"
        assert _verified_source_links({"links": [], "availability": "absent"}, {"source_document": payload})["availability"] == "unavailable"
    finally:
        get_settings.cache_clear()
