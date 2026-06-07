from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_current_user
from app.models.provider_key import ProviderKey
from app.models.user import User
from app.schemas.enums import Provider
from app.schemas.provider_settings import ProviderKeyRead, ProviderKeysListResponse, ProviderKeyUpsert
from app.services.provider_keys import delete_provider_key, list_provider_keys, upsert_provider_key

router = APIRouter(prefix="/settings/provider-keys", tags=["provider-settings"])


def _read_provider_key(provider_key: ProviderKey) -> ProviderKeyRead:
    return ProviderKeyRead(
        provider=Provider(provider_key.provider),
        base_url=provider_key.base_url,
        default_model=provider_key.default_model,
        api_key_fingerprint=provider_key.api_key_fingerprint,
        has_key=True,
    )


@router.get("", response_model=ProviderKeysListResponse)
def get_provider_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> ProviderKeysListResponse:
    return ProviderKeysListResponse(
        provider_keys=[_read_provider_key(item) for item in list_provider_keys(db=db, actor=current_user)]
    )


@router.put("/{provider}", response_model=ProviderKeyRead)
def put_provider_key(
    provider: Provider,
    payload: ProviderKeyUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> ProviderKeyRead:
    return _read_provider_key(
        upsert_provider_key(
            db=db,
            actor=current_user,
            provider=provider,
            api_key=payload.api_key,
            base_url=payload.base_url,
            default_model=payload.default_model,
        )
    )


@router.delete("/{provider}")
def remove_provider_key(
    provider: Provider,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> dict[str, str]:
    delete_provider_key(db=db, actor=current_user, provider=provider)
    return {"status": "deleted"}
