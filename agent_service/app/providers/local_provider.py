from __future__ import annotations

import re

from app.prompts import COACH_PROMPT, EXTRACTOR_PROMPT, GENERATOR_PROMPT, RECEIVE_CHOICES_PROMPT


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

        if any(verb in latest.lower() for verb in ["falo", "digo", "solto", "faço"]):
            return (
                f"Agora ficou mais vivo: {symbol} aparece e solta uma bobagem grande. "
                f"O ponto fraco ainda é que '{latest}' está muito direto. Transforme em cena: "
                "o que ele derruba, aperta ou joga para o alto no instante da bagunça?"
            )

        if latest:
            return (
                f"Use {latest} como imagem central, mas dê comportamento a ela. "
                "O que muda no corpo da cena quando o conflito aparece?"
            )

        return "Escolha uma imagem concreta e diga o que ela faz quando o conflito aparece."

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
            f"C. Como três rádios ligados ao mesmo tempo: sinais disputam espaço e nenhuma música consegue abrir caminho em {scene}.\n"
            "Escolha A, B ou C."
        )

    def _extract_symbol(self, text: str) -> str | None:
        match = re.search(r"\b(um|uma)\s+([^.\n]+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{match.group(1).lower()} {match.group(2).strip()}"
