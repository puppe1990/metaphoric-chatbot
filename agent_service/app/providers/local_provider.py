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
        latest_lower = latest.lower()

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
            "Escolha A, B ou C."
        )

    def _extract_symbol(self, text: str) -> str | None:
        match = re.search(r"\b(um|uma)\s+([^.\n]+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{match.group(1).lower()} {match.group(2).strip()}"
