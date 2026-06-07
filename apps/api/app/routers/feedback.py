from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_current_user
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackRead
from app.services.feedback import (
    FeedbackForbiddenError,
    FeedbackNotFoundError,
    create_feedback,
    list_feedback_for_admin,
    mark_feedback_processed,
)

router = APIRouter(tags=["feedback"])


@router.post("/analyses/{analysis_id}/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def post_feedback(
    analysis_id: UUID,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> Feedback:
    try:
        return create_feedback(db=db, actor=current_user, analysis_id=analysis_id, payload=payload)
    except FeedbackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc


@router.get("/admin/feedback", response_model=FeedbackListResponse)
def get_admin_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> FeedbackListResponse:
    try:
        return FeedbackListResponse(feedback=list_feedback_for_admin(db=db, actor=current_user))
    except FeedbackForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required") from exc


@router.patch("/admin/feedback/{feedback_id}/processed", response_model=FeedbackRead)
def patch_feedback_processed(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> Feedback:
    try:
        return mark_feedback_processed(db=db, actor=current_user, feedback_id=feedback_id)
    except FeedbackForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required") from exc
    except FeedbackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found") from exc
