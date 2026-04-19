import pytest
from app.db import SessionLocal
from app.main import create_app
from app.models import SessionRecord
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
    assert artifact["content"] == body["messages"][-1]["content"]
    assert artifact["metadata"] == {
        "clarifier_asked": False,
        "internal_candidate_count": 3,
        "selected_option": None,
    }
    assert [choice["label"] for choice in artifact["choices"]] == ["A", "B", "C"]
    assert all(choice["text"] for choice in artifact["choices"])
    assert "possibilidades" in body["messages"][-1]["content"].lower()
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
        "internal_candidate_count": 3,
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
    assert body["state"] == "refine_selected"
    assert "barco" in body["assistant_message"].lower() or "oceano" in body["assistant_message"].lower()

    restored_body = restored.json()
    assert restored_body["state"] == "refine_selected"


def test_message_endpoint_refinement_request_in_present_choices_skips_literal_selection(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})

        response = client.post("/api/chat/message", json={"token": token, "content": "mais curta"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "refine_selected"
    assert "mais curta" not in body["assistant_message"].lower()
    assert body["messages"][-1]["role"] == "assistant"


def test_message_endpoint_contextual_receive_suggestions_match_problem_language(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        response = client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})

    assert response.status_code == 200
    body = response.json()
    choice_texts = [choice["text"].lower() for choice in body["artifacts"][0]["choices"]]
    assert any("motor" in text or "corredor" in text or "comporta" in text for text in choice_texts)


def test_message_endpoint_refinement_request_keeps_active_metaphor_context(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "estou bloqueado"})
        client.post("/api/chat/message", json={"token": token, "content": "um barco perdido no oceano"})
        response = client.post("/api/chat/message", json={"token": token, "content": "mais concreta"})

    assert response.status_code == 200
    assert (
        "barco" in response.json()["assistant_message"].lower()
        or "oceano" in response.json()["assistant_message"].lower()
    )


def test_message_endpoint_receive_mode_converges_to_final_metaphor(tmp_path, monkeypatch):
    from app.providers.local_provider import LocalProvider

    monkeypatch.setattr("app.main.resolve_provider", lambda _db: LocalProvider())

    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api-flow.db")) as client:
        token = client.post("/api/chat/start", json={"mode": "receive"}).json()["token"]
        client.post("/api/chat/message", json={"token": token, "content": "Sei o que quero, mas fico adiando."})
        client.post("/api/chat/message", json={"token": token, "content": "C"})
        client.post("/api/chat/message", json={"token": token, "content": "mais poética"})
        client.post("/api/chat/message", json={"token": token, "content": "uma luta no ringue"})
        response = client.post(
            "/api/chat/message",
            json={"token": token, "content": "uma luta de anos entre uma voz suave e um chiado agressivo"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "refine_selected"
    assert "?" not in body["assistant_message"]
    assert "luta" in body["assistant_message"].lower()
    assert "chiado" in body["assistant_message"].lower()


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
        client.post("/api/chat/message", json={"token": token, "content": "um barco perdido no oceano"})
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
    assert persisted.active_metaphor_seed == "um barco perdido no oceano"
    assert (
        "barco" in response.json()["assistant_message"].lower()
        or "oceano" in response.json()["assistant_message"].lower()
    )


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
    assert [choice["label"] for choice in body["artifacts"][0]["choices"]] == ["A", "B", "C"]
    assert "possibilidades" in body["messages"][-1]["content"].lower()
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
            "assistant: Aqui vao tres possibilidades para seguir nessa imagem.\n"
            "user: C\n"
            "assistant: Boa. Agora diga como voce quer ajustar essa opcao.\n"
            "user: mais poetica\n"
            "assistant: Entao o centro continua claro.\n"
            "user: uma luta no ringue\n"
            "assistant: O que essa imagem faz com a cena quando o conflito aparece?\n"
            "user: uma luta de anos entre uma voz suave e um chiado agressivo"
        ),
        provider_factory=lambda: __import__("app.providers.local_provider", fromlist=["LocalProvider"]).LocalProvider(),
    )

    assert state == "refine_selected"
    assert "?" not in message
    assert "luta" in message.lower()
    assert artifacts == []
    assert interpretation is not None


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
    assert any("bloque" in text or "trav" in text or "pres" in text for text in choice_texts)


def test_generate_contextual_choices_for_estou_preso_stays_in_stuck_semantic_field():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "estou preso")

    choice_texts = [choice.text.lower() for choice in artifact.choices]
    joined = " ".join(choice_texts)
    assert "carro girando em falso na lama" not in joined
    assert "gaveta emperrada" not in joined
    assert "três rádios ligados ao mesmo tempo" not in joined
    assert any("pres" in text or "trav" in text or "bloque" in text for text in choice_texts)


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


def test_generate_contextual_choices_preserves_user_metaphor_field():
    from app.agents import generate_contextual_choices
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "um barco perdido no oceano")

    joined = " ".join(choice.text.lower() for choice in artifact.choices)
    assert "barco" in joined or "oceano" in joined
    assert "carro girando em falso na lama" not in joined
    assert "gaveta emperrada" not in joined
    assert "três rádios ligados ao mesmo tempo" not in joined


def test_hydrate_receive_choice_artifact_preserves_contextual_copy():
    from app.agents import generate_contextual_choices, hydrate_receive_choice_artifact
    from app.providers.local_provider import LocalProvider

    artifact = generate_contextual_choices(LocalProvider(), "um barco perdido no oceano")
    hydrated = hydrate_receive_choice_artifact(artifact.content, artifact.metadata)

    assert hydrated.content == artifact.content
    assert "Escolha A, B ou C" not in hydrated.content
