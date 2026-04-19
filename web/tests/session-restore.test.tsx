import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { SessionRestoreBanner } from "../components/session-restore-banner";
import { clearRecentSessions, loadRecentSessions, rememberRecentSession } from "../lib/session";

describe("session restore", () => {
  beforeEach(() => {
    clearRecentSessions();
  });

  it("returns an empty list when localStorage exists without the Storage methods", () => {
    const originalLocalStorage = window.localStorage;

    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {},
    });

    expect(loadRecentSessions()).toEqual([]);

    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: originalLocalStorage,
    });
  });

  it("ignores session writes when localStorage exists without the Storage methods", () => {
    const originalLocalStorage = window.localStorage;

    try {
      Object.defineProperty(window, "localStorage", {
        configurable: true,
        value: {},
      });

      expect(() => {
        rememberRecentSession({ token: "tok_ok", mode: "receive", progressLabel: "intake_problem" });
      }).not.toThrow();
    } finally {
      Object.defineProperty(window, "localStorage", {
        configurable: true,
        value: originalLocalStorage,
      });
    }
  });

  it("filters corrupted payloads from localStorage", () => {
    window.localStorage.setItem(
      "metaphoric-chatbot:recent-sessions",
      JSON.stringify([
        { token: "tok_ok", mode: "receive", progressLabel: "intake_problem", updatedAt: "2026-04-18T00:00:00.000Z" },
        { token: 1, mode: "receive" },
        "bad-entry",
        { token: "tok_bad_mode", mode: "broken", progressLabel: "x", updatedAt: "2026-04-18T00:00:00.000Z" },
      ]),
    );

    expect(loadRecentSessions()).toEqual([
      { token: "tok_ok", mode: "receive", progressLabel: "intake_problem", updatedAt: "2026-04-18T00:00:00.000Z" },
    ]);
  });

  it("renders restore links for prior sessions", async () => {
    window.localStorage.setItem(
      "metaphoric-chatbot:recent-sessions",
      JSON.stringify([
        { token: "tok_old", mode: "build", progressLabel: "sharpen_image", updatedAt: "2026-04-17T10:00:00.000Z" },
      ]),
    );

    render(
      <SessionRestoreBanner
        currentSession={{ token: "tok_current", mode: "receive", progressLabel: "intake_problem" }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Restaurar sessão")).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /Construir · sharpen_image/i })).toHaveAttribute(
      "href",
      "/c/tok_old?mode=build",
    );
    expect(screen.getByText(/1 disponíveis/i)).toBeInTheDocument();
  });
});
