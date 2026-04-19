import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatSessionPageClient } from "../app/c/[token]/chat-session-page-client";
import { clearRecentSessions } from "../lib/session";

const router = vi.hoisted(() => ({
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

describe("ChatSessionPageClient", () => {
  beforeEach(() => {
    router.replace.mockReset();
    clearRecentSessions();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts a fresh session in the same mode when the user restarts", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "GET") {
        return new Response(
          JSON.stringify({
            token: "old_token",
            mode: "build",
            state: "user_attempt",
            messages: [
              { role: "assistant", content: "Descreva o problema em uma frase simples." },
              { role: "user", content: "um macaco bagunceiro" },
            ],
          }),
          { status: 200 },
        );
      }

      return new Response(
        JSON.stringify({
          token: "new_token",
          mode: "build",
          state: "intake_problem",
          assistant_message: "Descreva o problema em uma frase simples.",
        }),
        { status: 200 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatSessionPageClient requestedMode="build" token="old_token" />);

    const restart = await screen.findByRole("button", { name: "Recomeçar" });
    fireEvent.click(restart);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith(
        "http://localhost:8000/api/chat/start",
        expect.objectContaining({
          body: JSON.stringify({ mode: "build" }),
          method: "POST",
        }),
      );
    });
    expect(router.replace).toHaveBeenCalledWith("/c/new_token?mode=build");
    expect(await screen.findByText("Descreva o problema em uma frase simples.")).toBeInTheDocument();
  });

  it("offers a way back to the home page when the session cannot be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("offline", { status: 503 })));

    render(<ChatSessionPageClient requestedMode="receive" token="broken_token" />);

    expect(await screen.findByRole("link", { name: "Voltar ao início" })).toHaveAttribute("href", "/");
    expect(await screen.findByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("fills the controlled input when a suggestion is clicked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            token: "build_token",
            mode: "build",
            state: "intake_problem",
            messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
            artifacts: [],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<ChatSessionPageClient requestedMode="build" token="build_token" />);

    const suggestion = await screen.findByRole("button", {
      name: "Quero chegar em alguém por quem sinto atração.",
    });

    fireEvent.click(suggestion);

    expect(screen.getByLabelText("Message input")).toHaveValue("Quero chegar em alguém por quem sinto atração.");
  });

  it("does not render the restore banner inside the chat page", async () => {
    window.localStorage.setItem(
      "metaphoric-chatbot:recent-sessions",
      JSON.stringify([
        { token: "tok_old", mode: "build", progressLabel: "rewrite_together", updatedAt: "2026-04-17T10:00:00.000Z" },
      ]),
    );

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            token: "receive_token",
            mode: "receive",
            state: "intake_problem",
            messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
            artifacts: [],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<ChatSessionPageClient requestedMode="receive" token="receive_token" />);

    expect(await screen.findByText("Descreva o problema em uma frase simples.")).toBeInTheDocument();
    expect(screen.queryByText("Restaurar sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Sessões recentes salvas neste navegador.")).not.toBeInTheDocument();
  });

  it("uses the viewport remainder below the global header and clips horizontal overflow", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            token: "receive_token",
            mode: "receive",
            state: "intake_problem",
            messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
            artifacts: [],
          }),
          { status: 200 },
        ),
      ),
    );

    const { container } = render(<ChatSessionPageClient requestedMode="receive" token="receive_token" />);

    await screen.findByText("Descreva o problema em uma frase simples.");

    const main = container.querySelector("main");
    expect(main).toHaveClass("flex");
    expect(main).toHaveClass("min-h-0");
    expect(main).toHaveClass("overflow-x-hidden");
  });

  it("locks document scrolling while the chat page is mounted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            token: "receive_token",
            mode: "receive",
            state: "intake_problem",
            messages: [{ role: "assistant", content: "Descreva o problema em uma frase simples." }],
            artifacts: [],
          }),
          { status: 200 },
        ),
      ),
    );

    const { unmount } = render(<ChatSessionPageClient requestedMode="receive" token="receive_token" />);

    await screen.findByText("Descreva o problema em uma frase simples.");

    expect(document.documentElement.style.overflow).toBe("hidden");
    expect(document.body.style.overflow).toBe("hidden");

    unmount();

    expect(document.documentElement.style.overflow).toBe("");
    expect(document.body.style.overflow).toBe("");
  });
});
