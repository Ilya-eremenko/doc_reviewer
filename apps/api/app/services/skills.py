from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.schemas.enums import EntityStatus
from app.schemas.skills import SkillRead, SkillSourceSnapshot


def list_active_skills(*, db: Session) -> list[Skill]:
    statement = select(Skill).where(Skill.status == EntityStatus.ACTIVE.value).order_by(Skill.name, Skill.version)
    return list(db.execute(statement).scalars().all())


def skill_source_snapshot(skill: Skill) -> dict:
    return {
        "name": skill.name,
        "version": skill.version,
        "skill_type": skill.skill_type,
        "source_type": skill.source_type,
        "source_uri": skill.source_uri,
        "source_entrypoint": skill.source_entrypoint,
        "source_revision": skill.source_revision,
        "source_fingerprint": skill.source_fingerprint,
        "source_metadata": skill.source_metadata,
        "result_schema_path": skill.result_schema_path,
    }


def read_skill(skill: Skill) -> SkillRead:
    return SkillRead(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        version=skill.version,
        skill_type=skill.skill_type,
        supported_document_types=skill.supported_document_types,
        result_schema_path=skill.result_schema_path,
        status=skill.status,
        source_snapshot=SkillSourceSnapshot(
            source_type=skill.source_type,
            source_uri=skill.source_uri,
            source_entrypoint=skill.source_entrypoint,
            source_revision=skill.source_revision,
            source_fingerprint=skill.source_fingerprint,
            source_metadata=skill.source_metadata,
        ),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )
