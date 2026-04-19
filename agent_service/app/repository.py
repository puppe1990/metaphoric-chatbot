from __future__ import annotations

import secrets
from collections.abc import Mapping
from typing import get_args

from app.models import ArtifactRecord, SessionRecord
from app.schemas import ArtifactMetadata, TurnIntent
from sqlalchemy.exc import IntegrityError

DEFAULT_STATE_BY_MODE = {
    "receive": "intake_problem",
    "build": "intake_problem",
}

SESSION_CONTEXT_FIELDS = {
    "active_metaphor_seed",
    "last_user_intent",
    "sensory_mode",
    "suggestion_basis",
}
TURN_INTENT_VALUES = set(get_args(TurnIntent))


class SessionRepository:
    def __init__(self, db_session):
        self.db = db_session

    def create_session(self, mode: str) -> SessionRecord:
        try:
            state = DEFAULT_STATE_BY_MODE[mode]
        except KeyError as exc:
            raise ValueError(f"Unsupported session mode: {mode!r}") from exc

        last_error = None
        for _ in range(3):
            record = SessionRecord(
                token=secrets.token_urlsafe(24),
                mode=mode,
                state=state,
            )
            self.db.add(record)
            try:
                self.db.commit()
            except IntegrityError as exc:
                self.db.rollback()
                last_error = exc
                continue
            self.db.refresh(record)
            return record

        assert last_error is not None
        raise last_error

    def create_artifact(
        self,
        session_id: int,
        artifact_type: str,
        content: str,
        metadata: ArtifactMetadata | Mapping[str, object] | None = None,
    ) -> ArtifactRecord:
        validated_metadata = None
        if metadata is not None:
            validated_metadata = ArtifactMetadata.model_validate(metadata).model_dump()

        record = ArtifactRecord(
            session_id=session_id,
            artifact_type=artifact_type,
            content=content,
        )
        record.set_metadata(validated_metadata)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def update_latest_artifact_metadata(
        self,
        session_id: int,
        metadata: ArtifactMetadata | Mapping[str, object],
        artifact_type: str | None = None,
    ) -> ArtifactRecord | None:
        query = (
            self.db.query(ArtifactRecord)
            .filter(ArtifactRecord.session_id == session_id)
            .order_by(ArtifactRecord.id.desc())
        )
        if artifact_type is not None:
            query = query.filter(ArtifactRecord.artifact_type == artifact_type)

        record = query.first()
        if record is None:
            return None

        current_metadata = record.get_metadata() or {}
        metadata_updates = metadata.model_dump() if isinstance(metadata, ArtifactMetadata) else dict(metadata)
        updated_metadata = ArtifactMetadata.model_validate({**current_metadata, **metadata_updates}).model_dump()
        record.set_metadata(updated_metadata)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def update_session_context(self, session_id: int, context: Mapping[str, object]) -> SessionRecord:
        unknown_fields = sorted(set(context) - SESSION_CONTEXT_FIELDS)
        if unknown_fields:
            raise ValueError(f"Unsupported session context fields: {', '.join(unknown_fields)}")

        intent = context.get("last_user_intent")
        if intent is not None and intent not in TURN_INTENT_VALUES:
            raise ValueError(f"Unsupported turn intent: {intent!r}")

        record = self.db.query(SessionRecord).filter(SessionRecord.id == session_id).one()
        for key, value in context.items():
            setattr(record, key, value)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record
