import os

from app.config import load_environment_file


def test_load_environment_file_reads_parent_dotenv_when_service_runs_from_subdir(tmp_path, monkeypatch):
    root = tmp_path / "project"
    service = root / "agent_service"
    service.mkdir(parents=True)
    (root / ".env").write_text("GROQ_API_KEY=test-key\nAGENT_DATABASE_URL=sqlite:///root.db\n")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    loaded = load_environment_file(service)

    assert loaded == root / ".env"
    assert os.environ["GROQ_API_KEY"] == "test-key"
    assert os.environ["AGENT_DATABASE_URL"] == "sqlite:///root.db"
