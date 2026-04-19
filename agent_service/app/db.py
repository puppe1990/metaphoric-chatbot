from __future__ import annotations

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)

SESSION_CONTEXT_SQLITE_COLUMNS = {
    "active_metaphor_seed": "TEXT",
    "last_user_intent": "VARCHAR(64)",
    "sensory_mode": "VARCHAR(32)",
    "suggestion_basis": "VARCHAR(255)",
}


def _sync_sqlite_session_columns() -> None:
    assert engine is not None
    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("sessions")}
    missing_columns = SESSION_CONTEXT_SQLITE_COLUMNS.keys() - existing_columns
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name in sorted(missing_columns):
            column_type = SESSION_CONTEXT_SQLITE_COLUMNS[column_name]
            connection.execute(text(f"ALTER TABLE sessions ADD COLUMN {column_name} {column_type}"))


def init_db(database_url: str) -> None:
    global engine

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

    SessionLocal.configure(bind=engine)

    # Import models after the engine/session factory exist so SQLAlchemy can
    # register the tables before creating them.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if database_url.startswith("sqlite"):
        _sync_sqlite_session_columns()
