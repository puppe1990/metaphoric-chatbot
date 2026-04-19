from app.db import SessionLocal, init_db
from app.models import ArtifactRecord, SessionRecord
from app.repository import SessionRepository
from app.schemas import ArtifactMetadata
from pydantic import ValidationError


def test_create_session_persists_defaults(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)

        created = repo.create_session(mode="receive")
        token = created.token
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        persisted = fresh_session.query(SessionRecord).filter_by(token=token).one()
    finally:
        fresh_session.close()

    assert persisted.mode == "receive"
    assert persisted.state == "intake_problem"
    assert persisted.token == token


def test_create_session_retries_after_token_collision(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)

    tokens = iter(["dup-token", "dup-token", "unique-token"])
    monkeypatch.setattr("app.repository.secrets.token_urlsafe", lambda _n: next(tokens))

    session = SessionLocal()
    try:
        repo = SessionRepository(session)

        first = repo.create_session(mode="receive")
        second = repo.create_session(mode="receive")
        first_token = first.token
        second_token = second.token
    finally:
        session.close()

    assert first_token == "dup-token"
    assert second_token == "unique-token"

    fresh_session = SessionLocal()
    try:
        tokens_in_db = [row.token for row in fresh_session.query(SessionRecord).order_by(SessionRecord.id)]
    finally:
        fresh_session.close()

    assert tokens_in_db == ["dup-token", "unique-token"]


def test_create_session_rejects_invalid_mode(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)

        try:
            repo.create_session(mode="unknown")
        except ValueError as exc:
            assert "Unsupported session mode" in str(exc)
        else:
            raise AssertionError("Expected create_session to reject invalid mode")
    finally:
        session.close()


def test_create_artifact_persists_metadata(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        metadata = ArtifactMetadata(
            clarifier_asked=True,
            internal_candidate_count=3,
            selected_option="B",
        )

        artifact = repo.create_artifact(
            session_id=created_session.id,
            artifact_type="receive_choice",
            content="B. The bridge holds because it bends.",
            metadata=metadata,
        )
        session.commit()
        artifact_id = artifact.id
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        persisted = fresh_session.query(ArtifactRecord).filter_by(id=artifact_id).one()
    finally:
        fresh_session.close()

    assert persisted.session_id == created_session.id
    assert persisted.artifact_type == "receive_choice"
    assert persisted.content == "B. The bridge holds because it bends."
    assert persisted.get_metadata() == metadata.model_dump()


def test_create_artifact_respects_outer_transaction_boundary(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        artifact = repo.create_artifact(
            session_id=created_session.id,
            artifact_type="receive_choice",
            content="A. Uma ponte que cede sem romper.",
            metadata={
                "clarifier_asked": False,
                "internal_candidate_count": 3,
                "selected_option": None,
            },
        )
        artifact_id = artifact.id
        session.rollback()
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        persisted = fresh_session.query(ArtifactRecord).filter_by(id=artifact_id).first()
    finally:
        fresh_session.close()

    assert persisted is None


def test_create_artifact_rejects_invalid_selected_option(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        try:
            repo.create_artifact(
                session_id=created_session.id,
                artifact_type="receive_choice",
                content="Invalid choice payload",
                metadata={
                    "clarifier_asked": True,
                    "internal_candidate_count": 2,
                    "selected_option": "Z",
                },
            )
        except ValidationError as exc:
            assert "selected_option" in str(exc)
        else:
            raise AssertionError("Expected create_artifact to reject invalid selected_option")
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        artifact_count = fresh_session.query(ArtifactRecord).count()
    finally:
        fresh_session.close()

    assert artifact_count == 0


def test_update_latest_artifact_metadata_merges_partial_updates(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        artifact = repo.create_artifact(
            session_id=created_session.id,
            artifact_type="receive_choice",
            content="B. The bridge holds because it bends.",
            metadata={
                "clarifier_asked": False,
                "internal_candidate_count": 3,
                "selected_option": None,
            },
        )
        session.commit()

        updated = repo.update_latest_artifact_metadata(
            session_id=created_session.id,
            artifact_type="receive_choice",
            metadata={"selected_option": "C"},
        )
        session.commit()
        artifact_id = artifact.id
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        persisted = fresh_session.query(ArtifactRecord).filter_by(id=artifact_id).one()
    finally:
        fresh_session.close()

    assert updated is not None
    assert persisted.get_metadata() == {
        "clarifier_asked": False,
        "internal_candidate_count": 3,
        "selected_option": "C",
    }


def test_update_latest_artifact_metadata_filters_by_artifact_type(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        choice_artifact = repo.create_artifact(
            session_id=created_session.id,
            artifact_type="receive_choice",
            content="A. Uma ponte que cede sem romper.",
            metadata={
                "clarifier_asked": False,
                "internal_candidate_count": 3,
                "selected_option": None,
            },
        )
        repo.create_artifact(
            session_id=created_session.id,
            artifact_type="note",
            content="observacao interna",
            metadata=None,
        )
        session.commit()

        updated = repo.update_latest_artifact_metadata(
            session_id=created_session.id,
            artifact_type="receive_choice",
            metadata={"selected_option": "B"},
        )
        session.commit()
        choice_artifact_id = choice_artifact.id
    finally:
        session.close()

    fresh_session = SessionLocal()
    try:
        persisted_choice = fresh_session.query(ArtifactRecord).filter_by(id=choice_artifact_id).one()
        note_artifact = (
            fresh_session.query(ArtifactRecord).filter_by(session_id=created_session.id, artifact_type="note").one()
        )
    finally:
        fresh_session.close()

    assert updated is not None
    assert persisted_choice.get_metadata()["selected_option"] == "B"
    assert note_artifact.get_metadata() is None


def test_update_latest_artifact_metadata_returns_none_when_no_match_exists(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    init_db(database_url)
    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        updated = repo.update_latest_artifact_metadata(
            session_id=created_session.id,
            artifact_type="receive_choice",
            metadata={"selected_option": "A"},
        )
    finally:
        session.close()

    assert updated is None
