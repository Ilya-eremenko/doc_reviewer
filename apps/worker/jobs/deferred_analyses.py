from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import SessionLocal
from app.logging import worker_logger
from app.models.analysis import Analysis
from app.models.base import utc_now
from app.models.skill import Skill
from app.models.skill_source import SkillSourceSnapshot
from app.models.document import Document
from app.schemas.enums import DocumentParseStatus, DocumentType, RunStatus
from app.services.analysis_jobs import enqueue_run_analysis
from app.services.analyses import DOCUMENT_PARSE_DEPENDENCY_KEY
from skills.snapshot_loader import load_skill_source_snapshot


DeferredAnalysisEnqueue = Callable[[UUID], None]


def enqueue_ready_deferred_analyses(
    *,
    db: Session | None = None,
    document_id: UUID | None = None,
    enqueue: DeferredAnalysisEnqueue | None = None,
) -> int:
    owns_session = db is None
    session = db or SessionLocal()
    enqueue_analysis = enqueue or enqueue_run_analysis
    try:
        analyses = _ready_deferred_analyses(session=session, document_id=document_id)
        enqueued = 0
        for analysis, document in analyses:
            try:
                _validate_progress_review_snapshot(session=session, analysis=analysis, document=document)
            except (ValueError, RuntimeError, OSError):
                analysis.status = RunStatus.FAILED.value
                analysis.completed_at = utc_now()
                analysis.error_message = "Progress Review source snapshot is missing its rubric or main-skill route"
                _mark_dependency_state(
                    session=session,
                    analysis=analysis,
                    document=document,
                    state="source_preflight_failed",
                    error=analysis.error_message,
                )
                worker_logger.info(
                    "deferred_analysis_source_preflight_failed",
                    extra={"analysis_id": str(analysis.id), "status": "failed"},
                )
                continue
            _mark_dependency_state(
                session=session,
                analysis=analysis,
                document=document,
                state="enqueueing",
            )
            try:
                enqueue_analysis(analysis.id)
            except Exception as exc:
                _mark_dependency_state(
                    session=session,
                    analysis=analysis,
                    document=document,
                    state="enqueue_failed",
                    error=f"{exc.__class__.__name__}: {exc}",
                )
                worker_logger.info(
                    "deferred_analysis_enqueue_failed",
                    extra={
                        "job_type": "parse_document",
                        "entity_id": str(document.id),
                        "analysis_id": str(analysis.id),
                        "status": "failed",
                        "error_class": exc.__class__.__name__,
                    },
                )
                continue

            _mark_dependency_state(
                session=session,
                analysis=analysis,
                document=document,
                state="enqueued",
            )
            enqueued += 1
            worker_logger.info(
                "deferred_analysis_enqueued",
                extra={
                    "job_type": "parse_document",
                    "entity_id": str(document.id),
                    "analysis_id": str(analysis.id),
                    "status": "queued",
                },
            )
        return enqueued
    finally:
        if owns_session:
            session.close()



def _validate_progress_review_snapshot(*, session: Session, analysis: Analysis, document: Document) -> None:
    document_type = document.manual_document_type or document.detected_document_type
    if document_type != DocumentType.PROGRESS_REVIEW.value:
        return
    skill = session.get(Skill, analysis.skill_id)
    if skill is None or skill.name != "gate2_challenger_main_analysis":
        return
    snapshot_id = (analysis.run_parameters or {}).get("source_snapshot_id")
    snapshot = session.get(SkillSourceSnapshot, UUID(str(snapshot_id))) if snapshot_id else None
    if snapshot is None or snapshot.analysis_id != analysis.id:
        raise ValueError("progress_review_snapshot_unavailable")
    material = load_skill_source_snapshot(snapshot.artifact_path)
    prefix = "skills/gate-challenger/"
    if not material.read_text(prefix + "references/progress-review-rubric.md") or (
        "progress-review-rubric.md" not in (material.read_text(prefix + "SKILL.md") or "")
    ):
        raise ValueError("progress_review_snapshot_incomplete")


def _ready_deferred_analyses(
    *,
    session: Session,
    document_id: UUID | None,
) -> list[tuple[Analysis, Document]]:
    statement = (
        select(Analysis, Document)
        .join(Document, Analysis.document_id == Document.id)
        .where(
            Analysis.status == RunStatus.QUEUED.value,
            Analysis.deleted_at.is_(None),
            Document.parse_status == DocumentParseStatus.COMPLETED.value,
        )
        .order_by(Analysis.created_at, Analysis.id)
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)

    return [
        (analysis, document)
        for analysis, document in session.execute(statement).all()
        if _is_waiting_for_document_parse(analysis)
    ]


def _is_waiting_for_document_parse(analysis: Analysis) -> bool:
    dependency = (analysis.run_parameters or {}).get(DOCUMENT_PARSE_DEPENDENCY_KEY)
    return isinstance(dependency, dict) and dependency.get("state") != "enqueued"


def _mark_dependency_state(
    *,
    session: Session,
    analysis: Analysis,
    document: Document,
    state: str,
    error: str | None = None,
) -> None:
    parameters = dict(analysis.run_parameters or {})
    dependency = dict(parameters.get(DOCUMENT_PARSE_DEPENDENCY_KEY) or {})
    dependency.update(
        {
            "document_id": str(document.id),
            "state": state,
        }
    )
    if error:
        dependency["error"] = error
    else:
        dependency.pop("error", None)
    parameters[DOCUMENT_PARSE_DEPENDENCY_KEY] = dependency
    parameters["document_type"] = document.manual_document_type or document.detected_document_type
    analysis.run_parameters = parameters
    flag_modified(analysis, "run_parameters")
    session.commit()
