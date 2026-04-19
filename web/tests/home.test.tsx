import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import HomePage from "../app/page";
import { clearRecentSessions } from "../lib/session";

describe("HomePage", () => {
  beforeEach(() => {
    clearRecentSessions();
  });

  it("renders the moved intro block with both chat mode entry points", () => {
    render(<HomePage />);

    expect(screen.getByText("Dois caminhos para trabalhar uma imagem com calma e precisão.")).toBeInTheDocument();
    expect(screen.getByText("Receba uma imagem curta para enxergar o problema por outro ângulo.")).toBeInTheDocument();
    expect(screen.getByText("Parta de uma ideia abstrata e lapide uma imagem concreta até ela ganhar força.")).toBeInTheDocument();
    expect(screen.getByText("Escolha um modo para começar quando quiser.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /receber uma metáfora/i })).toHaveAttribute(
      "href",
      "/receber",
    );
    expect(screen.getByRole("link", { name: /construir minha metáfora/i })).toHaveAttribute(
      "href",
      "/construir",
    );
  });

  it("renders old conversations saved in this browser", async () => {
    window.localStorage.setItem(
      "metaphoric-chatbot:recent-sessions",
      JSON.stringify([
        { token: "tok_old_1", mode: "build", progressLabel: "sharpen_image", updatedAt: "2026-04-17T10:00:00.000Z" },
        { token: "tok_old_2", mode: "receive", progressLabel: "refine_output", updatedAt: "2026-04-17T09:00:00.000Z" },
      ]),
    );

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Conversas antigas")).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /Construir · sharpen_image/i })).toHaveAttribute(
      "href",
      "/c/tok_old_1?mode=build",
    );
    expect(screen.getByRole("link", { name: /Receber · refine_output/i })).toHaveAttribute(
      "href",
      "/c/tok_old_2?mode=receive",
    );
  });
});
