"use client";

import React from "react";
import { useEffect, useRef, useState } from "react";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";
import { ProgressChip } from "./progress-chip";
import { downloadChatMarkdown } from "../lib/chat-markdown";
import type { GuidedSessionView } from "../lib/api";

type ChatShellProps = {
  session: GuidedSessionView;
  inputDisabled?: boolean;
  inputValue?: string;
  onInputValueChange?: (value: string) => void;
  onInputChange?: React.ChangeEventHandler<HTMLTextAreaElement>;
  onInputSubmit?: React.FormEventHandler<HTMLFormElement>;
  onRestart?: () => void;
  restartDisabled?: boolean;
};

export function ChatShell({
  inputDisabled = false,
  inputValue,
  onInputChange,
  onInputValueChange,
  onInputSubmit,
  onRestart,
  restartDisabled = false,
  session,
}: ChatShellProps) {
  const [draft, setDraft] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const pendingChoiceSubmitRef = useRef<"A" | "B" | "C" | null>(null);
  const value = inputValue ?? draft;

  const updateValue = (nextValue: string) => {
    if (inputValue === undefined) {
      setDraft(nextValue);
    }

    onInputValueChange?.(nextValue);
  };

  const handleChange: React.ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onInputChange?.(event);
    if (inputValue === undefined) {
      setDraft(event.target.value);
    }
  };

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    pendingChoiceSubmitRef.current = null;
    onInputSubmit?.(event);

    if (inputValue === undefined) {
      setDraft("");
    }
  };

  const handleChoiceSelect = (label: "A" | "B" | "C") => {
    if (inputDisabled) {
      return;
    }

    pendingChoiceSubmitRef.current = label;
    updateValue(label);
  };

  useEffect(() => {
    const pendingChoice = pendingChoiceSubmitRef.current;
    if (pendingChoice == null) {
      return;
    }

    if (inputDisabled || value !== pendingChoice) {
      pendingChoiceSubmitRef.current = null;
      return;
    }

    pendingChoiceSubmitRef.current = null;
    formRef.current?.requestSubmit();
  }, [inputDisabled, value]);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return;
    }

    transcript.scrollTop = transcript.scrollHeight;
  }, [session.messages, session.artifacts]);

  return (
    <section className="h-full min-h-0 px-3 pb-3 text-ink sm:px-5">
      <div className="mx-auto grid h-full min-h-0 max-w-5xl grid-rows-[auto_1fr] overflow-hidden rounded-lg border border-ink/10 bg-white/82 shadow-[0_24px_80px_rgba(23,25,18,0.12)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-white/78 px-4 py-4 sm:px-6">
          <ProgressChip label={session.progressLabel} />
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm font-semibold text-ink transition-colors hover:bg-fog disabled:cursor-not-allowed disabled:opacity-60"
              disabled={inputDisabled}
              onClick={() => downloadChatMarkdown(session)}
              type="button"
            >
              Baixar .md
            </button>
            {onRestart ? (
              <button
                className="rounded-lg border border-ink/10 bg-fog px-3 py-2 text-sm font-semibold text-ink transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={restartDisabled}
                onClick={onRestart}
                type="button"
              >
                Recomeçar
              </button>
            ) : null}
          </div>
        </div>

        <section className="grid min-h-0 grid-rows-[1fr_auto]">
          <div className="min-h-0 overflow-y-auto px-4 py-5 sm:px-6" ref={transcriptRef}>
            <div className="mx-auto max-w-3xl">
              <MessageList
                artifacts={session.artifacts}
                disabled={inputDisabled}
                messages={session.messages}
                onChoiceSelect={handleChoiceSelect}
              />
            </div>
          </div>
          <div className="mx-auto w-full max-w-3xl">
            <ChatInput
              disabled={inputDisabled}
              formRef={formRef}
              helperText={
                session.mode === "receive"
                  ? "Descreva o problema em uma frase. Se eu tiver contexto suficiente, já te mostro 3 caminhos."
                  : "Envie sua resposta para avançar o estado guiado desta conversa."
              }
              onChange={handleChange}
              onValueChange={updateValue}
              onSubmit={handleSubmit}
              placeholder={
                session.mode === "build"
                  ? "Ex.: uma porta emperrada, um espelho riscado..."
                  : "Ex.: o projeto trava quando precisa decidir..."
              }
              suggestions={session.suggestions}
              value={value}
            />
          </div>
        </section>
      </div>
    </section>
  );
}
