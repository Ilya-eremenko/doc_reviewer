from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_current_user
from app.models.user import User
from app.schemas.skills import SkillsListResponse
from app.services.skills import list_active_skills, read_skill

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=SkillsListResponse)
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> SkillsListResponse:
    return SkillsListResponse(skills=[read_skill(skill) for skill in list_active_skills(db=db)])
