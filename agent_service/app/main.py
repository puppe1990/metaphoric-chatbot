from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_allowed_origins, load_environment_file
from app.db import SessionLocal, init_db
from app.models import ArtifactRecord, MessageRecord, SessionRecord
from app.agents import hydrate_receive_choice_artifact
from app.orchestrator import (
    REFINE_SELECTED_MESSAGE,
    advance_mode,
    build_assistant_message,
    start_assistant_message,
)
from app.providers.base import ChatProvider
from app.providers.groq_provider import GroqProvider
from app.providers.local_provider import LocalProvider
from app.repository import SessionRepository
from app.schemas import ArtifactView, ChatResponse, MessageRequest, StartSessionRequest

RECEIVE_SELECTIONS = {"A", "B", "C"}


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
    return (
        db.query(MessageRecord)
        .filter(MessageRecord.session_id == session_id)
        .order_by(MessageRecord.id.asc())
        .all()
    )


def serialize_messages(messages: list[MessageRecord]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def list_session_artifacts(db, session_id: int) -> list[ArtifactRecord]:
    return (
        db.query(ArtifactRecord)
        .filter(ArtifactRecord.session_id == session_id)
        .order_by(ArtifactRecord.id.asc())
        .all()
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


def create_provider() -> ChatProvider:
    try:
        return GroqProvider()
    except RuntimeError as exc:
        return LocalProvider()


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

        if (
            session.mode == "receive"
            and session.state == "present_choices"
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
                    role="user",
                    content=content,
                    step=session.state,
                )
            )
            session.state = "refine_selected"
            db.add(
                MessageRecord(
                    session_id=session.id,
                    role="assistant",
                    content=REFINE_SELECTED_MESSAGE,
                    step=session.state,
                )
            )
            db.commit()
            db.refresh(session)

            return {
                "token": session.token,
                "mode": session.mode,
                "state": session.state,
                "assistant_message": REFINE_SELECTED_MESSAGE,
                "messages": serialize_messages(list_session_messages(db, session.id)),
                "artifacts": serialize_artifacts(list_session_artifacts(db, session.id)),
            }

        next_state = advance_mode(session.mode, session.state)
        resolved_state, assistant_message, artifacts = build_assistant_message(
            mode=session.mode,
            state=next_state,
            user_input=build_contextual_user_input(existing_messages, content),
            provider_factory=create_provider,
        )

        db.add(
            MessageRecord(
                session_id=session.id,
                role="user",
                content=content,
                step=session.state,
            )
        )
        session.state = resolved_state
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
