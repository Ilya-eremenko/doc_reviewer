from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_current_user
from app.models.etalon import Etalon
from app.models.user import User
from app.schemas.etalons import EtalonDraftCreate, EtalonRead
from app.services.analyses import AnalysisNotFoundError
from app.services.etalons import EtalonForbiddenError, EtalonPreconditionError, create_etalon_draft_from_analysis

router = APIRouter(tags=["etalons"])


@router.post("/analyses/{analysis_id}/etalon-draft", response_model=EtalonRead, status_code=status.HTTP_201_CREATED)
def create_etalon_draft(
    analysis_id: UUID,
    payload: EtalonDraftCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> Etalon:
    try:
        return create_etalon_draft_from_analysis(
            db=db,
            actor=current_user,
            analysis_id=analysis_id,
            payload=payload or EtalonDraftCreate(),
        )
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc
    except EtalonForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except EtalonPreconditionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
