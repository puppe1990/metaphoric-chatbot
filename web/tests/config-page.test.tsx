import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ConfigPage from "../app/config/page";

describe("ConfigPage", () => {
  it("uses the first current NVIDIA model when switching provider", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/config")) {
          return new Response(
            JSON.stringify({
              provider: "groq",
              model: "llama-3.3-70b-versatile",
              groq_models: ["llama-3.3-70b-versatile"],
              nvidia_models: ["openai/gpt-oss-120b", "meta/llama-3.3-70b-instruct"],
            }),
            { status: 200 },
          );
        }

        return new Response(null, { status: 404 });
      }),
    );

    render(<ConfigPage />);

    fireEvent.click(await screen.findByRole("button", { name: "NVIDIA NIM" }));

    expect(await screen.findByText("openai/gpt-oss-120b")).toBeInTheDocument();
  });
});
