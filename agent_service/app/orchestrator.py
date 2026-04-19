from __future__ import annotations

from collections.abc import Callable

from app.agents import (
    TurnInterpretation,
    build_receive_concrete_anchor_prompt,
    coach_metaphor,
    finalize_receive_metaphor,
    generate_symbolic_world_choices,
    has_receive_concrete_anchor,
    interpret_turn,
    should_finalize_receive_response,
)
from app.schemas import ArtifactView
from app.state_machine import next_state

START_PROMPT_BY_MODE = {
    "receive": "Descreva o problema em uma frase simples.",
    "build": "Descreva o problema em uma frase simples.",
}

RECEIVE_SYMBOLIC_GUIDE_MESSAGE = "Escolha o mundo que mais encaixa. Depois eu desenvolvo a metáfora por esse caminho."

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
    receive_llm_question_count: int = 0,
) -> tuple[str, str, list[ArtifactView], TurnInterpretation | None]:
    if mode == "receive":
        if state == "intake_problem":
            return state, "Descreva o problema em uma frase simples.", [], None
        if state == "generate_candidates":
            artifact = generate_symbolic_world_choices()
            return "present_choices", RECEIVE_SYMBOLIC_GUIDE_MESSAGE, [artifact], None
        if state in {"present_choices", "refine_selected"}:
            interpretation = interpret_turn(provider_factory(), current_state=state, user_input=user_input)
            if interpretation.intent == "agent_option_selection":
                interpretation.assistant_response_kind = "receive_refinement_prompt"
                return "refine_selected", REFINE_SELECTED_MESSAGE, [], interpretation
            if state == "present_choices":
                interpretation.assistant_response_kind = "receive_symbolic_world_prompt"
                artifact = generate_symbolic_world_choices()
                return "present_choices", RECEIVE_SYMBOLIC_GUIDE_MESSAGE, [artifact], interpretation
            if interpretation.intent == "refinement_request" and not has_receive_concrete_anchor(user_input):
                interpretation.assistant_response_kind = "receive_concrete_anchor_prompt"
                return "refine_selected", build_receive_concrete_anchor_prompt(user_input), [], interpretation
            provider = provider_factory()
            if should_finalize_receive_response(state, user_input, interpretation, receive_llm_question_count):
                interpretation.assistant_response_kind = "receive_llm_final"
                return "refine_selected", finalize_receive_metaphor(provider, user_input), [], interpretation
            if interpretation.intent in {"user_introduced_metaphor", "refinement_request", "problem_statement"}:
                interpretation.assistant_response_kind = "receive_llm_question"
                return "refine_selected", coach_metaphor(provider, user_input), [], interpretation
            interpretation.assistant_response_kind = "receive_symbolic_world_prompt"
            artifact = generate_symbolic_world_choices()
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
