from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import FeedbackUsefulness


class FeedbackCreate(BaseModel):
    usefulness: FeedbackUsefulness
    verdict_correct: bool | None = None
    has_false_findings: bool | None = None
    has_missed_findings: bool | None = None
    comment: str | None = None
    can_use_for_benchmark: bool = False


class FeedbackRead(BaseModel):
    id: UUID
    user_id: UUID
    document_id: UUID
    analysis_id: UUID
    provider: str
    model: str
    skill_id: UUID
    skill_version: str
    usefulness: FeedbackUsefulness
    verdict_correct: bool | None
    has_false_findings: bool | None
    has_missed_findings: bool | None
    comment: str | None
    can_use_for_benchmark: bool
    processed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    feedback: list[FeedbackRead]
