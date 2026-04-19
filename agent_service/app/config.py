import os
from pathlib import Path


def load_environment_file(start_path: str | Path | None = None) -> Path | None:
    current = Path(start_path or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        env_path = directory / ".env"
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        return env_path

    return None


def get_database_url() -> str:
    return os.getenv("AGENT_DATABASE_URL", "sqlite:///./metaphoric_chatbot.db")


def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "AGENT_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
