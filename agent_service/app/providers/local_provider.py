from __future__ import annotations

import json
import re

from app.prompts import (
    COACH_PROMPT,
    EXTRACTOR_PROMPT,
    GENERATOR_PROMPT,
    RECEIVE_CHOICES_PROMPT,
    RECEIVE_CONTEXTUAL_PROMPT,
    RECEIVE_FINAL_BANDLER_PROMPT,
    RECEIVE_FINAL_ERICKSON_PROMPT,
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

        if system_prompt == RECEIVE_FINAL_ERICKSON_PROMPT:
            return self._receive_final_response(user_prompt, style="erickson")

        if system_prompt == RECEIVE_FINAL_BANDLER_PROMPT:
            return self._receive_final_response(user_prompt, style="bandler")

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
            if selected_world == "jornada" and self._journey_tool_seeking_loop(user_lines):
                return (
                    "Então a cena pode estar mentindo sobre a ferramenta. "
                    "O que te tira da trilha principal nessa jornada: "
                    "um novo mapa, outra trilha ou o impulso de desviar de novo?"
                )
            if selected_world == "guerra" and self._war_blockage_needs_tactic(latest_lower):
                return (
                    "Então a muralha já mostrou o problema com nitidez. "
                    "O que entra nessa cena como tática real: mira, ritmo, alcance ou janela de ataque?"
                )
            if "engren" in latest_lower and "emperr" in latest_lower:
                return (
                    "Então, a engrenagem está emperrada. "
                    "O que essa engrenagem precisa destravar para a máquina voltar a andar?"
                )
            if "máquina imensa" in latest_lower or "maquina imensa" in latest_lower:
                return (
                    "Então, essa engrenagem emperrada segura uma máquina imensa inteira. "
                    "O que entra nessa cena para forçar esse destravamento?"
                )
            if "alavanca" in latest_lower:
                return "Então a alavanca já entrou na cena. O que faz essa alavanca ter força de verdade nessa cena?"
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

    def _receive_final_response(self, user_prompt: str, style: str) -> str:
        context_active_seed = self._context_value(user_prompt, "active_metaphor_seed")
        context_literal_block = self._context_value(user_prompt, "receive_literal_block_story")
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
        imagetic_lines = [line for line in substantive_lines if self._looks_like_user_metaphor(line)]

        seed = context_active_seed or (
            imagetic_lines[-1] if imagetic_lines else substantive_lines[-1] if substantive_lines else "essa imagem"
        )

        anchor_candidates = [line for line in imagetic_lines if line != seed]
        if anchor_candidates:
            anchor = anchor_candidates[-1]
        elif context_literal_block and context_active_seed:
            anchor = context_active_seed
        elif len(substantive_lines) > 1:
            anchor = substantive_lines[-2]
        else:
            anchor = "o conflito antigo"
        selected_world = self._selected_symbolic_world(user_lines)

        if selected_world == "guerra" or self._contains_war_imagery(seed, anchor):
            return self._receive_war_final_response(anchor=anchor, seed=seed, style=style)

        if style == "erickson":
            return (
                f"Quando {anchor} toma a cena inteira, parece que tudo ao redor aprende a se contrair junto, "
                "como se o espaço também passasse a obedecer ao mesmo aperto.\n\n"
                f"Então {seed} deixa de ser só presença e começa a mudar o compasso da imagem, "
                "empurrando a tensão para outro ponto, onde ela já não consegue mandar do mesmo jeito.\n\n"
                "E, no instante em que essa pressão perde o centro, aparece uma folga pequena, mas real. "
                "Às vezes é isso que basta para o movimento voltar antes mesmo de a cena inteira entender por quê."
            )

        return (
            f"{anchor.capitalize()} aperta a cena até sobrar pouco ar entre uma coisa e outra. "
            "O peso fica concentrado, o corpo sente onde a pressão encosta, "
            "e o resto do quadro gira em torno desse mesmo ponto.\n\n"
            f"Então {seed} entra com impacto nítido, mexendo no ritmo, "
            "deslocando força, abrindo contraste onde antes só havia "
            "compressão contínua.\n\n"
            "Quando a pressão sai do lugar antigo, a imagem responde inteira. "
            "O aperto perde domínio, surge espaço para passagem, e o que estava encurralado volta a encontrar direção."
        )

    def _receive_war_final_response(self, *, anchor: str, seed: str, style: str) -> str:
        if style == "erickson":
            return (
                f"Diante de {anchor}, a distância parece sempre maior no instante em que alguém pensa em avançar. "
                "A pedra segura o campo, o corpo mede o peso do obstáculo, "
                "e por um tempo tudo parece pedir recuo.\n\n"
                f"Então {seed} deixa de ser pressa e vira cálculo: ajustar a base, "
                "sentir o alcance, esperar o ponto certo "
                "em que a tensão para de se espalhar e começa a obedecer.\n\n"
                "E, quando o primeiro impacto encontra a mesma fissura duas vezes, "
                "a muralha já não parece inteira do mesmo jeito. "
                "Às vezes a passagem não nasce de derrubar tudo, mas de descobrir onde a pedra começou a ceder."
            )

        return (
            f"{anchor.capitalize()} ocupa o campo inteiro, grossa, alta, "
            "fechando a passagem como se cada bloco empurrasse o outro para o mesmo lugar. "
            "O ar pesa antes de qualquer movimento, e chegar perto só faz o tamanho dela aparecer mais.\n\n"
            f"Então {seed} entra na cena com precisão bruta: madeira tensionada, "
            "base firme, braço puxado no limite, cálculo de alcance e mira presa "
            "no mesmo ponto da pedra. "
            "Nada explode de uma vez; o trabalho é bater onde a rocha devolve menos resistência.\n\n"
            "Depois de alguns disparos no mesmo lugar, surge um som oco, curto, diferente do resto. "
            "A brecha ainda é estreita, mas agora existe, e o campo muda inteiro "
            "quando a muralha deixa de parecer absoluta."
        )

    def _extract_symbol(self, text: str) -> str | None:
        match = re.search(r"\b(um|uma)\s+([^.\n]+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{match.group(1).lower()} {match.group(2).strip()}"

    def _context_value(self, text: str, field_name: str) -> str | None:
        match = re.search(rf"^{re.escape(field_name)}:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        value = match.group(1).strip()
        return value or None

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
            "mochila",
            "pedra",
            "peito",
            "nó",
            "no",
            "monstro",
            "muralha",
            "fortaleza",
            "catapulta",
            "trincheira",
            "raiz",
            "semente",
            "ponte",
            "mapa",
            "engrenagem",
            "alavanca",
            "válvula",
            "valvula",
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

        compact = normalized.strip().strip(".!?")
        if compact and len(compact.split()) <= 3:
            return any(
                re.search(rf"\b{re.escape(marker)}\b", compact, flags=re.IGNORECASE)
                for marker in concrete_image_markers
            )

        return any(
            re.search(rf"\b{re.escape(marker)}\b", normalized, flags=re.IGNORECASE) for marker in concrete_image_markers
        )

    def _war_blockage_needs_tactic(self, normalized: str) -> bool:
        return bool(
            re.search(
                (
                    r"\b(n[aã]o consigo passar|intranspon[ií]vel|bloqueia|bloqueando|"
                    r"muralha|barreira|forte e densa|forte|densa)\b"
                ),
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _journey_tool_seeking_loop(self, user_lines: list[str]) -> bool:
        transcript = " ".join(user_lines).lower()
        has_tool_chasing = bool(
            re.search(
                r"\b(nova ferramenta|novas ferramentas|ferramenta certa|ferramenta ideal|ferramenta)\b",
                transcript,
                flags=re.IGNORECASE,
            )
        )
        has_journey_drift = bool(
            re.search(
                r"\b(jornada|jornadas|trilha|trilhas|mapa|mapas|desvio|seguir|caminho|rota)\b",
                transcript,
                flags=re.IGNORECASE,
            )
        )
        has_main_task_loss = bool(
            re.search(
                r"\b(nunca faço|nunca faco|ganhar dinheiro|realmente importa|importa)\b",
                transcript,
                flags=re.IGNORECASE,
            )
        )
        return has_tool_chasing and has_journey_drift and has_main_task_loss

    def _contains_war_imagery(self, *values: str) -> bool:
        return any(
            re.search(
                r"\b(muralha|catapulta|brecha|fortaleza|cerco|trincheira|ataque|campo)\b",
                value,
                flags=re.IGNORECASE,
            )
            for value in values
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
