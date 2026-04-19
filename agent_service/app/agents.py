from __future__ import annotations

import json
import re

from pydantic import BaseModel

from .prompts import (
    COACH_PROMPT,
    EXTRACTOR_PROMPT,
    GENERATOR_PROMPT,
    RECEIVE_CHOICES_PROMPT,
    RECEIVE_CONTEXTUAL_PROMPT,
    TURN_INTERPRETER_PROMPT,
)
from .providers.base import ChatProvider
from .schemas import ArtifactMetadata, ArtifactView, MetaphorChoice, TurnIntent

CHOICE_LABELS = ("A", "B", "C")
CHOICE_PATTERN = re.compile(r"(?ims)^\s*([ABC])\s*[\.\):-]\s*(.+?)(?=^\s*[ABC]\s*[\.\):-]\s*|\Z)")


class TurnInterpretation(BaseModel):
    intent: TurnIntent
    active_metaphor_seed: str | None = None
    sensory_mode: str | None = None
    suggestion_basis: str | None = None


def extract_symbolic_structure(provider: ChatProvider, user_input: str) -> str:
    return provider.invoke_chat(EXTRACTOR_PROMPT, user_input)


def generate_metaphor(provider: ChatProvider, user_input: str) -> str:
    return provider.invoke_chat(GENERATOR_PROMPT, user_input)


def coach_metaphor(provider: ChatProvider, user_input: str) -> str:
    return provider.invoke_chat(COACH_PROMPT, user_input)


def interpret_turn(provider: ChatProvider, current_state: str, user_input: str) -> TurnInterpretation:
    prompt_input = f"current_state: {current_state}\n{user_input}"
    try:
        raw_output = provider.invoke_chat(TURN_INTERPRETER_PROMPT, prompt_input)
    except Exception:
        return _fallback_turn_interpretation(user_input)
    parsed = _parse_turn_interpretation(raw_output)
    if parsed is not None:
        return parsed
    return _fallback_turn_interpretation(user_input)


def generate_receive_choices(provider: ChatProvider, user_input: str) -> ArtifactView:
    raw_output = provider.invoke_chat(RECEIVE_CHOICES_PROMPT, user_input)
    choices = _parse_receive_choices(raw_output)
    if choices is None:
        choices = _fallback_receive_choices(user_input)

    content = _format_receive_choices_content(choices)
    return ArtifactView(
        artifact_type="receive_choice",
        content=content,
        metadata=ArtifactMetadata(
            clarifier_asked=False,
            internal_candidate_count=len(choices),
            selected_option=None,
        ),
        choices=choices,
    )


def generate_contextual_choices(provider: ChatProvider, user_input: str) -> ArtifactView:
    raw_output = provider.invoke_chat(RECEIVE_CONTEXTUAL_PROMPT, user_input)
    choices = _parse_receive_choices(raw_output) or _fallback_receive_choices(user_input)
    return ArtifactView(
        artifact_type="receive_choice",
        content=_format_contextual_choices_content(choices),
        metadata=ArtifactMetadata(
            clarifier_asked=False,
            internal_candidate_count=len(choices),
            selected_option=None,
        ),
        choices=choices,
    )


def hydrate_receive_choice_artifact(
    content: str,
    metadata: ArtifactMetadata | dict[str, object] | None,
) -> ArtifactView:
    choices = _parse_receive_choices(content)
    if choices is None:
        choices = _fallback_receive_choices(content)

    metadata_model = ArtifactMetadata.model_validate(metadata or {})
    return ArtifactView(
        artifact_type="receive_choice",
        content=content if _is_contextual_choice_content(content) else _format_receive_choices_content(choices),
        metadata=metadata_model,
        choices=choices,
    )


def _parse_receive_choices(raw_output: str) -> list[MetaphorChoice] | None:
    matches = list(CHOICE_PATTERN.finditer(raw_output.strip()))
    if not matches:
        return None

    choice_map: dict[str, MetaphorChoice] = {}
    for match in matches:
        label = match.group(1).upper()
        text = _normalize_choice_text(match.group(2))
        if label in choice_map or not text:
            return None
        choice_map[label] = MetaphorChoice(label=label, text=text)

    if set(choice_map) != set(CHOICE_LABELS):
        return None

    return [choice_map[label] for label in CHOICE_LABELS]


def _normalize_choice_text(text: str) -> str:
    compact = " ".join(line.strip() for line in text.strip().splitlines() if line.strip())
    compact = re.sub(r"\s+", " ", compact)
    compact = re.sub(r"\s*Escolha\s+A,\s*B\s+ou\s+C\.?\s*$", "", compact, flags=re.IGNORECASE)
    return compact.strip(" -")


def _fallback_receive_choices(user_input: str) -> list[MetaphorChoice]:
    problem = _latest_user_problem(user_input).rstrip(".!?")
    scene = problem or "isso"
    normalized_problem = problem.lower()

    if _has_sea_metaphor_language(normalized_problem):
        return [
            MetaphorChoice(label="A", text="Como um barco sem bússola rodando em círculos no mesmo trecho do oceano."),
            MetaphorChoice(label="B", text="Como um casco pequeno apanhando de ondas grandes sem ver a costa."),
            MetaphorChoice(label="C", text="Como um barco perdido sob neblina, ouvindo o mar mas sem achar direção."),
        ]

    if _has_stuck_language(normalized_problem):
        return [
            MetaphorChoice(label="A", text="Como um corredor estreito entupido de caixas."),
            MetaphorChoice(label="B", text="Como um motor que gira e nao engata."),
            MetaphorChoice(label="C", text="Como agua presa atras de uma comporta."),
        ]

    return [
        MetaphorChoice(
            label="A",
            text=f"Como um carro girando em falso na lama: faz força demais e ainda assim não sai do lugar em {scene}.",
        ),
        MetaphorChoice(
            label="B",
            text=f"Como uma gaveta emperrada: você puxa, hesita, solta, e tudo fica preso no meio em {scene}.",
        ),
        MetaphorChoice(
            label="C",
            text=(
                "Como três rádios ligados ao mesmo tempo: sinais disputam espaço "
                f"e nenhuma música consegue abrir caminho em {scene}."
            ),
        ),
    ]


def _latest_user_problem(user_input: str) -> str:
    user_lines = [
        line.split(":", 1)[1].strip()
        for line in user_input.splitlines()
        if line.lower().startswith("user:") and ":" in line
    ]
    if user_lines:
        return user_lines[-1]
    return user_input.strip()


def _parse_turn_interpretation(raw_output: str) -> TurnInterpretation | None:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return TurnInterpretation.model_validate(payload)
    except Exception:
        return None


def _fallback_turn_interpretation(user_input: str) -> TurnInterpretation:
    latest = _latest_user_problem(user_input)
    normalized = latest.strip().lower()

    if latest.upper() in CHOICE_LABELS:
        return TurnInterpretation(intent="agent_option_selection", suggestion_basis="deterministic-fallback")

    if _is_ambiguous_reply(normalized):
        return TurnInterpretation(intent="ambiguous", suggestion_basis="deterministic-fallback")

    if _is_refinement_request(normalized):
        return TurnInterpretation(
            intent="refinement_request",
            sensory_mode="verbal",
            suggestion_basis="deterministic-fallback",
        )

    if _looks_like_user_metaphor(normalized):
        return TurnInterpretation(
            intent="user_introduced_metaphor",
            active_metaphor_seed=latest,
            sensory_mode="visual",
            suggestion_basis="deterministic-fallback",
        )

    return TurnInterpretation(
        intent="problem_statement",
        sensory_mode="kinesthetic",
        suggestion_basis="deterministic-fallback",
    )


def _is_ambiguous_reply(normalized: str) -> bool:
    return normalized in {
        "não sei",
        "nao sei",
        "talvez",
        "tanto faz",
        "não tenho certeza",
        "nao tenho certeza",
        "sei lá",
        "sei la",
    }


def _is_refinement_request(normalized: str) -> bool:
    direct_markers = {
        "mais curta",
        "mais curto",
        "mais concreta",
        "mais concreto",
        "mais direta",
        "mais direto",
        "mais poética",
        "mais poetica",
        "menos poética",
        "menos poetica",
        "reescreve",
        "reescrever",
        "ajusta",
        "ajusta isso",
    }
    if normalized in direct_markers:
        return True
    return bool(re.match(r"^(reescreve|reescrever|ajusta)\b", normalized, flags=re.IGNORECASE))


def _looks_like_user_metaphor(normalized: str) -> bool:
    concrete_image_markers = (
        "barco",
        "navio",
        "oceano",
        "mar",
        "costa",
        "bussola",
        "bússola",
        "onda",
        "ondas",
        "neblina",
        "rio",
        "porta",
        "gaveta",
        "motor",
        "corredor",
    )

    literal_problem_markers = (
        "problema",
        "dificuldade",
        "conflito",
        "situação",
        "situacao",
        "questão",
        "questao",
        "coisa",
        "negócio",
        "negocio",
        "trabalho",
        "conversa",
        "reunião",
        "reuniao",
        "discussão",
        "discussao",
        "chefe",
    )
    if any(marker in normalized for marker in literal_problem_markers):
        return False

    article_led = re.match(r"^(?:(?:como|parece|soa como|vira|e como)\s+)?(um|uma)\b", normalized, flags=re.IGNORECASE)
    if article_led:
        return True

    return any(
        re.search(rf"\b{re.escape(marker)}\b", normalized, flags=re.IGNORECASE) for marker in concrete_image_markers
    )


def _has_stuck_language(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(bloquead[oa]s?|bloqueio|travad[oa]s?|trava(?:do|da)?|pres[oa]s?)\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _has_sea_metaphor_language(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(barco|navio|oceano|mar|costa|bússola|bussola|onda|ondas|neblina)\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _is_contextual_choice_content(content: str) -> bool:
    lowered = content.lower()
    return "aqui vao tres possibilidades" in lowered and "escolha a imagem" not in lowered


def _format_receive_choices_content(choices: list[MetaphorChoice]) -> str:
    lines = ["Escolha a imagem que mais acerta o problema agora:"]
    lines.extend(f"{choice.label}. {choice.text}" for choice in choices)
    lines.append("Escolha A, B ou C.")
    return "\n".join(lines)


def _format_contextual_choices_content(choices: list[MetaphorChoice]) -> str:
    lines = ["Aqui vao tres possibilidades para seguir nessa imagem:"]
    lines.extend(f"{choice.label}. {choice.text}" for choice in choices)
    lines.append("Se alguma acertar, eu desenvolvo por esse caminho.")
    return "\n".join(lines)
