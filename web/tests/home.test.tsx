import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders the Portuguese mode labels as links", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: /receber uma metáfora/i })).toHaveAttribute(
      "href",
      "/c/new?mode=receive",
    );
    expect(screen.getByRole("link", { name: /construir minha metáfora/i })).toHaveAttribute(
      "href",
      "/c/new?mode=build",
    );
  });
});
