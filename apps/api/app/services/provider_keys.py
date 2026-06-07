from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider_key import ProviderKey
from app.models.user import User
from app.schemas.enums import Provider
from app.security.secrets import decrypt_secret, encrypt_secret


def upsert_provider_key(
    *,
    db: Session,
    actor: User,
    provider: Provider,
    api_key: str,
    base_url: str | None,
    default_model: str,
) -> ProviderKey:
    provider_key = get_provider_key(db=db, owner_id=actor.id, provider=provider)
    if provider_key is None:
        provider_key = ProviderKey(owner_id=actor.id, provider=provider.value)
        db.add(provider_key)

    provider_key.base_url = base_url
    provider_key.default_model = default_model
    provider_key.encrypted_api_key = encrypt_secret(api_key)
    provider_key.api_key_fingerprint = _fingerprint(provider, api_key)
    db.commit()
    db.refresh(provider_key)
    return provider_key


def list_provider_keys(*, db: Session, actor: User) -> list[ProviderKey]:
    statement = select(ProviderKey).where(ProviderKey.owner_id == actor.id).order_by(ProviderKey.provider)
    return list(db.execute(statement).scalars().all())


def get_provider_key(*, db: Session, owner_id, provider: Provider) -> ProviderKey | None:
    statement = select(ProviderKey).where(
        ProviderKey.owner_id == owner_id,
        ProviderKey.provider == provider.value,
    )
    return db.execute(statement).scalar_one_or_none()


def delete_provider_key(*, db: Session, actor: User, provider: Provider) -> bool:
    provider_key = get_provider_key(db=db, owner_id=actor.id, provider=provider)
    if provider_key is None:
        return False
    db.delete(provider_key)
    db.commit()
    return True


def decrypt_provider_key(provider_key: ProviderKey) -> str:
    return decrypt_secret(provider_key.encrypted_api_key)


def _fingerprint(provider: Provider, api_key: str) -> str:
    suffix = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"{provider.value}:...{suffix}"
