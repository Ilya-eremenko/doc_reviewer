from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.analysis import Analysis
from app.models.document import Document
from app.models.etalon import Etalon
from app.schemas.enums import DocumentParseStatus, DocumentType, EtalonStatus, Provider, Role, RunStatus
from app.schemas.etalons import EtalonPayload
from app.seeds.skills import seed_baseline_skills

from test_documents_upload import create_user, login, upload_document


def test_etalon_payload_validates_layer_parent_links():
    payload = _valid_etalon_payload()

    etalon_payload = EtalonPayload.model_validate(payload)

    assert etalon_payload.expected_verdict == "need_evidence"
    assert etalon_payload.layer_2[0].parent_layer_1_id == "L1-001"


def test_etalon_payload_rejects_orphan_layer_2_parent():
    payload = _valid_etalon_payload()
    payload["layer_2"][0]["parent_layer_1_id"] = "L1-missing"

    with pytest.raises(ValidationError, match="parent_layer_1_id"):
        EtalonPayload.model_validate(payload)


def test_etalon_payload_rejects_invalid_severity():
    payload = _valid_etalon_payload()
    payload["layer_1"][0]["severity"] = "urgent"

    with pytest.raises(ValidationError):
        EtalonPayload.model_validate(payload)


def test_etalon_payload_requires_expected_verdict():
    payload = _valid_etalon_payload()
    payload.pop("expected_verdict")

    with pytest.raises(ValidationError):
        EtalonPayload.model_validate(payload)


def test_user_can_create_etalon_draft_from_own_completed_analysis(client, db_session):
    user = create_user(db_session, "author", "secret")
    analysis = _create_completed_analysis(client, db_session, user)
    login(client, "author", "secret")

    response = client.post(f"/analyses/{analysis.id}/etalon-draft")

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == str(analysis.document_id)
    assert payload["author_id"] == str(user.id)
    assert payload["source"] == "ai_post_annotation"
    assert payload["status"] == "draft"
    assert payload["expected_verdict"] == "need_evidence"
    assert payload["layer_1"][0]["id"] == "L1-001"
    assert payload["layer_2"][0]["parent_layer_1_id"] == "L1-001"
    assert payload["key_findings"] == ["Missing incrementality"]

    etalon = db_session.query(Etalon).one()
    assert etalon.document_id == analysis.document_id
    assert etalon.author_id == user.id
    assert etalon.status == EtalonStatus.DRAFT.value


def test_user_cannot_create_etalon_draft_from_another_users_analysis(client, db_session):
    owner = create_user(db_session, "owner", "secret")
    create_user(db_session, "other", "secret")
    analysis = _create_completed_analysis(client, db_session, owner)
    login(client, "other", "secret")

    response = client.post(f"/analyses/{analysis.id}/etalon-draft")

    assert response.status_code == 404
    assert db_session.query(Etalon).count() == 0


def test_admin_can_create_active_etalon_from_analysis(client, db_session):
    admin = create_user(db_session, "admin", "secret", Role.ADMIN)
    analysis = _create_completed_analysis(client, db_session, admin)
    login(client, "admin", "secret")

    response = client.post(f"/analyses/{analysis.id}/etalon-draft", json={"status": "active"})

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    assert db_session.query(Etalon).one().status == EtalonStatus.ACTIVE.value


def test_normal_user_cannot_create_active_etalon_from_analysis(client, db_session):
    user = create_user(db_session, "author", "secret")
    analysis = _create_completed_analysis(client, db_session, user)
    login(client, "author", "secret")

    response = client.post(f"/analyses/{analysis.id}/etalon-draft", json={"status": "active"})

    assert response.status_code == 403
    assert db_session.query(Etalon).count() == 0


def _valid_etalon_payload():
    return {
        "expected_verdict": "need_evidence",
        "layer_1": [
            {
                "id": "L1-001",
                "dimension": "Traction credibility",
                "status": "fail",
                "severity": "high",
                "title": "Traction does not prove scaling",
                "summary": "Pilot results are extrapolated without scaling evidence.",
                "evidence": [{"quote": "pilot grew 10%", "location": "page 5"}],
                "recommendation": "Add cohort and incrementality analysis.",
                "confidence": 0.8,
            }
        ],
        "layer_2": [
            {
                "id": "L2-001",
                "parent_layer_1_id": "L1-001",
                "check": "Is there evidence of incrementality?",
                "status": "partial",
                "severity": "medium",
                "finding": "Incrementality is claimed but not measured.",
                "evidence": [{"quote": "impact was positive", "location": "page 8"}],
                "expected_fix": "Show control group and significance.",
                "confidence": 0.76,
            }
        ],
        "key_findings": ["Missing incrementality"],
    }


def _create_completed_analysis(client, db_session, user):
    from app.main import app
    from app.routers import documents as documents_router

    app.dependency_overrides[documents_router.get_parse_document_enqueue] = lambda: lambda document_id: None
    try:
        login(client, user.login, "secret")
        upload = upload_document(client, "gate.txt", b"Gate 2 MVP metrics")
        client.post("/auth/logout")
    finally:
        app.dependency_overrides.pop(documents_router.get_parse_document_enqueue, None)
    document = db_session.get(Document, UUID(upload.json()["id"]))
    document.parse_status = DocumentParseStatus.COMPLETED.value
    document.parsed_text = "Gate 2 MVP metrics"
    document.detected_document_type = DocumentType.GATE_2.value
    skill = seed_baseline_skills(db_session)[0]
    analysis = Analysis(
        document_id=document.id,
        user_id=user.id,
        skill_id=skill.id,
        skill_version=skill.version,
        provider=Provider.OPENAI_COMPATIBLE.value,
        model="gpt-test",
        status=RunStatus.COMPLETED.value,
        verdict="need_evidence",
        summary="Needs evidence",
        structured_output={
            "verdict": "need_evidence",
            "summary": "Needs evidence",
            "layer_1": [
                {
                    "id": "L1-001",
                    "dimension": "Traction credibility",
                    "status": "fail",
                    "severity": "high",
                    "title": "Traction does not prove scaling",
                    "summary": "Pilot results are extrapolated without scaling evidence.",
                    "evidence": [{"quote": "pilot grew 10%", "location": "page 5"}],
                    "recommendation": "Add cohort and incrementality analysis.",
                    "confidence": 0.8,
                }
            ],
            "layer_2": [
                {
                    "id": "L2-001",
                    "parent_layer_1_id": "L1-001",
                    "check": "Is there evidence of incrementality?",
                    "status": "partial",
                    "severity": "medium",
                    "finding": "Incrementality is claimed but not measured.",
                    "evidence": [{"quote": "impact was positive", "location": "page 8"}],
                    "expected_fix": "Show control group and significance.",
                    "confidence": 0.76,
                }
            ],
            "key_findings": ["Missing incrementality"],
            "findings": [],
            "checks": [],
        },
        raw_output="raw",
        run_parameters={},
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis
