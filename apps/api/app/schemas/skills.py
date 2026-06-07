from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import DocumentType, EntityStatus, SkillSourceType, SkillType


class SkillSourceSnapshot(BaseModel):
    source_type: SkillSourceType
    source_uri: str | None
    source_entrypoint: str | None
    source_revision: str | None
    source_fingerprint: str | None
    source_metadata: dict


class SkillRead(BaseModel):
    id: UUID
    name: str
    description: str
    version: str
    skill_type: SkillType
    supported_document_types: list[DocumentType]
    result_schema_path: str
    status: EntityStatus
    source_snapshot: SkillSourceSnapshot
    created_at: datetime
    updated_at: datetime


class SkillsListResponse(BaseModel):
    skills: list[SkillRead]
