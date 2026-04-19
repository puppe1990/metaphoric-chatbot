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
    SYMBOLIC_WORLD_BY_LABEL = {
        "A": "natureza",
        "B": "guerra",
        "C": "jornada",
        "D": "máquina",
        "E": "energia",
    }

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
        selected_world = self._selected_symbolic_world(user_lines)
        has_concrete_user_image = self._has_concrete_user_image(user_lines[:-1])
        latest_lower = latest.lower()

        if self._is_refinement_request(latest_lower):
            if selected_world and not has_concrete_user_image:
                return (
                    f"Então, na {selected_world} que você escolheu, que elemento concreto "
                    "(um objeto, uma paisagem ou um som) poderia simbolizar a decisão que ainda está em suspenso?"
                )
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
            "Em qual desses mundos isso se encaixa?\n"
            "A. Natureza: plantio, colheita, raiz, crescimento.\n"
            "B. Guerra / estratégia: batalha, território, ataque, defesa.\n"
            "C. Jornada / viagem: caminho, mapa, destino.\n"
            "D. Máquina / engenharia: sistema, engrenagem, processo.\n"
            "E. Energia / física: calor, pressão, força.\n"
            "Escolha uma opção e eu desenvolvo a metáfora por esse caminho.\n"
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
            f"Fica como uma luta antiga no mesmo ringue: {anchor} entra primeiro na cena, "
            "ocupando o espaço e prendendo o corpo no mesmo circuito de esforço.\n\n"
            f"No meio, {seed} empurra o conflito para um ponto mais agudo, como se o ruído "
            "apertasse as cordas e obrigasse tudo a se decidir sob pressão.\n\n"
            "No fim, a cena não explode; ela se reorganiza. O ringue ainda existe, mas abre "
            "uma fresta limpa, e é nessa abertura que a força volta a ter direção."
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
        normalized = normalized.strip().rstrip(".!?")
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

    def _selected_symbolic_world(self, user_lines: list[str]) -> str | None:
        for line in reversed(user_lines):
            normalized = line.strip().upper()
            if normalized in self.SYMBOLIC_WORLD_BY_LABEL:
                return self.SYMBOLIC_WORLD_BY_LABEL[normalized]
        return None

    def _has_concrete_user_image(self, user_lines: list[str]) -> bool:
        for line in reversed(user_lines):
            normalized = line.strip()
            if not normalized:
                continue
            if normalized.upper() in self.SYMBOLIC_WORLD_BY_LABEL:
                continue
            if self._is_refinement_request(normalized.lower()):
                continue
            if self._looks_like_user_metaphor(normalized):
                return True
        return False
