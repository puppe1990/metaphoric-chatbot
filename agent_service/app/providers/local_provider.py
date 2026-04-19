from __future__ import annotations

import json
import re

from app.prompts import (
    COACH_PROMPT,
    EXTRACTOR_PROMPT,
    GENERATOR_PROMPT,
    RECEIVE_CHOICES_PROMPT,
    RECEIVE_CONTEXTUAL_PROMPT,
    RECEIVE_FINAL_PROMPT,
    TURN_INTERPRETER_PROMPT,
)


class LocalProvider:
    def invoke_chat(self, system_prompt: str, user_prompt: str) -> str:
        if system_prompt == EXTRACTOR_PROMPT:
            return (
                "Entendi o mapa básico: há um problema nomeado, uma sensação dominante "
                "e uma mudança desejada. Vou usar isso para criar uma metáfora curta, "
                "concreta e sem diagnóstico."
            )

        if system_prompt == GENERATOR_PROMPT:
            return (
                "É como uma mesa cheia de papéis num dia de vento. A pressa tenta segurar "
                "tudo ao mesmo tempo, mas a clareza começa quando uma mão para, escolhe "
                "uma folha, e coloca um peso simples sobre o que importa agora."
            )

        if system_prompt == RECEIVE_CHOICES_PROMPT:
            return self._receive_choices_response(user_prompt)

        if system_prompt == TURN_INTERPRETER_PROMPT:
            latest = self._latest_user_line(user_prompt)
            latest_normalized = latest.strip().lower()
            if latest.upper() in {"A", "B", "C", "D", "E"}:
                return (
                    '{"intent":"agent_option_selection","active_metaphor_seed":null,'
                    '"sensory_mode":null,"suggestion_basis":"literal-choice"}'
                )
            if latest_normalized in {
                "não sei",
                "nao sei",
                "talvez",
                "tanto faz",
                "não tenho certeza",
                "nao tenho certeza",
                "sei lá",
                "sei la",
            }:
                return (
                    '{"intent":"ambiguous","active_metaphor_seed":null,'
                    '"sensory_mode":null,"suggestion_basis":"unclear-user-signal"}'
                )
            if any(
                latest_normalized == marker
                for marker in (
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
                )
            ) or re.match(r"^(reescreve|reescrever|ajusta)\b", latest_normalized, flags=re.IGNORECASE):
                return (
                    '{"intent":"refinement_request","active_metaphor_seed":null,'
                    '"sensory_mode":"verbal","suggestion_basis":"user-asked-to-adjust-wording"}'
                )
            if self._looks_like_user_metaphor(latest):
                return json.dumps(
                    {
                        "intent": "user_introduced_metaphor",
                        "active_metaphor_seed": latest,
                        "sensory_mode": "visual",
                        "suggestion_basis": "derived-from-user-image",
                    },
                    ensure_ascii=False,
                )
            return (
                '{"intent":"problem_statement","active_metaphor_seed":null,'
                '"sensory_mode":"kinesthetic","suggestion_basis":"derived-from-user-problem"}'
            )

        if system_prompt == RECEIVE_CONTEXTUAL_PROMPT:
            latest = self._latest_user_line(user_prompt).lower()
            if self._has_sea_metaphor_language(latest):
                return (
                    "A. Como um barco sem bússola rodando em círculos no mesmo trecho do oceano.\n"
                    "B. Como um casco pequeno apanhando de ondas grandes sem ver a costa.\n"
                    "C. Como um barco perdido sob neblina, ouvindo o mar mas sem achar direção.\n"
                    "D. Como uma rota marítima longa demais para ser lida sem mapa.\n"
                    "E. Como maré puxando para lados diferentes ao mesmo tempo.\n"
                )
            if self._has_stuck_language(latest):
                return (
                    "A. Como um corredor estreito entupido de caixas.\n"
                    "B. Como um motor que gira e não engata.\n"
                    "C. Como água presa atrás de uma comporta.\n"
                    "D. Como uma engrenagem travada segurando a máquina toda.\n"
                    "E. Como pressão acumulada sem conseguir sair.\n"
                )
            return self._contextual_choices_response(user_prompt)

        if system_prompt == RECEIVE_FINAL_PROMPT:
            return self._receive_final_response(user_prompt)

        if system_prompt == COACH_PROMPT:
            return self._coach_response(user_prompt)

        return user_prompt

    def _coach_response(self, user_prompt: str) -> str:
        user_lines = [
            line.split(":", 1)[1].strip()
            for line in user_prompt.splitlines()
            if line.lower().startswith("user:") and ":" in line
        ]
        latest = user_lines[-1] if user_lines else user_prompt.strip()
        previous = " ".join(user_lines[:-1])
        symbol = self._extract_symbol(previous) or "essa imagem"
        latest_lower = latest.lower()

        if self._is_refinement_request(latest_lower):
            return (
                f"Então o centro continua claro: {symbol}. "
                "O que deixa essa imagem mais nítida agora: a direção falha, a neblina fecha, ou a costa some?"
            )

        if any(verb in latest_lower for verb in ["falo", "digo", "solto", "faço"]):
            return (
                f"Então a cena já ganhou movimento: {symbol} aparece e solta uma bobagem grande. "
                f"A fala ainda está direta demais. O que essa bobagem derruba ou bagunça na cena?"
            )

        if latest and len(user_lines) <= 2:
            return (
                f"Então já existe uma direção: {latest} começa a dar corpo ao conflito. "
                "Qual é o sinal mais visível de que essa cena saiu do eixo?"
            )

        if latest:
            return (
                f"Então {latest} já pode ser o centro da imagem, sem precisar corrigir nada agora. "
                "O que essa imagem faz com a cena quando o conflito aparece?"
            )

        return "Então vamos partir de uma imagem concreta. O que ela faz no instante em que o conflito aparece?"

    def _receive_choices_response(self, user_prompt: str) -> str:
        user_lines = [
            line.split(":", 1)[1].strip()
            for line in user_prompt.splitlines()
            if line.lower().startswith("user:") and ":" in line
        ]
        latest = user_lines[-1] if user_lines else user_prompt.strip()
        scene = latest.rstrip(".!?") or "isso"

        return (
            "Escolha a imagem que mais acerta o problema agora:\n"
            f"A. Como um carro girando em falso na lama: faz barulho, força o motor, mas não sai do lugar em {scene}.\n"
            f"B. Como uma gaveta emperrada: você puxa, hesita, solta, e tudo fica preso no meio em {scene}.\n"
            "C. Como três rádios ligados ao mesmo tempo: sinais disputam espaço "
            f"e nenhuma música consegue abrir caminho em {scene}.\n"
            f"D. Como uma ponte longa demais para atravessar sem mapa em {scene}.\n"
            f"E. Como uma caldeira acumulando pressão por dentro em {scene}.\n"
            "Escolha uma opção para eu desenvolver."
        )

    def _contextual_choices_response(self, user_prompt: str) -> str:
        return (
            "Para achar sua metáfora, veja em qual mundo isso se encaixa melhor:\n"
            "A. Natureza: plantio, colheita, raiz, crescimento.\n"
            "B. Guerra / estratégia: batalha, território, ataque, defesa.\n"
            "C. Jornada / viagem: caminho, mapa, destino.\n"
            "D. Máquina / engenharia: sistema, engrenagem, processo.\n"
            "E. Energia / física: calor, pressão, força.\n"
            "Se algum desses mundos encaixar, eu desenvolvo a metáfora por esse caminho.\n"
            "Quando travar, pense: em qual desses mundos isso se encaixa?\n"
        )

    def _receive_final_response(self, user_prompt: str) -> str:
        user_lines = [
            line.split(":", 1)[1].strip()
            for line in user_prompt.splitlines()
            if line.lower().startswith("user:") and ":" in line
        ]
        substantive_lines = [
            line
            for line in user_lines
            if line
            and line.upper() not in {"A", "B", "C"}
            and not self._is_refinement_request(line.lower())
            and line.lower()
            not in {
                "não sei",
                "nao sei",
                "talvez",
                "tanto faz",
                "não tenho certeza",
                "nao tenho certeza",
                "sei lá",
                "sei la",
            }
        ]
        seed = substantive_lines[-1] if substantive_lines else "essa imagem"
        anchor = substantive_lines[-2] if len(substantive_lines) > 1 else "o conflito antigo"

        return (
            f"Fica como uma luta antiga no mesmo ringue: {anchor} segue ali, gastando força, "
            f"enquanto {seed} tenta atravessar o ruído sem desaparecer. E o que antes era só briga cega "
            "começa a virar um instante de definição, como se a cena finalmente mostrasse qual som ainda fica de pé."
        )

    def _extract_symbol(self, text: str) -> str | None:
        match = re.search(r"\b(um|uma)\s+([^.\n]+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{match.group(1).lower()} {match.group(2).strip()}"

    def _looks_like_user_metaphor(self, text: str) -> bool:
        normalized = text.strip().lower()
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

        if re.match(r"^(?:(?:como|parece|soa como|vira|e como)\s+)?(um|uma)\b", normalized, flags=re.IGNORECASE):
            return True

        return any(
            re.search(rf"\b{re.escape(marker)}\b", normalized, flags=re.IGNORECASE) for marker in concrete_image_markers
        )

    def _has_stuck_language(self, normalized: str) -> bool:
        return bool(
            re.search(
                r"\b(bloquead[oa]s?|bloqueio|travad[oa]s?|trava(?:do|da)?|pres[oa]s?)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _has_sea_metaphor_language(self, normalized: str) -> bool:
        return bool(
            re.search(
                r"\b(barco|navio|oceano|mar|costa|bússola|bussola|onda|ondas|neblina)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _is_refinement_request(self, normalized: str) -> bool:
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

    def _latest_user_line(self, user_prompt: str) -> str:
        user_lines = [
            line.split(":", 1)[1].strip()
            for line in user_prompt.splitlines()
            if line.lower().startswith("user:") and ":" in line
        ]
        if user_lines:
            return user_lines[-1]
        return user_prompt.strip()
