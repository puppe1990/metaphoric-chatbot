import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatShell } from "../components/chat-shell";
import { RECEIVE_CHOICE_ARTIFACT_TYPE, type GuidedSessionView } from "../lib/api";

describe("ChatShell", () => {
  it("renders the guided view model and supports draft input", () => {
    const session: GuidedSessionView = {
      token: "tok_123",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: ["O que está travando?", "Onde a tensão aparece?"],
    };

    render(
      <ChatShell session={session} />,
    );

    expect(screen.getByText("Intake Problem")).toBeInTheDocument();
    expect(screen.getByText("Descreva o problema em uma frase simples.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Receber metáfora" })).not.toBeInTheDocument();
    expect(screen.queryByText("tok_123")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Voltar ao início" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Baixar .md" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "O que está travando?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onde a tensão aparece?" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Descreva o problema em uma frase. Se eu tiver contexto suficiente, já te mostro mundos simbólicos para desenvolver sua metáfora.",
      ),
    ).toBeInTheDocument();

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, { target: { value: "Quero algo mais concreto." } });
    expect(input).toHaveValue("Quero algo mais concreto.");

    fireEvent.click(screen.getByRole("button", { name: "O que está travando?" }));
    expect(input).toHaveValue("O que está travando?");

    fireEvent.submit(screen.getByRole("button", { name: "Enviar" }).closest("form") as HTMLFormElement);
    expect(input).toHaveValue("");
  });

  it("renders the active provider and model when available", () => {
    const session: GuidedSessionView = {
      token: "tok_provider",
      mode: "build",
      title: "Construir minha metáfora",
      description: "Transforme abstração em imagem com crítica técnica e reescrita guiada.",
      progressLabel: "offer_symbolic_fields",
      messages: [{ role: "assistant", content: "Escolha um campo simbólico para começar." }],
      artifacts: [],
      artifactTitle: "Mapa simbólico",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell activeModel="llama-3.3-70b-versatile" activeProviderLabel="Groq" session={session} />);

    expect(screen.getByText("Groq")).toBeInTheDocument();
    expect(screen.getByText("llama-3.3-70b-versatile")).toBeInTheDocument();
    expect(screen.getByText("Modelo ativo")).toBeInTheDocument();
  });

  it("renders a loading bubble under the latest message while the assistant is thinking", () => {
    const session: GuidedSessionView = {
      token: "tok_loading",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "assistant", content: "Descreva o problema em uma frase simples." },
        { role: "user", content: "Meu projeto trava quando precisa decidir." },
      ],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell inputDisabled isThinking session={session} />);

    const transcriptItems = screen.getAllByRole("listitem");
    const loadingBubble = transcriptItems[2];

    expect(transcriptItems).toHaveLength(3);
    expect(within(loadingBubble).getByText("Assistente")).toBeInTheDocument();
    expect(within(loadingBubble).getByText("Pensando...")).toBeInTheDocument();
  });

  it("scrolls the transcript to the bottom when submit enters the thinking state", () => {
    const session: GuidedSessionView = {
      token: "tok_scroll_loading",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "assistant", content: "Descreva o problema em uma frase simples." },
        { role: "user", content: "Meu projeto trava quando precisa decidir." },
      ],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    const { container, rerender } = render(<ChatShell session={session} />);
    const transcript = container.querySelector(".overflow-y-auto") as HTMLDivElement;

    Object.defineProperty(transcript, "scrollHeight", {
      configurable: true,
      value: 480,
    });
    transcript.scrollTop = 0;

    rerender(<ChatShell isThinking session={session} />);

    expect(transcript.scrollTop).toBe(480);
  });

  it("uses the same visual treatment for the top action buttons", () => {
    const session: GuidedSessionView = {
      token: "tok_actions",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell onRestart={() => {}} session={session} />);

    const downloadButton = screen.getByRole("button", { name: "Baixar .md" });
    const restartButton = screen.getByRole("button", { name: "Recomeçar" });

    expect(downloadButton.className).toContain("rounded-xl");
    expect(restartButton.className).toContain("rounded-xl");
    expect(downloadButton.className).toContain("bg-white/90");
    expect(restartButton.className).toContain("bg-white/90");
    expect(downloadButton.className).toContain("hover:border-ink/20");
    expect(restartButton.className).toContain("hover:border-ink/20");
  });

  it("keeps the chat input pinned to the bottom edge while the transcript scrolls", () => {
    const session: GuidedSessionView = {
      token: "tok_layout",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: ["Estou travado para tomar uma decisão."],
    };

    const { container } = render(<ChatShell session={session} />);

    const layoutSection = container.querySelectorAll("section")[1];
    const transcript = layoutSection?.querySelector("div");
    const inputRegion = screen.getByRole("button", { name: "Enviar" }).closest("form")?.parentElement?.parentElement;

    expect(layoutSection).toHaveClass("flex");
    expect(layoutSection).toHaveClass("flex-1");
    expect(layoutSection).toHaveClass("flex-col");
    expect(transcript?.className).toContain("flex-1");
    expect(inputRegion).toHaveClass("z-10");
    expect(inputRegion).toHaveClass("pb-4");
  });

  it("stretches the shell card to fill the available page height", () => {
    const session: GuidedSessionView = {
      token: "tok_fill",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    const { container } = render(<ChatShell session={session} />);

    const outerSection = container.querySelector("section");
    const card = outerSection?.querySelector("div");

    expect(outerSection).toHaveClass("flex");
    expect(outerSection).toHaveClass("flex-1");
    expect(card).toHaveClass("flex-1");
  });

  it("renders receive-choice artifacts under the latest assistant message in the transcript", () => {
    const session: GuidedSessionView = {
      token: "tok_choices",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "assistant", content: "Descreva o problema em uma frase simples." },
        { role: "user", content: "Meu projeto trava quando preciso decidir." },
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
      ],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Mensagem antiga que nao deve ser usada para pareamento.",
          metadata: {
            clarifier_asked: false,
            internal_candidate_count: 5,
            selected_option: null,
          },
          choices: [
            { label: "A", text: "Uma ponte oscilando no vento." },
            { label: "B", text: "Um motor girando sem engatar." },
            { label: "C", text: "Uma porta pesada que quase cede." },
            { label: "D", text: "Um mapa cheio de desvios." },
            { label: "E", text: "Uma caldeira perto do limite." },
          ],
        },
      ],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell session={session} />);

    const transcriptItems = screen.getAllByRole("listitem");
    const latestAssistantMessage = transcriptItems[2];

    expect(within(transcriptItems[0]).queryByRole("button", { name: "A Uma ponte oscilando no vento." })).toBeNull();
    expect(within(transcriptItems[1]).queryByRole("button", { name: "A Uma ponte oscilando no vento." })).toBeNull();

    expect(
      within(latestAssistantMessage).getByRole("button", { name: "A Uma ponte oscilando no vento." }),
    ).toBeInTheDocument();
    expect(
      within(latestAssistantMessage).getByRole("button", { name: "B Um motor girando sem engatar." }),
    ).toBeInTheDocument();
    expect(
      within(latestAssistantMessage).getByRole("button", { name: "C Uma porta pesada que quase cede." }),
    ).toBeInTheDocument();
    expect(within(latestAssistantMessage).getByRole("button", { name: "D Um mapa cheio de desvios." })).toBeInTheDocument();
    expect(
      within(latestAssistantMessage).getByRole("button", { name: "E Uma caldeira perto do limite." }),
    ).toBeInTheDocument();
  });

  it("hides stale receive-choice artifacts after a selection was made during refinement", () => {
    const session: GuidedSessionView = {
      token: "tok_refine",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "refine_selected",
      messages: [
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
        { role: "user", content: "B" },
        { role: "assistant", content: "Quer deixá-la mais curta, mais concreta ou mais poética?" },
      ],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Escolha a imagem que melhor descreve seu momento.",
          metadata: {
            clarifier_asked: false,
            internal_candidate_count: 5,
            selected_option: "B",
          },
          choices: [
            { label: "A", text: "Uma ponte oscilando no vento." },
            { label: "B", text: "Um motor girando sem engatar." },
            { label: "C", text: "Uma porta pesada que quase cede." },
            { label: "D", text: "Um mapa cheio de desvios." },
            { label: "E", text: "Uma caldeira perto do limite." },
          ],
        },
      ],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell session={session} />);

    const transcriptItems = screen.getAllByRole("listitem");
    const refinementPrompt = transcriptItems[2];

    expect(
      within(refinementPrompt).queryByRole("button", { name: "A Uma ponte oscilando no vento." }),
    ).toBeNull();
    expect(
      within(refinementPrompt).queryByRole("button", { name: "B Um motor girando sem engatar." }),
    ).toBeNull();
    expect(
      within(refinementPrompt).queryByRole("button", { name: "C Uma porta pesada que quase cede." }),
    ).toBeNull();
    expect(within(refinementPrompt).queryByRole("button", { name: "D Um mapa cheio de desvios." })).toBeNull();
    expect(within(refinementPrompt).queryByRole("button", { name: "E Uma caldeira perto do limite." })).toBeNull();
    expect(screen.queryByRole("button", { name: "A Uma ponte oscilando no vento." })).toBeNull();
    expect(screen.getByText("B — Um motor girando sem engatar.")).toBeInTheDocument();
  });

  it("renders refinement suggestions as clickable actions inside the latest assistant message", () => {
    const session: GuidedSessionView = {
      token: "tok_refine_actions",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "refine_selected",
      messages: [
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
        { role: "user", content: "B" },
        {
          role: "assistant",
          content: "Boa. Agora diga como você quer ajustar essa opção: mais curta, mais concreta, mais poética ou mais direta.",
        },
      ],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: ["Mais curta.", "Mais concreta.", "Mais poética.", "Mais direta."],
    };

    render(<ChatShell session={session} />);

    const transcriptItems = screen.getAllByRole("listitem");
    const refinementPrompt = transcriptItems[2];

    expect(within(refinementPrompt).getByRole("button", { name: "Mais curta." })).toBeInTheDocument();
    expect(within(refinementPrompt).getByRole("button", { name: "Mais concreta." })).toBeInTheDocument();
    expect(within(refinementPrompt).getByRole("button", { name: "Mais poética." })).toBeInTheDocument();
    expect(within(refinementPrompt).getByRole("button", { name: "Mais direta." })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mais curta." })).toBeInTheDocument();
    expect(screen.queryByText("Sua próxima linha")).toBeInTheDocument();
  });

  it("submits a refinement suggestion through the existing chat form flow", async () => {
    const submissions: string[] = [];
    const handleSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) => {
      const input = event.currentTarget.querySelector("textarea");
      submissions.push(input?.value ?? "");
    });

    const session: GuidedSessionView = {
      token: "tok_refine_submit",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "refine_selected",
      messages: [
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
        { role: "user", content: "B" },
        {
          role: "assistant",
          content: "Boa. Agora diga como você quer ajustar essa opção: mais curta, mais concreta, mais poética ou mais direta.",
        },
      ],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: ["Mais curta.", "Mais concreta.", "Mais poética.", "Mais direta."],
    };

    render(<ChatShell onInputSubmit={handleSubmit} session={session} />);

    fireEvent.click(screen.getByRole("button", { name: "Mais concreta." }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledTimes(1));
    expect(submissions).toEqual(["Mais concreta."]);
    expect(screen.getByLabelText("Message input")).toHaveValue("");
  });

  it("hides refinement suggestions when the latest assistant message has already moved to a new question", () => {
    const session: GuidedSessionView = {
      token: "tok_refine_followup",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "refine_selected",
      messages: [
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
        { role: "user", content: "B" },
        { role: "user", content: "Mais poética." },
        {
          role: "assistant",
          content:
            "Então, no mundo A que você escolheu, que elemento concreto (um objeto, uma paisagem ou um som) poderia simbolizar a decisão que ainda está em suspenso?",
        },
      ],
      artifacts: [],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: ["Mais curta.", "Mais concreta.", "Mais poética.", "Mais direta."],
    };

    render(<ChatShell session={session} />);

    expect(screen.queryByRole("button", { name: "Mais curta." })).toBeNull();
    expect(screen.queryByRole("button", { name: "Mais concreta." })).toBeNull();
    expect(screen.queryByRole("button", { name: "Mais poética." })).toBeNull();
    expect(screen.queryByRole("button", { name: "Mais direta." })).toBeNull();
  });

  it("submits a receive-choice selection through the existing chat form flow", async () => {
    const submissions: string[] = [];
    const handleSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) => {
      const input = event.currentTarget.querySelector("textarea");
      submissions.push(input?.value ?? "");
    });

    const session: GuidedSessionView = {
      token: "tok_choice_submit",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
      ],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Escolha a imagem que melhor descreve seu momento.",
          metadata: {
            clarifier_asked: false,
            internal_candidate_count: 5,
            selected_option: null,
          },
          choices: [
            { label: "A", text: "Uma ponte oscilando no vento." },
            { label: "B", text: "Um motor girando sem engatar." },
            { label: "C", text: "Uma porta pesada que quase cede." },
            { label: "D", text: "Um mapa cheio de desvios." },
            { label: "E", text: "Uma caldeira perto do limite." },
          ],
        },
      ],
      artifactTitle: "Receita da metáfora",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(<ChatShell onInputSubmit={handleSubmit} session={session} />);

    fireEvent.click(screen.getByRole("button", { name: "B Um motor girando sem engatar." }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledTimes(1));
    expect(submissions).toEqual(["B"]);
    expect(screen.getByLabelText("Message input")).toHaveValue("");
  });

  it("submits a receive-choice selection through the controlled input path", async () => {
    const submissions: string[] = [];
    const inputValueChanges: string[] = [];
    const inputChangeEvents: string[] = [];
    const session: GuidedSessionView = {
      token: "tok_controlled_choice",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [{ role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." }],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Escolha a imagem que melhor descreve seu momento.",
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

    function ControlledChatShell() {
      const [value, setValue] = React.useState("");

      return (
        <ChatShell
          inputValue={value}
          onInputChange={(event) => {
            inputChangeEvents.push(event.target.value);
            setValue(event.target.value);
          }}
          onInputValueChange={(nextValue) => {
            inputValueChanges.push(nextValue);
            setValue(nextValue);
          }}
          onInputSubmit={(event) => {
            const input = event.currentTarget.querySelector("textarea");
            submissions.push(input?.value ?? "");
            setValue("");
          }}
          session={session}
        />
      );
    }

    render(<ControlledChatShell />);

    fireEvent.click(screen.getByRole("button", { name: "B Um motor girando sem engatar." }));

    expect(inputValueChanges).toEqual(["B"]);
    expect(inputChangeEvents).toEqual([]);
    await waitFor(() => expect(submissions).toEqual(["B"]));
    expect(screen.getByLabelText("Message input")).toHaveValue("");
  });

  it("disables receive-choice buttons when the shell input is disabled", () => {
    const submissions: string[] = [];
    const inputValueChanges: string[] = [];
    const session: GuidedSessionView = {
      token: "tok_disabled_choice",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [{ role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." }],
      artifacts: [
        {
          artifact_type: RECEIVE_CHOICE_ARTIFACT_TYPE,
          content: "Escolha a imagem que melhor descreve seu momento.",
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

    function DisabledChatShell() {
      const [value, setValue] = React.useState("");

      return (
        <ChatShell
          inputDisabled
          inputValue={value}
          onInputSubmit={() => {
            submissions.push(value);
          }}
          onInputValueChange={(nextValue) => {
            inputValueChanges.push(nextValue);
            setValue(nextValue);
          }}
          session={session}
        />
      );
    }

    render(<DisabledChatShell />);

    const choiceButton = screen.getByRole("button", { name: "B Um motor girando sem engatar." });
    expect(choiceButton).toBeDisabled();

    fireEvent.click(choiceButton);

    expect(inputValueChanges).toEqual([]);
    expect(submissions).toEqual([]);
    expect(screen.getByLabelText("Message input")).toHaveValue("");
  });

  it("submits the current message when Enter is pressed", async () => {
    const submissions: string[] = [];
    const session: GuidedSessionView = {
      token: "tok_enter_submit",
      mode: "build",
      title: "Construir minha metáfora",
      description: "Transforme abstração em imagem com crítica técnica e reescrita guiada.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Mapa simbólico",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(
      <ChatShell
        onInputSubmit={(event) => {
          const input = event.currentTarget.querySelector("textarea");
          submissions.push(input?.value ?? "");
        }}
        session={session}
      />,
    );

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, { target: { value: "Uma porta emperrada." } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter", charCode: 13 });

    await waitFor(() => expect(submissions).toEqual(["Uma porta emperrada."]));
    expect(screen.getByLabelText("Message input")).toHaveValue("");
  });

  it("keeps a newline when Shift+Enter is pressed", () => {
    const submissions: string[] = [];
    const session: GuidedSessionView = {
      token: "tok_shift_enter",
      mode: "build",
      title: "Construir minha metáfora",
      description: "Transforme abstração em imagem com crítica técnica e reescrita guiada.",
      progressLabel: "intake_problem",
      messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
      artifacts: [],
      artifactTitle: "Mapa simbólico",
      artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
      suggestions: [],
    };

    render(
      <ChatShell
        onInputSubmit={() => {
          submissions.push("submitted");
        }}
        session={session}
      />,
    );

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, { target: { value: "Primeira linha" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter", charCode: 13, shiftKey: true });
    fireEvent.change(input, { target: { value: "Primeira linha\nSegunda linha" } });

    expect(submissions).toEqual([]);
    expect(screen.getByLabelText("Message input")).toHaveValue("Primeira linha\nSegunda linha");
  });

  it("downloads the current conversation as markdown", () => {
    const session: GuidedSessionView = {
      token: "tok_download",
      mode: "receive",
      title: "Receber uma metáfora",
      description: "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
      progressLabel: "present_choices",
      messages: [
        { role: "system", content: "Mantenha a resposta curta." },
        { role: "assistant", content: "Escolha a imagem que melhor descreve seu momento." },
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
    const createObjectUrl = vi.fn(() => "blob:markdown");
    const revokeObjectUrl = vi.fn();
    const click = vi.fn();
    const originalCreateElement = document.createElement.bind(document);

    vi.stubGlobal(
      "URL",
      Object.assign(URL, {
        createObjectURL: createObjectUrl,
        revokeObjectURL: revokeObjectUrl,
      }),
    );

    const createElement = vi.spyOn(document, "createElement").mockImplementation(((tagName: string) => {
      if (tagName === "a") {
        const anchor = originalCreateElement("a");
        anchor.click = click;
        return anchor;
      }

      return originalCreateElement(tagName);
    }) as typeof document.createElement);
    const appendChild = vi.spyOn(document.body, "appendChild");
    const removeChild = vi.spyOn(document.body, "removeChild");

    render(<ChatShell session={session} />);
    appendChild.mockClear();
    removeChild.mockClear();

    fireEvent.click(screen.getByRole("button", { name: "Baixar .md" }));

    expect(createObjectUrl).toHaveBeenCalledTimes(1);
    expect(createObjectUrl.mock.calls[0]?.[0]).toBeInstanceOf(Blob);
    expect(appendChild).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(removeChild).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:markdown");

    const link = appendChild.mock.calls[0]?.[0] as HTMLAnchorElement;
    expect(link.download).toBe("conversa-tok_download.md");
    expect(link.href).toBe("blob:markdown");

    createElement.mockRestore();
    appendChild.mockRestore();
    removeChild.mockRestore();
  });
});
