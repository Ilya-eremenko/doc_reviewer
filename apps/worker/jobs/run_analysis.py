import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.analysis import Analysis
from app.models.document import Document
from app.models.provider_key import ProviderKey
from app.models.skill import Skill
from app.models.base import utc_now
from app.schemas.enums import Provider, RunStatus
from app.security.secrets import decrypt_secret
from providers.base import ProviderRunRequest
from providers.registry import get_provider_adapter
from results.schema_validation import parse_and_validate_json_output
from skills.prompt_renderer import render_prompt


def run_analysis(analysis_id: str, *, db: Session | None = None) -> None:
    owns_session = db is None
    session = db or SessionLocal()
    analysis_uuid = UUID(str(analysis_id))
    try:
        analysis = session.get(Analysis, analysis_uuid)
        if analysis is None:
            raise ValueError(f"Analysis {analysis_id} not found")
        analysis.status = RunStatus.RUNNING.value
        analysis.started_at = utc_now()
        analysis.error_message = None
        session.commit()

        document = session.get(Document, analysis.document_id)
        skill = session.get(Skill, analysis.skill_id)
        if document is None or skill is None:
            raise RuntimeError("analysis_context_missing")

        provider = Provider(analysis.provider)
        provider_key = _get_provider_key(session, analysis, provider)
        if provider != Provider.HERMES and provider_key is None:
            raise RuntimeError("provider_key_missing")
        api_key = decrypt_secret(provider_key.encrypted_api_key) if provider_key else None

        schema = json.loads(_resolve_schema_path(skill.result_schema_path).read_text(encoding="utf-8"))
        request = ProviderRunRequest(
            provider=provider,
            model=analysis.model,
            api_key=api_key,
            base_url=provider_key.base_url if provider_key else None,
            prompt=render_prompt(document=document, skill=skill, response_schema=schema),
            response_schema=schema,
            run_parameters=analysis.run_parameters,
        )
        result = get_provider_adapter(provider, analysis.run_parameters).run(request)
        structured = parse_and_validate_json_output(
            structured_text=result.structured_text,
            schema_path=skill.result_schema_path,
        )

        analysis.structured_output = structured
        analysis.raw_output = result.raw_output
        analysis.verdict = structured.get("verdict")
        analysis.summary = structured.get("summary")
        analysis.input_tokens = result.input_tokens
        analysis.output_tokens = result.output_tokens
        analysis.latency_ms = result.latency_ms
        analysis.estimated_cost = result.estimated_cost
        analysis.status = RunStatus.COMPLETED.value
        analysis.completed_at = utc_now()
        session.commit()
    except Exception as exc:
        session.rollback()
        failed = session.get(Analysis, analysis_uuid)
        if failed is None:
            raise
        failed.status = RunStatus.FAILED.value
        failed.error_message = str(exc)
        failed.completed_at = utc_now()
        session.commit()
    finally:
        if owns_session:
            session.close()


def _get_provider_key(session: Session, analysis: Analysis, provider: Provider) -> ProviderKey | None:
    statement = select(ProviderKey).where(
        ProviderKey.owner_id == analysis.user_id,
        ProviderKey.provider == provider.value,
    )
    return session.execute(statement).scalar_one_or_none()


def _resolve_schema_path(schema_path: str) -> Path:
    return Path(__file__).resolve().parents[3] / schema_path
