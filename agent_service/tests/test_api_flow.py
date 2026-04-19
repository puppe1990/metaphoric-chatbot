import time

import pytest
from app.db import SessionLocal
from app.main import build_contextual_user_input, create_app
from app.models import ArtifactRecord, SessionRecord
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


def test_build_contextual_user_input_includes_selected_symbolic_world_context():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider
    from app.repository import SessionRepository

    session = SessionLocal()
    try:
        repo = SessionRepository(session)
        created_session = repo.create_session(mode="receive")

        artifact = generate_contextual_choices(LocalProvider(), "Tenho pressa e não consigo organizar as ideias.")
        repo.create_artifact(
            session_id=created_session.id,
            artifact_type=artifact.artifact_type,
            content=artifact.content,
            metadata={
                **artifact.metadata.model_dump(),
                "selected_option": "D",
            },
        )
        session.commit()

        contextual_input = build_contextual_user_input(
            messages=[],
            content="Mais poética.",
            artifacts=session.query(ArtifactRecord).filter_by(session_id=created_session.id).all(),
        )
    finally:
        session.close()

    assert "selected_symbolic_world_label: D" in contextual_input
    assert "selected_symbolic_world_name: Máquina / engenharia" in contextual_input
    assert (
        "selected_symbolic_world_description: Máquina / engenharia: sistema, engrenagem, processo." in contextual_input
    )


def test_message_endpoint_persists_transcript_and_advances_state(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

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
    assert body["messages"][-1]["content"] == (
        "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."
    )
    assert artifact["content"] != body["messages"][-1]["content"]
    assert artifact["metadata"] == {
        "clarifier_asked": False,
        "internal_candidate_count": 5,
        "selected_option": None,
    }
    assert [choice["label"] for choice in artifact["choices"]] == ["A", "B", "C", "D", "E"]
    assert all(choice["text"] for choice in artifact["choices"])
    assert "mundo" in body["messages"][-1]["content"].lower()
    assert "Escolha A, B ou C" not in body["messages"][-1]["content"]
    assistant_messages = [message["content"] for message in body["messages"] if message["role"] == "assistant"]
    assert "Qual é a sensação dominante nisso?" not in assistant_messages
    assert "Que mudança você gostaria de sentir ao final desta metáfora?" not in assistant_messages

    assert restored.status_code == 200
    assert restored.json()["messages"] == body["messages"]
    assert restored.json()["artifacts"] == body["artifacts"]


def test_message_endpoint_selects_receive_choice_and_enters_refinement(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

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
        "internal_candidate_count": 5,
        "selected_option": "B",
    }


def test_message_endpoint_promotes_user_image_to_active_metaphor_seed(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})

        response = client.post("/api/chat/message", json={"token": token, "content": "um barco perdido no oceano"})
        restored = client.get(f"/api/chat/session/{token}")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert body["assistant_message"] == (
        "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."
    )
    assert body["artifacts"][0]["artifact_type"] == "receive_choice"
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C", "D", "E"]

    restored_body = restored.json()
    assert restored_body["state"] == "present_choices"


def test_message_endpoint_refinement_request_in_present_choices_skips_literal_selection(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})

        response = client.post("/api/chat/message", json={"token": token, "content": "mais curta"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert body["assistant_message"] == (
        "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."
    )
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C", "D", "E"]
    assert body["messages"][-1]["role"] == "assistant"


def test_message_endpoint_contextual_receive_suggestions_offer_symbolic_worlds(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        response = client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})

    assert response.status_code == 200
    body = response.json()
    choice_texts = [choice["text"].lower() for choice in body["artifacts"][0]["choices"]]
    assert "natureza: plantio, colheita, raiz, crescimento." in choice_texts
    assert "guerra / estratégia: batalha, território, ataque, defesa." in choice_texts
    assert "jornada / viagem: caminho, mapa, destino." in choice_texts


def test_message_endpoint_repeated_problem_statement_in_present_choices_does_not_advance_state(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post(
            "/api/chat/message",
            json={"token": token, "content": "Tenho pressa e não consigo organizar as ideias."},
        )
        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Tenho pressa e não consigo organizar as ideias."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert (
        body["assistant_message"]
        == "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."
    )
    assert body["artifacts"][0]["artifact_type"] == "receive_choice"
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C", "D", "E"]


def test_message_endpoint_refinement_request_keeps_active_metaphor_context(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})
        client.post("/api/chat/message", json={"token": token, "content": "C"})
        response = client.post("/api/chat/message", json={"token": token, "content": "mais concreta"})

    assert response.status_code == 200
    message = response.json()["assistant_message"].lower()
    assert response.json()["state"] == "refine_selected"
    assert "jornada / viagem" in message
    assert "trilha" in message


def test_message_endpoint_receive_mode_converges_to_final_metaphor(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())
    monkeypatch.setattr(
        "app.main._load_provider_config",
        lambda _db: __import__("app.main", fromlist=["ProviderConfig"]).ProviderConfig(
            provider="local",
            model="",
        ),
    )

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "Sei o que quero, mas fico adiando."})
        client.post("/api/chat/message", json={"token": token, "content": "C"})
        client.post("/api/chat/message", json={"token": token, "content": "mais poética"})
        client.post("/api/chat/message", json={"token": token, "content": "uma luta no ringue"})
        first_follow_up = client.post(
            "/api/chat/message",
            json={"token": token, "content": "uma luta de anos entre uma voz suave e um chiado agressivo"},
        )
        second_follow_up = client.post(
            "/api/chat/message",
            json={"token": token, "content": "o chiado aperta a cena e empurra tudo para o canto"},
        )
        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "eu preciso que no fim sobre uma abertura limpa para agir"},
        )

        final_body = None
        for _ in range(200):
            restored = client.get(f"/api/chat/session/{token}")
            assert restored.status_code == 200
            candidate = restored.json()
            final_artifact = candidate["artifacts"][-1]
            statuses = [variant["status"] for variant in final_artifact["comparison_variants"]]
            if statuses == ["complete", "complete"]:
                final_body = candidate
                break
            time.sleep(0.05)

    assert first_follow_up.status_code == 200
    assert "?" in first_follow_up.json()["assistant_message"]
    assert second_follow_up.status_code == 200
    assert "?" in second_follow_up.json()["assistant_message"]
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "refine_selected"
    assert body["assistant_message"] == "Aqui estão duas leituras finais do mesmo núcleo metafórico."
    comparison_artifact = body["artifacts"][-1]
    assert comparison_artifact["artifact_type"] == "receive_final_comparison"
    assert len(comparison_artifact["comparison_variants"]) == 2
    assert comparison_artifact["comparison_variants"][0]["title"] == "Erickson / insinuante"
    assert comparison_artifact["comparison_variants"][1]["title"] == "Bandler / cinematográfica"
    assert comparison_artifact["comparison_variants"][0]["status"] == "pending"
    assert comparison_artifact["comparison_variants"][1]["status"] == "pending"

    assert final_body is not None
    final_artifact = final_body["artifacts"][-1]
    assert "chiado" in final_artifact["comparison_variants"][0]["text"].lower()
    assert "chiado" in final_artifact["comparison_variants"][1]["text"].lower()
    assert "máquina imensa" not in final_artifact["comparison_variants"][0]["text"].lower()
    assert "máquina imensa" not in final_artifact["comparison_variants"][1]["text"].lower()
    assert final_artifact["comparison_variants"][0]["text"].count("\n\n") == 2
    assert final_artifact["comparison_variants"][1]["text"].count("\n\n") == 2


def test_message_endpoint_refinement_request_uses_symbolic_world_name_instead_of_letter(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "Estou travado para tomar uma decisão."})
        client.post("/api/chat/message", json={"token": token, "content": "A"})
        response = client.post("/api/chat/message", json={"token": token, "content": "Mais poética."})

    assert response.status_code == 200
    message = response.json()["assistant_message"].lower()
    assert "na natureza que você escolheu" in message
    assert "mundo a" not in message


def test_message_endpoint_selection_without_existing_choice_artifact_stays_recoverable(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        response = client.post("/api/chat/message", json={"token": token, "content": "A"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "present_choices"
    assert body["artifacts"][0]["artifact_type"] == "receive_choice"
    assert body["artifacts"][0]["metadata"]["selected_option"] is None


def test_message_endpoint_refinement_request_preserves_persisted_active_metaphor_seed(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())
    database_url = f"sqlite:///{tmp_path}/api-flow.db"

    with TestClient(create_app(database_url=database_url)) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})
        client.post("/api/chat/message", json={"token": token, "content": "B"})
        response = client.post("/api/chat/message", json={"token": token, "content": "mais concreta"})
        restored = client.get(f"/api/chat/session/{token}")

    session = SessionLocal()
    try:
        persisted = session.query(SessionRecord).filter_by(token=token).one()
    finally:
        session.close()

    assert response.status_code == 200
    assert restored.status_code == 200
    assert restored.json()["state"] == "refine_selected"
    assert persisted.active_metaphor_seed is None
    assert "guerra / estratégia" in response.json()["assistant_message"].lower()
    assert persisted.receive_llm_question_count == 0


def test_message_endpoint_rejects_blank_content(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        response = client.post("/api/chat/message", json={"token": token, "content": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Message content cannot be empty."}


def test_message_endpoint_uses_local_fallback_when_provider_is_not_configured(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

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
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C", "D", "E"]
    assert "mundo" in body["messages"][-1]["content"].lower()
    assert "Escolha A, B ou C" not in body["messages"][-1]["content"]


def test_message_endpoint_normalizes_malformed_receive_choices_into_safe_artifact(tmp_path, monkeypatch):
    class BrokenChoiceProvider:
        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            return "Uma gaveta emperrada sem rótulos nem três opções."

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: BrokenChoiceProvider())

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
        "internal_candidate_count": 5,
        "selected_option": None,
    }
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C", "D", "E"]
    assert body["messages"][-1]["content"] == (
        "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."
    )
    assert "A." in body["artifacts"][0]["content"]
    assert "B." in body["artifacts"][0]["content"]
    assert "C." in body["artifacts"][0]["content"]
    assert "D." in body["artifacts"][0]["content"]
    assert "E." in body["artifacts"][0]["content"]
    assistant_messages = [message["content"] for message in body["messages"] if message["role"] == "assistant"]
    assert "Qual é a sensação dominante nisso?" not in assistant_messages
    assert "Que mudança você gostaria de sentir ao final desta metáfora?" not in assistant_messages


def test_message_endpoint_returns_structured_provider_error_when_model_is_unavailable(tmp_path, monkeypatch):
    class ExpiredModelProvider:
        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            raise Exception(
                "[410] Gone\n"
                "The model 'deepseek-ai/deepseek-r1' has reached its end of life on "
                "2026-01-26T00:00:00Z and is no longer available."
            )

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: ExpiredModelProvider())
    monkeypatch.setattr(
        "app.main._load_provider_config",
        lambda _db: __import__("app.main", fromlist=["ProviderConfig"]).ProviderConfig(
            provider="nvidia",
            model="deepseek-ai/deepseek-r1",
        ),
    )

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        started = client.post("/api/chat/start", json={"mode": "receive"})
        token = started.json()["token"]

        initial = client.post(
            "/api/chat/message",
            json={"token": token, "content": "Meu projeto trava quando preciso decidir."},
        )
        choose_world = client.post("/api/chat/message", json={"token": token, "content": "D"})
        refine_tone = client.post("/api/chat/message", json={"token": token, "content": "Mais poética."})
        response = client.post("/api/chat/message", json={"token": token, "content": "engrenagem"})

    assert initial.status_code == 200
    assert choose_world.status_code == 200
    assert refine_tone.status_code == 200
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "provider_model_unavailable",
            "message": (
                "O modelo NVIDIA NIM / deepseek-ai/deepseek-r1 não está mais disponível. "
                "Troque de modelo ou provider para continuar."
            ),
            "provider": "nvidia",
            "model": "deepseek-ai/deepseek-r1",
            "retryable": False,
            "action": "switch_provider_or_model",
        }
    }


def test_start_session_rejects_invalid_mode_with_400(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        response = client.post("/api/chat/start", json={"mode": "unknown"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported session mode: 'unknown'"}


def test_build_assistant_message_returns_opening_prompt_for_intake_problem():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="intake_problem",
        user_input="",
        provider_factory=lambda: None,
    )

    assert state == "intake_problem"
    assert message == "Descreva o problema em uma frase simples."
    assert artifacts == []
    assert interpretation is None


def test_build_assistant_message_returns_build_opening_prompt_for_intake_problem():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="build",
        state="intake_problem",
        user_input="",
        provider_factory=lambda: None,
    )

    assert state == "intake_problem"
    assert message == "Descreva o problema em uma frase simples."
    assert artifacts == []
    assert interpretation is None


def test_build_fallback_coaching_responds_to_user_attempt_without_repeating_prompt():
    state, message, artifacts, interpretation = build_assistant_message(
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
    assert interpretation is None


def test_build_fallback_coaching_uses_user_image_without_invalidating_it():
    state, message, artifacts, interpretation = build_assistant_message(
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
    assert interpretation is None


def test_build_assistant_message_finalizes_receive_when_image_has_enough_material():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="refine_selected",
        user_input=(
            "assistant: Descreva o problema em uma frase simples.\n"
            "user: Sei o que quero, mas fico adiando.\n"
            "assistant: Em qual desses mundos isso se encaixa?\n"
            "user: C\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais poetica\n"
            "assistant: Entao o centro continua claro.\n"
            "user: uma luta no ringue\n"
            "assistant: O que essa imagem faz com a cena quando o conflito aparece?\n"
            "user: uma luta de anos entre uma voz suave e um chiado agressivo"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
        receive_llm_question_count=3,
    )

    assert state == "refine_selected"
    assert message == "Aqui estão duas leituras finais do mesmo núcleo metafórico."
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "receive_final_comparison"
    assert len(artifacts[0].comparison_variants) == 2
    assert artifacts[0].comparison_variants[0].title == "Erickson / insinuante"
    assert artifacts[0].comparison_variants[1].title == "Bandler / cinematográfica"
    assert artifacts[0].comparison_variants[0].status == "pending"
    assert artifacts[0].comparison_variants[1].status == "pending"
    assert artifacts[0].comparison_variants[0].text == ""
    assert artifacts[0].comparison_variants[1].text == ""
    assert interpretation is not None


def test_build_assistant_message_keeps_exploring_before_three_llm_questions():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="refine_selected",
        user_input=(
            "assistant: Descreva o problema em uma frase simples.\n"
            "user: Sei o que quero, mas fico adiando.\n"
            "assistant: Em qual desses mundos isso se encaixa?\n"
            "user: C\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais poetica\n"
            "assistant: Entao o centro continua claro.\n"
            "user: uma luta no ringue\n"
            "assistant: O que essa imagem faz com a cena quando o conflito aparece?\n"
            "user: uma luta de anos entre uma voz suave e um chiado agressivo"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
        receive_llm_question_count=2,
    )

    assert state == "refine_selected"
    assert "?" in message
    assert artifacts == []
    assert interpretation is not None


def test_build_assistant_message_uses_more_imagetic_machine_question_for_stuck_gear():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="refine_selected",
        user_input=(
            "assistant: Descreva o problema em uma frase simples.\n"
            "user: Estou travado para tomar uma decisão.\n"
            "assistant: Em qual desses mundos isso se encaixa?\n"
            "user: D\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais concreta\n"
            "assistant: Boa. Para seguir por maquina / engenharia...\n"
            "user: a engrenagem ta emperrada"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "refine_selected"
    assert "o que essa engrenagem precisa destravar" in message.lower()
    assert "movimento você está tentando fazer" not in message.lower()
    assert artifacts == []
    assert interpretation is not None


def test_build_assistant_message_uses_more_imagetic_machine_question_for_lever():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="refine_selected",
        user_input=(
            "assistant: Descreva o problema em uma frase simples.\n"
            "user: Estou travado para tomar uma decisão.\n"
            "assistant: Em qual desses mundos isso se encaixa?\n"
            "user: D\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais concreta\n"
            "assistant: Boa. Para seguir por maquina / engenharia...\n"
            "user: uma alavanca com pessoas fortes"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "refine_selected"
    assert "o que faz essa alavanca ter força de verdade" in message.lower()
    assert "aspecto concreto da alavanca" not in message.lower()
    assert artifacts == []
    assert interpretation is not None


def test_build_assistant_message_asks_for_tactic_not_spectacle_in_war_field():
    state, message, artifacts, interpretation = build_assistant_message(
        mode="receive",
        state="refine_selected",
        user_input=(
            "assistant: Descreva o problema em uma frase simples.\n"
            "user: Sei o que quero, mas fico adiando.\n"
            "assistant: Em qual desses mundos isso se encaixa?\n"
            "user: B\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais concreta\n"
            "assistant: Boa. Para seguir por guerra / estrategia...\n"
            "user: uma muralha gigante\n"
            "assistant: Entao, ao olhar essa muralha gigante...\n"
            "user: uma muralha forte e densa\n"
            "assistant: Entao, ao encarar essa muralha forte e densa...\n"
            "user: nao consigo passar por ela\n"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "refine_selected"
    lowered = message.lower()
    assert "ritmo" in lowered or "mirar" in lowered or "janela" in lowered or "alcance" in lowered
    assert "romper ou contornar essa barreira" not in lowered
    assert artifacts == []
    assert interpretation is not None


def test_local_provider_receive_final_response_preserves_user_war_scene_instead_of_generic_machine():
    from app.prompts import RECEIVE_FINAL_BANDLER_PROMPT, RECEIVE_FINAL_ERICKSON_PROMPT
    from app.providers.local_provider import LocalProvider

    provider = LocalProvider()
    transcript = (
        "assistant: Descreva o problema em uma frase simples.\n"
        "user: Sei o que quero, mas fico adiando.\n"
        "assistant: Em qual desses mundos isso se encaixa?\n"
        "user: B\n"
        "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
        "user: mais concreta\n"
        "assistant: Boa. Para seguir por guerra / estrategia...\n"
        "user: uma muralha gigante\n"
        "assistant: Entao, ao olhar essa muralha gigante...\n"
        "user: uma muralha forte e densa\n"
        "assistant: Entao, a muralha parece intransponivel...\n"
        "user: uma catapulta\n"
    )

    erickson = provider.invoke_chat(RECEIVE_FINAL_ERICKSON_PROMPT, transcript).lower()
    bandler = provider.invoke_chat(RECEIVE_FINAL_BANDLER_PROMPT, transcript).lower()

    assert "muralha" in erickson
    assert "catapulta" in erickson
    assert "máquina imensa" not in erickson
    assert "muralha" in bandler
    assert "catapulta" in bandler
    assert "máquina" not in bandler


def test_message_endpoint_receive_mode_final_keeps_user_mechanism_and_avoids_epic_cliches(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())
    monkeypatch.setattr(
        "app.main._load_provider_config",
        lambda _db: __import__("app.main", fromlist=["ProviderConfig"]).ProviderConfig(
            provider="local",
            model="",
        ),
    )

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "Sei o que quero, mas fico adiando."})
        client.post("/api/chat/message", json={"token": token, "content": "B"})
        client.post("/api/chat/message", json={"token": token, "content": "mais concreta"})
        client.post("/api/chat/message", json={"token": token, "content": "uma muralha gigante"})
        client.post("/api/chat/message", json={"token": token, "content": "uma muralha forte e densa"})
        client.post("/api/chat/message", json={"token": token, "content": "nao consigo passar por ela"})
        response = client.post("/api/chat/message", json={"token": token, "content": "uma catapulta"})

        final_body = None
        for _ in range(200):
            restored = client.get(f"/api/chat/session/{token}")
            assert restored.status_code == 200
            candidate = restored.json()
            final_artifact = candidate["artifacts"][-1]
            statuses = [variant["status"] for variant in final_artifact["comparison_variants"]]
            if statuses == ["complete", "complete"]:
                final_body = candidate
                break
            time.sleep(0.05)

    assert response.status_code == 200
    assert final_body is not None
    joined = " ".join(variant["text"].lower() for variant in final_body["artifacts"][-1]["comparison_variants"])
    assert "muralha" in joined
    assert "catapulta" in joined
    assert "céu de chumbo" not in joined
    assert "raio distante" not in joined
    assert "máquina imensa" not in joined


def test_coach_prompt_pushes_war_field_toward_tactic_instead_of_symbol_explanation():
    from app.prompts import COACH_PROMPT

    lowered = COACH_PROMPT.lower()
    assert "war / strategy" in lowered
    assert "tactic" in lowered
    assert "timing" in lowered
    assert "ask what it guards" not in lowered
    assert "ask what it blocks" not in lowered


def test_receive_final_prompts_forbid_ornamental_cliche_language_seen_in_browser():
    from app.prompts import RECEIVE_FINAL_BANDLER_PROMPT, RECEIVE_FINAL_ERICKSON_PROMPT

    erickson_lowered = RECEIVE_FINAL_ERICKSON_PROMPT.lower()
    bandler_lowered = RECEIVE_FINAL_BANDLER_PROMPT.lower()

    for lowered in (erickson_lowered, bandler_lowered):
        assert "ornamental adjectives" in lowered
        assert "stone-black walls" not in lowered
        assert "heart-like openings" not in lowered

    for lowered in (erickson_lowered, bandler_lowered):
        for fragment in ("heart", "light", "shadow", "black stone", "heroic corridor"):
            assert fragment in lowered


def test_receive_final_prompts_push_finer_style_split_for_real_provider():
    from app.prompts import RECEIVE_FINAL_BANDLER_PROMPT, RECEIVE_FINAL_ERICKSON_PROMPT

    erickson_lowered = RECEIVE_FINAL_ERICKSON_PROMPT.lower()
    bandler_lowered = RECEIVE_FINAL_BANDLER_PROMPT.lower()

    assert "use understatement, implication, and small sensory shifts" in erickson_lowered
    assert "avoid muscular pep-talk cadence" in erickson_lowered
    assert "privilege calibration, repetition, leverage, contact, recoil, and structural response" in bandler_lowered
    assert "avoid lyrical narration" in bandler_lowered


def test_receive_final_erickson_prompt_forbids_grandiose_shortcuts():
    from app.prompts import RECEIVE_FINAL_ERICKSON_PROMPT

    lowered = RECEIVE_FINAL_ERICKSON_PROMPT.lower()
    assert "avoid horizon, destiny, revelation, unexpected path, or majestic scale" in lowered
    assert "prefer nearby detail over panoramic grandeur" in lowered


def test_interpret_turn_marks_user_metaphor_when_user_supplies_new_image():
    from app.agents import interpret_turn
    from app.providers.local_provider import LocalProvider

    result = interpret_turn(
        LocalProvider(),
        current_state="present_choices",
        user_input=("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: um barco perdido no oceano"),
    )

    assert result.intent == "user_introduced_metaphor"
    assert result.active_metaphor_seed == "um barco perdido no oceano"


def test_interpret_turn_uses_turn_interpreter_prompt_and_provider_response():
    from app.agents import interpret_turn
    from app.prompts import TURN_INTERPRETER_PROMPT

    class RecordingProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            self.calls.append((system_prompt, user_prompt))
            return (
                '{"intent":"refinement_request","active_metaphor_seed":null,'
                '"sensory_mode":"verbal","suggestion_basis":"user-asked-to-adjust-wording"}'
            )

    provider = RecordingProvider()

    result = interpret_turn(
        provider,
        current_state="present_choices",
        user_input=("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: mais curta"),
    )

    assert provider.calls
    assert provider.calls[0][0] == TURN_INTERPRETER_PROMPT
    assert "present_choices" in provider.calls[0][1]
    assert "mais curta" in provider.calls[0][1]
    assert result.intent == "refinement_request"
    assert result.sensory_mode == "verbal"
    assert result.suggestion_basis == "user-asked-to-adjust-wording"


def test_interpret_turn_falls_back_deterministically_when_provider_payload_is_invalid():
    from app.agents import interpret_turn

    class InvalidPayloadProvider:
        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            return "isso não é json"

    result = interpret_turn(
        InvalidPayloadProvider(),
        current_state="present_choices",
        user_input=("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: não sei"),
    )

    assert result.intent == "ambiguous"
    assert result.suggestion_basis == "deterministic-fallback"


def test_interpret_turn_falls_back_deterministically_when_provider_raises():
    from app.agents import interpret_turn

    class ExplodingProvider:
        def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("provider timeout")

    result = interpret_turn(
        ExplodingProvider(),
        current_state="present_choices",
        user_input=("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: sei lá"),
    )

    assert result.intent == "ambiguous"
    assert result.suggestion_basis == "deterministic-fallback"


@pytest.mark.parametrize(
    ("user_input", "expected_intent"),
    [
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: B", "agent_option_selection"),
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: E", "agent_option_selection"),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\nuser: um barco perdido no oceano",
            "user_introduced_metaphor",
        ),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\nuser: barco perdido no oceano",
            "user_introduced_metaphor",
        ),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\nuser: como barco perdido no oceano",
            "user_introduced_metaphor",
        ),
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: mais curta", "refinement_request"),
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: reescreve", "refinement_request"),
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: não sei", "ambiguous"),
        ("assistant: Escolha a imagem que mais acerta o problema agora.\nuser: sei lá", "ambiguous"),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\nuser: tenho um problema no trabalho",
            "problem_statement",
        ),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\n"
            "user: tenho uma conversa difícil com meu chefe",
            "problem_statement",
        ),
        (
            "assistant: Escolha a imagem que mais acerta o problema agora.\nuser: preciso ajustar isso no trabalho",
            "problem_statement",
        ),
    ],
)
def test_interpret_turn_covers_task_2_intents_without_article_false_positive(user_input, expected_intent):
    from app.agents import interpret_turn
    from app.providers.local_provider import LocalProvider

    result = interpret_turn(
        LocalProvider(),
        current_state="present_choices",
        user_input=user_input,
    )

    assert result.intent == expected_intent


def test_generate_contextual_choices_fallback_stays_in_user_semantic_field():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "estou bloqueado")

    choice_texts = [choice.text.lower() for choice in artifact.choices]
    assert "natureza: plantio, colheita, raiz, crescimento." in choice_texts
    assert "guerra / estratégia: batalha, território, ataque, defesa." in choice_texts
    assert "jornada / viagem: caminho, mapa, destino." in choice_texts


def test_generate_contextual_choices_for_estou_preso_stays_in_stuck_semantic_field():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "estou preso")

    choice_texts = [choice.text.lower() for choice in artifact.choices]
    joined = " ".join(choice_texts)
    assert "natureza: plantio" in joined
    assert "guerra / estratégia" in joined
    assert "jornada / viagem" in joined
    assert "corredor estreito entupido de caixas" not in joined
    assert "motor que gira e nao engata" not in joined
    assert "agua presa atras de uma comporta" not in joined


@pytest.mark.parametrize("user_input", ["estou com pressa", "estou atravessado com isso"])
def test_generate_contextual_choices_does_not_force_stuck_field_for_partial_word_matches(user_input):
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), user_input)

    joined = " ".join(choice.text.lower() for choice in artifact.choices)
    assert "corredor estreito entupido de caixas" not in joined
    assert "motor que gira e não engata" not in joined
    assert "água presa atrás de uma comporta" not in joined


def test_generate_contextual_choices_avoids_rigid_quiz_framing():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "estou bloqueado")

    assert "Escolha A, B ou C" not in artifact.content
    assert "escolha a imagem" not in artifact.content.lower()
    assert artifact.content.lower().startswith("em qual desses mundos isso se encaixa")


def test_generate_contextual_choices_preserves_user_metaphor_field():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "um barco perdido no oceano")

    joined = " ".join(choice.text.lower() for choice in artifact.choices)
    assert "natureza: plantio" in joined
    assert "guerra / estratégia" in joined
    assert "energia / física" in joined
    assert "barco" not in joined
    assert "oceano" not in joined


def test_hydrate_receive_choice_artifact_preserves_contextual_copy():
    from app.agents import generate_contextual_choices, hydrate_receive_choice_artifact
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "um barco perdido no oceano")
    hydrated = hydrate_receive_choice_artifact(artifact.content, artifact.metadata)

    assert hydrated.content == artifact.content
    assert "Escolha A, B ou C" not in hydrated.content
    assert hydrated.content.lower().startswith("em qual desses mundos isso se encaixa")
