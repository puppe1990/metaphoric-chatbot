from __future__ import annotations

from collections.abc import Callable

from app.agents import (
    coach_metaphor,
    generate_receive_choices,
)
from app.schemas import ArtifactView
from app.state_machine import next_state

START_PROMPT_BY_MODE = {
    "receive": "Descreva o problema em uma frase simples.",
    "build": "Descreva o problema em uma frase simples.",
}

REFINE_SELECTED_MESSAGE = (
    "Boa. Agora diga como você quer ajustar essa opção: mais curta, mais concreta, mais poética ou mais direta."
)


def start_assistant_message(mode: str) -> str:
    try:
        return START_PROMPT_BY_MODE[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported session mode: {mode!r}") from exc


def build_assistant_message(
    mode: str,
    state: str,
    user_input: str,
    provider_factory: Callable[[], object],
) -> tuple[str, str, list[ArtifactView]]:
    if mode == "receive":
        if state == "intake_problem":
            return state, "Descreva o problema em uma frase simples.", []
        if state == "generate_candidates":
            artifact = generate_receive_choices(provider_factory(), user_input)
            return "present_choices", artifact.content, [artifact]
        if state == "present_choices":
            return state, "Escolha A, B ou C para continuarmos.", []
        if state == "refine_selected":
            return state, REFINE_SELECTED_MESSAGE, []

    if mode == "build":
        if state == "intake_problem":
            return state, "Descreva o problema em uma frase simples.", []
        if state == "identify_core_conflict":
            return state, "Se isso tivesse um conflito central, qual seria em poucas palavras?", []
        if state == "offer_symbolic_fields":
            return (
                state,
                "Isso parece mais uma porta emperrada, um rio barrado, uma engrenagem "
                "presa, um motor acelerado ou uma bússola girando?",
                [],
            )
        if state in {"user_selects_symbol", "user_attempt", "coach_feedback", "rewrite_together"}:
            return state, coach_metaphor(provider_factory(), user_input), []

    return state, "Vamos continuar.", []


def advance_mode(mode: str, current_state: str) -> str:
    return next_state(mode, current_state)
