import { describe, expect, it } from "vitest";
import { buildChatMarkdown } from "../lib/chat-markdown";
import {
  RECEIVE_CHOICE_ARTIFACT_TYPE,
  RECEIVE_FINAL_COMPARISON_ARTIFACT_TYPE,
  type GuidedSessionView,
} from "../lib/api";

describe("buildChatMarkdown", () => {
  it("serializes session metadata, transcript roles, and presented choices into markdown", () => {
    const session: GuidedSessionView = {
      token: "tok_markdown",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "system", content: "Mantenha a resposta curta." },
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
        { role: "user", content: "B" },
      ],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Mensagem antiga que nao deve ser usada para pareamento.",
          metadata: {
            clarifier_asked: false,
            internal_candidate_count: 3,
            selected_option: null,
          },
          choices: [
            { label: "A", text: "Uma ponte oscilando no vento." },
            { label: "B", text: "Um motor girando sem engatar." },
            { label: "C", text: "Uma porta pesada que quase cede." },
          ],
        },
      ],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    expect(buildChatMarkdown(session)).toBe(`# Receber uma metáfora

- Token: tok_markdown
- Modo: receive
- Progresso: present_choices

## System

Mantenha a resposta curta.

## Assistente

Escolha a imagem que melhor descreve seu momento.

### Opcoes apresentadas

- A: Uma ponte oscilando no vento.
- B: Um motor girando sem engatar.
- C: Uma porta pesada que quase cede.

## Voce

B
`);
  });

  it("serializes final comparison variants into markdown", () => {
    const session: GuidedSessionView = {
      token: "tok_compare",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "refine_selected",
      messages: [
        { role: "assistant", content: "Aqui estão duas leituras finais do mesmo núcleo metafórico." },
      ],
      artifacts: [
        {
          artifact_type: RECEIVE_FINAL_COMPARISON_ARTIFACT_TYPE,
          content: "[]",
          metadata: null,
          choices: [],
          comparison_variants: [
            { style: "erickson", title: "Erickson / insinuante", text: "Versão um" },
            { style: "bandler", title: "Bandler / cinematográfica", text: "Versão dois" },
          ],
        },
      ],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    expect(buildChatMarkdown(session)).toContain("### Comparação final");
    expect(buildChatMarkdown(session)).toContain("#### Erickson / insinuante");
    expect(buildChatMarkdown(session)).toContain("Versão um");
    expect(buildChatMarkdown(session)).toContain("#### Bandler / cinematográfica");
    expect(buildChatMarkdown(session)).toContain("Versão dois");
  });
});
