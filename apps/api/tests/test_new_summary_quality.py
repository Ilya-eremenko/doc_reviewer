from app.services.new_summary_quality import (
    document_quality_percent,
    with_bilingual_document_quality,
    with_document_quality,
)
from app.services.new_summaries import _read_state
from uuid import uuid4

import pytest


def test_document_quality_counts_rated_children_instead_of_parent():
    payload = {"required_elements": [
        {"id": "a", "status": "есть"},
        {"id": "b", "status": "нет", "detail": {"type": "solution_validation", "items": [
            {"verdict": "confirmed"}, {"verdict": "insufficient"},
        ]}},
        {"id": "c", "status": "частично подтверждено", "detail": {"type": "metric_binding",
            "input_metrics": [{"binding": "confirmed"}],
            "output_metrics": [{"binding": "insufficient"}],
        }},
        {"id": "d", "status": "нет", "detail": {"type": "next_review_plan", "outputs_until_next_review": ["Pilot"]}},
    ]}
    # 2/2 + 1/2 + 1/2 + 0/2 = 4/8, not the parents' 3/8.
    assert document_quality_percent(payload) == 50


def test_document_quality_uses_fraction_when_rated_children_are_absent():
    payload = {"required_elements": [
        {"id": "a", "status": "2/5"},
        {"id": "b", "status": "есть"},
    ]}
    assert document_quality_percent(payload) == 57


def test_document_quality_supports_historical_appendix_and_does_not_mutate_payload():
    payload = {
        "required_elements": [{"id": "a", "status": "нет"}],
        "required_details": {"a": {"type": "solution_validation", "items": [{"verdict": "confirmed"}]}},
    }
    enriched = with_document_quality(payload)
    assert enriched["document_quality_percent"] == 100
    assert "document_quality_percent" not in payload


def test_document_quality_preserves_the_persisted_bilingual_score():
    payload = {"required_elements": [{"status": "нет"}], "document_quality_percent": 50}
    assert with_document_quality(payload)["document_quality_percent"] == 50
    assert with_document_quality(payload, recompute=True)["document_quality_percent"] == 0


def test_document_quality_missing_checklist_stays_unset():
    assert with_document_quality({"title": "Old report"}) == {"title": "Old report"}


def test_document_quality_handles_english_statuses_and_half_up_rounding():
    assert document_quality_percent({"required_elements": [
        {"id": "a", "status": "present"},
        {"id": "b", "status": "partially confirmed"},
        {"id": "c", "status": "missing"},
    ]}) == 50
    assert document_quality_percent({"required_elements": [
        {"id": "a", "status": "present"},
        {"id": "b", "status": "missing"},
        {"id": "c", "status": "missing"},
    ]}) == 33


def test_old_bilingual_report_uses_one_quality_score_without_mutating_either_version():
    ru = {"required_elements": [{"status": "есть"}]}
    en = {"required_elements": [{"status": "missing"}]}
    enriched_ru, enriched_en = with_bilingual_document_quality(ru, en)
    assert enriched_ru["document_quality_percent"] == 100
    assert enriched_en["document_quality_percent"] == 100
    assert "document_quality_percent" not in ru
    assert "document_quality_percent" not in en


@pytest.mark.parametrize("schema_version", ["new-summary-v2", "new-summary-v3", "new-summary-v4", "new-summary-v5", "new-summary-v6"])
def test_numbered_report_is_read_without_reintroducing_removed_quality_field(schema_version):
    payload = {"schema_version": schema_version, "language": "ru",
               "required_elements": [{"status": "есть"}], "traction_summary": {"tables": []}}
    state = {"version": 2, "generation_mode": "new_summary_skill", "source_revision": "check-id",
             "ru": {"status": "completed", "payload": payload},
             "en": {"status": "completed", "payload": {**payload, "language": "en"}}}
    result = _read_state(uuid4(), state)
    assert "document_quality_percent" not in result.ru.payload
    assert "document_quality_percent" not in result.en.payload
    assert "document_quality_percent" not in state["ru"]["payload"]
