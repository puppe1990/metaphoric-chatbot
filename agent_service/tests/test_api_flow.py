from app.main import create_app
from app.orchestrator import build_assistant_message
from fastapi.testclient import TestClient


def test_start_session_returns_token_and_state(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        response = client.post("/api/chat/start", json={"mode": "receive"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "receive"
    assert body["state"] == "intake_problem"
    assert body["token"]


def test_start_session_supports_browser_preflight_from_web_origin(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        response = client.options(
            "/api/chat/start",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    allow_methods = response.headers["access-control-allow-methods"]
    assert "POST" in allow_methods


def test_start_session_returns_build_mode_opening_prompt(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        response = client.post("/api/chat/start", json={"mode": "build"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "build"
    assert body["state"] == "intake_problem"
    assert body["assistant_message"] == "Descreva o problema em uma frase simples."


def test_get_session_returns_persisted_opening_message(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.get(f"/api/chat/session/{token}")

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == token
    assert body["mode"] == "receive"
    assert body["state"] == "intake_problem"
    assert body["messages"] == [
        {
            "role": "assistant",
            "content": "Descreva o problema em uma frase simples.",
        }
    ]


def test_message_endpoint_persists_transcript_and_advances_state(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Meu projeto trava quando preciso decidir."},
        )

        restored = client.get(f"/api/chat/session/{token}")

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == token
    assert body["mode"] == "receive"
    assert body["state"] == "present_choices"
    artifact = body["artifacts"][0]
    assert body["messages"][:2] == [
        {
            "role": "assistant",
            "content": "Descreva o problema em uma frase simples.",
        },
        {
            "role": "user",
            "content": "Meu projeto trava quando preciso decidir.",
        },
    ]
    assert artifact["artifact_type"] == "receive_choice"
    assert artifact["content"] == body["messages"][-1]["content"]
    assert artifact["metadata"] == {
        "clarifier_asked": False,
        "internal_candidate_count": 3,
        "selected_option": None,
    }
    assert [choice["label"] for choice in artifact["choices"]] == ["A", "B", "C"]
    assert all(choice["text"] for choice in artifact["choices"])
    assert "Escolha" in body["messages"][-1]["content"]
    assistant_messages = [message["content"] for message in body["messages"] if message["role"] == "assistant"]
    assert "Qual é a sensação dominante nisso?" not in assistant_messages
    assert "Que mudança você gostaria de sentir ao final desta metáfora?" not in assistant_messages

    assert restored.status_code == 200
    assert restored.json()["messages"] == body["messages"]
    assert restored.json()["artifacts"] == body["artifacts"]


def test_message_endpoint_selects_receive_choice_and_enters_refinement(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        choices_response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Meu projeto trava quando preciso decidir."},
        )
        assert choices_response.status_code == 200

        response = client.post("/api/chat/message", json={"token": token, "content": "B"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "refine_selected"
    assert "mais curta" in body["assistant_message"]
    assert "mais concreta" in body["assistant_message"]
    assert "mais poética" in body["assistant_message"]
    assert "mais direta" in body["assistant_message"]
    assert body["messages"][-1] == {
        "role": "assistant",
        "content": body["assistant_message"],
    }
    assert body["artifacts"][0]["metadata"] == {
        "clarifier_asked": False,
        "internal_candidate_count": 3,
        "selected_option": "B",
    }


def test_message_endpoint_rejects_blank_content(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.post("/api/chat/message", json={"token": token, "content": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Message content cannot be empty."}


def test_message_endpoint_uses_local_fallback_when_provider_is_not_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Meu projeto trava."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert body["artifacts"][0]["artifact_type"] == "receive_choice"
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C"]
    assert "Escolha" in body["messages"][-1]["content"]


def test_message_endpoint_normalizes_malformed_receive_choices_into_safe_artifact(tmp_path, monkeypatch):
    class BrokenChoiceProvider:
        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            return "Uma gaveta emperrada sem rótulos nem três opções."

    monkeypatch.setattr("app.main.create_provider", lambda: BrokenChoiceProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Meu projeto trava quando preciso decidir."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert body["artifacts"][0]["artifact_type"] == "receive_choice"
    assert body["artifacts"][0]["metadata"] == {
        "clarifier_asked": False,
        "internal_candidate_count": 3,
        "selected_option": None,
    }
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C"]
    assert "A." in body["messages"][-1]["content"]
    assert "B." in body["messages"][-1]["content"]
    assert "C." in body["messages"][-1]["content"]
    assistant_messages = [message["content"] for message in body["messages"] if message["role"] == "assistant"]
    assert "Qual é a sensação dominante nisso?" not in assistant_messages
    assert "Que mudança você gostaria de sentir ao final desta metáfora?" not in assistant_messages


def test_start_session_rejects_invalid_mode_with_400(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        response = client.post("/api/chat/start", json={"mode": "unknown"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported session mode: 'unknown'"}


def test_build_assistant_message_returns_opening_prompt_for_intake_problem():
    state, message, artifacts = build_assistant_message(
        mode="receive",
        state="intake_problem",
        user_input="",
        provider_factory=lambda: None,
    )

    assert state == "intake_problem"
    assert message == "Descreva o problema em uma frase simples."
    assert artifacts == []


def test_build_assistant_message_returns_build_opening_prompt_for_intake_problem():
    state, message, artifacts = build_assistant_message(
        mode="build",
        state="intake_problem",
        user_input="",
        provider_factory=lambda: None,
    )

    assert state == "intake_problem"
    assert message == "Descreva o problema em uma frase simples."
    assert artifacts == []


def test_build_fallback_coaching_responds_to_user_attempt_without_repeating_prompt():
    state, message, artifacts = build_assistant_message(
        mode="build",
        state="coach_feedback",
        user_input=(
            "assistant: Isso parece mais uma porta emperrada, um rio barrado, "
            "uma engrenagem presa, um motor acelerado ou uma bússola girando?\n"
            "user: um macaco bagunceiro\n"
            "assistant: Boa direção. Escolha uma imagem concreta e diga o que ela faz quando o conflito aparece.\n"
            "user: falo uma bobagem muito grande"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "coach_feedback"
    assert "Escolha uma imagem concreta" not in message
    assert "macaco" in message
    assert "bobagem" in message
    assert artifacts == []


def test_build_fallback_coaching_uses_user_image_without_invalidating_it():
    state, message, artifacts = build_assistant_message(
        mode="build",
        state="rewrite_together",
        user_input=(
            "assistant: Se isso tivesse um conflito central, qual seria em poucas palavras?\n"
            "user: uma força lutando internamente\n"
            "assistant: Isso parece mais algo preso, algo sendo empurrado, ou algo perdido no caminho?\n"
            "user: vento\n"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "rewrite_together"
    assert "vento" in message.lower()
    assert "não é" not in message.lower()
    assert message.startswith("Então")
    assert not message.startswith("Use ")
    assert message.count("?") <= 1
    assert artifacts == []
