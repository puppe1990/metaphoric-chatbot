from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from app.agents import hydrate_receive_choice_artifact
from app.config import get_allowed_origins, load_environment_file
from app.db import SessionLocal, init_db
from app.models import ArtifactRecord, MessageRecord, SessionRecord, SettingRecord
from app.orchestrator import (
    advance_mode,
    build_assistant_message,
    start_assistant_message,
)
from app.providers.base import ChatProvider
from app.providers.groq_provider import GroqProvider, RateLimitError
from app.providers.local_provider import LocalProvider
from app.providers.nvidia_provider import NvidiaProvider
from app.repository import SessionRepository
from app.schemas import ArtifactView, ChatResponse, MessageRequest, StartSessionRequest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

RECEIVE_SELECTIONS = {"A", "B", "C", "D", "E"}

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

NVIDIA_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/nemotron-3-nano",
    "nvidia/nemotron-3-super-120b-a12b",
    "bigcode/starcoder2-7b",
]

PROVIDER_LABELS = {
    "groq": "Groq",
    "nvidia": "NVIDIA NIM",
    "local": "Local (mock)",
}


class ProviderConfig(BaseModel):
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"


def _provider_label(provider: str) -> str:
    return PROVIDER_LABELS.get(provider, provider)


def _build_provider_error_detail(
    *,
    code: str,
    message: str,
    provider: str,
    model: str,
    retryable: bool,
    action: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": code,
        "message": message,
        "provider": provider,
        "model": model,
        "retryable": retryable,
    }
    if action is not None:
        payload["action"] = action
    return payload


def _translate_provider_exception(exc: Exception, config: ProviderConfig) -> HTTPException:
    message = str(exc)
    normalized_message = message.lower()
    provider_label = _provider_label(config.provider)
    provider_with_model = f"{provider_label} / {config.model}"

    if (
        "end of life" in normalized_message
        or "no longer available" in normalized_message
        or "[410]" in normalized_message
    ):
        return HTTPException(
            status_code=503,
            detail=_build_provider_error_detail(
                code="provider_model_unavailable",
                message=(
                    f"O modelo {provider_with_model} não está mais disponível. "
                    "Troque de modelo ou provider para continuar."
                ),
                provider=config.provider,
                model=config.model,
                retryable=False,
                action="switch_provider_or_model",
            ),
        )

    if isinstance(exc, RateLimitError) or "rate_limit" in normalized_message or "[429]" in normalized_message:
        return HTTPException(
            status_code=429,
            detail=_build_provider_error_detail(
                code="provider_rate_limit",
                message=(
                    f"O provider {provider_with_model} atingiu o limite de uso agora. "
                    "Espere um pouco ou troque de provider/modelo para continuar."
                ),
                provider=config.provider,
                model=config.model,
                retryable=True,
                action="switch_provider_or_model",
            ),
        )

    if "api key" in normalized_message or "not set" in normalized_message or "unavailable" in normalized_message:
        return HTTPException(
            status_code=503,
            detail=_build_provider_error_detail(
                code="provider_configuration_error",
                message=(
                    f"O provider {provider_label} não está pronto para uso nesta instalação. "
                    "Troque de provider/modelo ou ajuste a configuração do backend."
                ),
                provider=config.provider,
                model=config.model,
                retryable=False,
                action="switch_provider_or_model",
            ),
        )

    return HTTPException(
        status_code=502,
        detail=_build_provider_error_detail(
            code="provider_request_failed",
            message=(
                f"A resposta do provider {provider_with_model} falhou desta vez. "
                "Tente novamente ou troque de provider/modelo se o erro continuar."
            ),
            provider=config.provider,
            model=config.model,
            retryable=True,
        ),
    )


def get_default_database_url() -> str:
    service_root = Path(__file__).resolve().parents[1]
    database_path = service_root / "metaphoric_chatbot.db"
    return f"sqlite:///{database_path}"


def resolve_database_url(database_url: str | None = None) -> str:
    if database_url:
        return database_url
    return get_default_database_url()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_or_404(db, token: str) -> SessionRecord:
    record = db.query(SessionRecord).filter(SessionRecord.token == token).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session not found for token '{token}'.")
    return record


def list_session_messages(db, session_id: int) -> list[MessageRecord]:
    return db.query(MessageRecord).filter(MessageRecord.session_id == session_id).order_by(MessageRecord.id.asc()).all()


def serialize_messages(messages: list[MessageRecord]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def list_session_artifacts(db, session_id: int) -> list[ArtifactRecord]:
    return (
        db.query(ArtifactRecord).filter(ArtifactRecord.session_id == session_id).order_by(ArtifactRecord.id.asc()).all()
    )


def serialize_artifacts(artifacts: list[ArtifactRecord]) -> list[dict[str, object]]:
    views = [_artifact_record_to_view(artifact) for artifact in artifacts]
    return [view.model_dump() for view in views]


def _artifact_record_to_view(artifact: ArtifactRecord) -> ArtifactView:
    metadata = artifact.get_metadata()
    if artifact.artifact_type == "receive_choice":
        return hydrate_receive_choice_artifact(artifact.content, metadata)

    return ArtifactView(
        artifact_type=artifact.artifact_type,
        content=artifact.content,
        metadata=metadata,
    )


def _load_provider_config(db) -> ProviderConfig:
    rows = db.query(SettingRecord).filter(SettingRecord.key.in_(["provider", "model"])).all()
    settings = {r.key: r.value for r in rows}
    return ProviderConfig(
        provider=settings.get("provider", "groq"),
        model=settings.get("model", "llama-3.3-70b-versatile"),
    )


def _save_provider_config(db, config: ProviderConfig) -> None:
    for key, value in [("provider", config.provider), ("model", config.model)]:
        row = db.query(SettingRecord).filter(SettingRecord.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SettingRecord(key=key, value=value))
    db.commit()


def _build_provider(provider: str, model: str) -> ChatProvider:
    if provider == "local":
        return LocalProvider()
    if provider == "nvidia":
        try:
            return NvidiaProvider(model=model)
        except RuntimeError:
            return LocalProvider()
    try:
        return GroqProvider(model=model)
    except RuntimeError:
        return LocalProvider()


def create_provider() -> ChatProvider:
    return _build_provider("groq", "llama-3.3-70b-versatile")


def resolve_provider(db) -> ChatProvider:
    cfg = _load_provider_config(db)
    return _build_provider(cfg.provider, cfg.model)


def build_contextual_user_input(messages: list[MessageRecord], content: str) -> str:
    transcript = "\n".join(
        f"{message.role}: {message.content}" for message in messages if message.role in {"assistant", "user"}
    )
    if not transcript:
        return content

    return f"{transcript}\nuser: {content}"


def create_app(database_url: str | None = None) -> FastAPI:
    load_environment_file(Path(__file__).resolve())
    resolved_database_url = resolve_database_url(database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db(resolved_database_url)
        yield

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/config")
    def get_config(db=Depends(get_db)) -> dict[str, object]:
        cfg = _load_provider_config(db)
        return {
            "provider": cfg.provider,
            "model": cfg.model,
            "groq_models": GROQ_MODELS,
            "nvidia_models": NVIDIA_MODELS,
        }

    @app.post("/api/config")
    def set_config(payload: ProviderConfig, db=Depends(get_db)) -> dict[str, object]:
        if payload.provider == "groq" and payload.model not in GROQ_MODELS:
            raise HTTPException(status_code=400, detail=f"Unknown model '{payload.model}'.")
        if payload.provider == "nvidia" and payload.model not in NVIDIA_MODELS:
            raise HTTPException(status_code=400, detail=f"Unknown NVIDIA model '{payload.model}'.")
        _save_provider_config(db, payload)
        return {"provider": payload.provider, "model": payload.model}

    @app.post("/api/chat/start", response_model=ChatResponse)
    def start_session(
        payload: StartSessionRequest,
        db=Depends(get_db),
    ) -> ChatResponse:
        repo = SessionRepository(db)
        try:
            created = repo.create_session(payload.mode)
            assistant_message = start_assistant_message(created.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        db.add(
            MessageRecord(
                session_id=created.id,
                role="assistant",
                content=assistant_message,
                step=created.state,
            )
        )
        db.commit()

        return ChatResponse(
            token=created.token,
            mode=created.mode,
            state=created.state,
            assistant_message=assistant_message,
        )

    @app.get("/api/chat/session/{token}")
    def get_session(token: str, db=Depends(get_db)) -> dict[str, object]:
        session = get_session_or_404(db, token)
        messages = list_session_messages(db, session.id)
        artifacts = list_session_artifacts(db, session.id)

        return {
            "token": session.token,
            "mode": session.mode,
            "state": session.state,
            "messages": serialize_messages(messages),
            "artifacts": serialize_artifacts(artifacts),
        }

    @app.post("/api/chat/message")
    def send_message(payload: MessageRequest, db=Depends(get_db)) -> dict[str, object]:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="Message content cannot be empty.")

        repo = SessionRepository(db)
        session = get_session_or_404(db, payload.token)
        existing_messages = list_session_messages(db, session.id)
        provider_config = _load_provider_config(db)

        prior_state = session.state
        next_state = advance_mode(session.mode, prior_state)
        state_for_response = next_state
        if session.mode == "receive" and prior_state in {"present_choices", "refine_selected"}:
            state_for_response = prior_state

        try:
            resolved_state, assistant_message, artifacts, interpretation = build_assistant_message(
                mode=session.mode,
                state=state_for_response,
                user_input=build_contextual_user_input(existing_messages, content),
                provider_factory=lambda: resolve_provider(db),
            )
        except Exception as exc:
            raise _translate_provider_exception(exc, provider_config) from exc

        db.add(
            MessageRecord(
                session_id=session.id,
                role="user",
                content=content,
                step=session.state,
            )
        )
        session.state = resolved_state
        if interpretation is not None:
            session_context: dict[str, str] = {
                "last_user_intent": interpretation.intent,
            }
            if interpretation.active_metaphor_seed is not None:
                session_context["active_metaphor_seed"] = interpretation.active_metaphor_seed
            if interpretation.sensory_mode is not None:
                session_context["sensory_mode"] = interpretation.sensory_mode
            if interpretation.suggestion_basis is not None:
                session_context["suggestion_basis"] = interpretation.suggestion_basis
            repo.update_session_context(
                session_id=session.id,
                context=session_context,
            )
            if (
                session.mode == "receive"
                and prior_state in {"present_choices", "refine_selected"}
                and interpretation.intent == "agent_option_selection"
                and content in RECEIVE_SELECTIONS
            ):
                updated_artifact = repo.update_latest_artifact_metadata(
                    session_id=session.id,
                    artifact_type="receive_choice",
                    metadata={"selected_option": content},
                )
                if updated_artifact is None:
                    raise HTTPException(
                        status_code=409,
                        detail="No receive choice artifact found for selection.",
                    )
        db.add(
            MessageRecord(
                session_id=session.id,
                role="assistant",
                content=assistant_message,
                step=resolved_state,
            )
        )
        for artifact in artifacts:
            repo.create_artifact(
                session_id=session.id,
                artifact_type=artifact.artifact_type,
                content=artifact.content,
                metadata=artifact.metadata,
            )
        db.commit()
        db.refresh(session)

        return {
            "token": session.token,
            "mode": session.mode,
            "state": session.state,
            "assistant_message": assistant_message,
            "messages": serialize_messages(list_session_messages(db, session.id)),
            "artifacts": serialize_artifacts(list_session_artifacts(db, session.id)),
        }

    return app


app = create_app()
