import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getGuidedSessionView,
  RECEIVE_CHOICE_ARTIFACT_TYPE,
  getSession,
  sendMessage,
  startSession,
} from "../lib/api";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

describe("api helpers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts session start requests to the agent service", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        token: "tok_start",
        mode: "receive",
        state: "intake_problem",
        assistant_message: "Descreva o problema em uma frase simples.",
      }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(startSession("receive")).resolves.toEqual({
      token: "tok_start",
      mode: "receive",
      state: "intake_problem",
      assistant_message: "Descreva o problema em uma frase simples.",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/chat/start",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("hydrates a guided session view from persisted session messages", () => {
    expect(
      getGuidedSessionView({
        token: "tok_live",
        mode: "build",
        state: "user_attempt",
        messages: [
          { role: "assistant", content: "Nomeie a imagem concreta." },
          { role: "user", content: "Uma porta emperrada." },
        ],
      }),
    ).toMatchObject({
      token: "tok_live",
      mode: "build",
      progressLabel: "user_attempt",
      messages: [
        { role: "assistant", content: "Nomeie a imagem concreta." },
        { role: "user", content: "Uma porta emperrada." },
      ],
    });
  });

  it("carries artifacts through the guided session view", () => {
    expect(
      getGuidedSessionView({
        token: "tok_choices",
        mode: "receive",
        state: "present_choices",
        messages: [{ role: "assistant", content: "Escolha uma imagem." }],
        artifacts: [
          {
            artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
            content: "Escolha uma imagem.",
            metadata: {
              clarifier_asked: false,
              internal_candidate_count: 3,
              selected_option: null,
            },
            choices: [
              { label: "A", text: "Uma ponte oscilando." },
              { label: "B", text: "Um motor sem tração." },
              { label: "C", text: "Uma porta pesada." },
            ],
          },
        ],
      }),
    ).toMatchObject({
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          choices: [
            { label: "A", text: "Uma ponte oscilando." },
            { label: "B", text: "Um motor sem tração." },
            { label: "C", text: "Uma porta pesada." },
          ],
        },
      ],
    });
  });

  it("uses state-specific answer suggestions instead of generic questions", () => {
    expect(
      getGuidedSessionView({
        token: "tok_live",
        mode: "build",
        state: "identify_core_conflict",
        messages: [{ role: "assistant", content: "Se isso tivesse um conflito central, qual seria em poucas palavras?" }],
      }),
    ).toMatchObject({
      suggestions: ["Desejo versus medo.", "Pressa versus clareza.", "Controle versus espontaneidade."],
    });

    expect(
      getGuidedSessionView({
        token: "tok_live",
        mode: "receive",
        state: "intake_problem",
        messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      }),
    ).toMatchObject({
      suggestions: [
        "Estou travado para tomar uma decisão.",
        "Tenho pressa e não consigo organizar as ideias.",
        "Sei o que quero, mas fico adiando.",
      ],
    });

    expect(
      getGuidedSessionView({
        token: "tok_live",
        mode: "receive",
        state: "refine_selected",
        messages: [
          {
            role: "assistant",
            content: "Boa. Agora diga como você quer ajustar essa opção: mais curta, mais concreta, mais poética ou mais direta.",
          },
        ],
      }),
    ).toMatchObject({
      suggestions: ["Mais curta.", "Mais concreta.", "Mais poética.", "Mais direta."],
    });
  });

  it("surfaces a clear error when the agent service is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("fetch failed")));

    await expect(getSession("tok_missing")).rejects.toThrow(
      "Não consegui falar com o serviço do chat agora. Tente novamente em instantes.",
    );
  });

  it("surfaces a localized timeout error when the agent service takes too long", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValueOnce(new DOMException("The operation was aborted.", "AbortError")),
    );

    await expect(getSession("tok_timeout")).rejects.toThrow(
      "O serviço do chat demorou demais para responder. Tente novamente.",
    );
  });

  it("sends messages to the restored session token", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        token: "tok_live",
        mode: "receive",
        state: "intake_desired_shift",
        messages: [
          { role: "assistant", content: "Descreva o problema em uma frase simples." },
          { role: "user", content: "Parece um nó apertando o peito." },
          { role: "assistant", content: "Que mudança você gostaria de sentir ao final desta metáfora?" },
        ],
      }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(sendMessage("tok_live", "Parece um nó apertando o peito.")).resolves.toMatchObject({
      token: "tok_live",
      state: "intake_desired_shift",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/chat/message",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ token: "tok_live", content: "Parece um nó apertando o peito." }),
      }),
    );
  });
});
