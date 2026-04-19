from __future__ import annotations

from collections.abc import Callable

from app.agents import (
    TurnInterpretation,
    coach_metaphor,
    finalize_receive_metaphor,
    generate_contextual_choices,
    interpret_turn,
    should_finalize_receive_response,
)
from app.schemas import ArtifactView
from app.state_machine import next_state

START_PROMPT_BY_MODE = {
    "receive": "Descreva o problema em uma frase simples.",
    "build": "Descreva o problema em uma frase simples.",
}

RECEIVE_SYMBOLIC_GUIDE_MESSAGE = (
    "Para achar sua metáfora, veja qual desses mundos encaixa melhor. "
    "Se algum encaixar, eu desenvolvo por esse caminho."
)

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
) -> tuple[str, str, list[ArtifactView], TurnInterpretation | None]:
    if mode == "receive":
        if state == "intake_problem":
            return state, "Descreva o problema em uma frase simples.", [], None
        if state == "generate_candidates":
            provider = provider_factory()
            artifact = generate_contextual_choices(provider, user_input)
            interpretation = interpret_turn(provider, current_state=state, user_input=user_input)
            return "present_choices", RECEIVE_SYMBOLIC_GUIDE_MESSAGE, [artifact], interpretation
        if state in {"present_choices", "refine_selected"}:
            provider = provider_factory()
            interpretation = interpret_turn(provider, current_state=state, user_input=user_input)
            if interpretation.intent == "agent_option_selection":
                return "refine_selected", REFINE_SELECTED_MESSAGE, [], interpretation
            if should_finalize_receive_response(state, user_input, interpretation):
                return "refine_selected", finalize_receive_metaphor(provider, user_input), [], interpretation
            if interpretation.intent in {"user_introduced_metaphor", "refinement_request", "problem_statement"}:
                return "refine_selected", coach_metaphor(provider, user_input), [], interpretation
            artifact = generate_contextual_choices(provider, user_input)
            return "present_choices", RECEIVE_SYMBOLIC_GUIDE_MESSAGE, [artifact], interpretation

    if mode == "build":
        if state == "intake_problem":
            return state, "Descreva o problema em uma frase simples.", [], None
        if state == "identify_core_conflict":
            return state, "Se isso tivesse um conflito central, qual seria em poucas palavras?", [], None
        if state == "offer_symbolic_fields":
            return (
                state,
                (
                    "Isso se encaixa mais em natureza, guerra/estratégia, "
                    "jornada/viagem, máquina/engenharia ou energia/física?"
                ),
                [],
                None,
            )
        if state in {"user_selects_symbol", "user_attempt", "coach_feedback", "rewrite_together"}:
            return state, coach_metaphor(provider_factory(), user_input), [], None

    return state, "Vamos continuar.", [], None


def advance_mode(mode: str, current_state: str) -> str:
    return next_state(mode, current_state)
