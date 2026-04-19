import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import RootLayout from "../app/layout";

describe("RootLayout", () => {
  it("renders a global header dedicated to route navigation", () => {
    const html = renderToStaticMarkup(
      <RootLayout>
        <main>Conteudo</main>
      </RootLayout>,
    );

    expect(html).toContain('href="/"');
    expect(html).toContain('>Início<');
    expect(html).toContain('href="/receber"');
    expect(html).toContain(">Receber uma metáfora<");
    expect(html).toContain('href="/construir"');
    expect(html).toContain(">Construir minha metáfora<");
    expect(html).toContain("Conteudo");
  });
});
