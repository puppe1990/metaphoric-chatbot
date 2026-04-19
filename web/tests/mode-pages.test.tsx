import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BuildModePage from "../app/construir/page";
import ReceiveModePage from "../app/receber/page";

describe("Mode pages", () => {
  it("renders the receive page with user-facing guidance only", () => {
    render(<ReceiveModePage />);

    expect(screen.getByRole("heading", { name: "Receber uma metáfora" })).toBeInTheDocument();
    expect(screen.getByText("Traga um conflito, um impasse ou uma sensação difícil de nomear.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Começar sessão de recebimento" })).toHaveAttribute(
      "href",
      "/c/new?mode=receive",
    );
  });

  it("renders the build page with user-facing guidance only", () => {
    render(<BuildModePage />);

    expect(screen.getByRole("heading", { name: "Construir minha metáfora" })).toBeInTheDocument();
    expect(screen.getByText("Escolha a situação que você quer traduzir e trabalhe a imagem em etapas.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Começar sessão de construção" })).toHaveAttribute(
      "href",
      "/c/new?mode=build",
    );
  });
});
