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

    expect(screen.getByRole("link", { name: "Voltar ao início" })).toHaveAttribute("href", "/");
    expect(screen.getByText("Receber uma metáfora")).toBeInTheDocument();
    expect(screen.getByText("Intake Problem")).toBeInTheDocument();
    expect(screen.getByText("tok_123", { selector: "header span" })).toBeInTheDocument();
    expect(screen.getByText("Descreva o problema em uma frase simples.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Receber metáfora" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "O que está travando?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onde a tensão aparece?" })).toBeInTheDocument();
    expect(
      screen.getByText("Descreva o problema em uma frase. Se eu tiver contexto suficiente, já te mostro 3 caminhos."),
    ).toBeInTheDocument();

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, { target: { value: "Quero algo mais concreto." } });
    expect(input).toHaveValue("Quero algo mais concreto.");

    fireEvent.click(screen.getByRole("button", { name: "O que está travando?" }));
    expect(input).toHaveValue("O que está travando?");

    fireEvent.submit(screen.getByRole("button", { name: "Enviar" }).closest("form") as HTMLFormElement);
    expect(input).toHaveValue("");
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
            internal_candidate_count: 3,
            selected_option: "B",
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
    expect(screen.queryByRole("button", { name: "A Uma ponte oscilando no vento." })).toBeNull();
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
});
