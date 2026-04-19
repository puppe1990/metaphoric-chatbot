"use client";

import React from "react";
import { useEffect, useRef, useState } from "react";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";
import { ProgressChip } from "./progress-chip";
import { downloadChatMarkdown } from "../lib/chat-markdown";
import type { GuidedSessionView } from "../lib/api";

type ChatShellProps = {
  activeModel?: string;
  activeProviderLabel?: string;
  isThinking?: boolean;
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
  activeModel,
  activeProviderLabel,
  isThinking = false,
  inputDisabled = false,
  inputValue,
  onInputChange,
  onInputValueChange,
  onInputSubmit,
  onRestart,
  restartDisabled = false,
  session,
}: ChatShellProps) {
  const topActionButtonClassName =
    "min-h-11 rounded-xl border border-ink/10 bg-white/90 px-4 py-2.5 text-sm font-semibold text-ink shadow-[0_1px_0_rgba(23,25,18,0.02)] transition-colors hover:border-ink/20 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60";
  const [draft, setDraft] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const pendingSubmissionRef = useRef<string | null>(null);
  const value = inputValue ?? draft;
  const latestAssistantMessage = [...session.messages].reverse().find((message) => message.role === "assistant")?.content ?? "";
  const showsRefinementActions =
    session.progressLabel === "refine_selected" &&
    latestAssistantMessage.toLowerCase().includes("como você quer ajustar essa opção");
  const inlineSuggestions = showsRefinementActions ? session.suggestions : [];
  const inputSuggestions = session.progressLabel === "refine_selected" ? [] : session.suggestions;

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
    pendingSubmissionRef.current = null;
    onInputSubmit?.(event);

    if (inputValue === undefined) {
      setDraft("");
    }
  };

  const handleChoiceSelect = (label: "A" | "B" | "C" | "D" | "E") => {
    if (inputDisabled) {
      return;
    }

    pendingSubmissionRef.current = label;
    updateValue(label);
  };

  const handleInlineSuggestionSelect = (suggestion: string) => {
    if (inputDisabled) {
      return;
    }

    pendingSubmissionRef.current = suggestion;
    updateValue(suggestion);
  };

  useEffect(() => {
    const pendingSubmission = pendingSubmissionRef.current;
    if (pendingSubmission == null) {
      return;
    }

    if (inputDisabled || value !== pendingSubmission) {
      pendingSubmissionRef.current = null;
      return;
    }

    pendingSubmissionRef.current = null;
    formRef.current?.requestSubmit();
  }, [inputDisabled, value]);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return;
    }

    transcript.scrollTop = transcript.scrollHeight;
  }, [isThinking, session.artifacts.length, session.messages.length]);

  return (
    <section className="flex min-h-0 flex-1 px-3 pt-3 text-ink sm:px-5 sm:pt-4">
      <div className="mx-auto flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-ink/10 bg-white/82 shadow-[0_24px_80px_rgba(23,25,18,0.12)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-white/78 px-4 py-4 sm:px-6">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
            <ProgressChip label={session.progressLabel} />
            {activeProviderLabel && activeModel ? (
              <div className="min-w-0 rounded-lg border border-ink/10 bg-fog/80 px-3 py-1.5">
                <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-clay">Modelo ativo</p>
                <p className="truncate text-sm font-semibold text-ink">
                  {activeProviderLabel}
                  <span className="px-1.5 text-clay">/</span>
                  <span className="font-medium text-clay">{activeModel}</span>
                </p>
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className={topActionButtonClassName}
              disabled={inputDisabled}
              onClick={() => downloadChatMarkdown(session)}
              type="button"
            >
              Baixar .md
            </button>
            {onRestart ? (
              <button
                className={topActionButtonClassName}
                disabled={restartDisabled}
                onClick={onRestart}
                type="button"
              >
                Recomeçar
              </button>
            ) : null}
          </div>
        </div>

        <section className="relative flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6" ref={transcriptRef}>
            <div className="mx-auto max-w-3xl pb-[19rem] sm:pb-[17rem]">
              <MessageList
                artifacts={session.artifacts}
                disabled={inputDisabled}
                inlineSuggestions={inlineSuggestions}
                isThinking={isThinking}
                messages={session.messages}
                onChoiceSelect={handleChoiceSelect}
                onInlineSuggestionSelect={handleInlineSuggestionSelect}
              />
            </div>
          </div>
          <div className="z-10 border-t border-ink/10 bg-gradient-to-t from-[#f4f6f1] via-[#f4f6f1]/95 to-transparent px-4 pb-4 pt-6 sm:px-6">
            <div className="mx-auto w-full max-w-3xl">
              <ChatInput
                disabled={inputDisabled}
                formRef={formRef}
                helperText={
                  session.mode === "receive"
                    ? "Descreva o problema em uma frase. Se eu tiver contexto suficiente, já te mostro mundos simbólicos para desenvolver sua metáfora."
                    : "Envie sua resposta para avançar o estado guiado desta conversa."
                }
                onChange={handleChange}
                onValueChange={updateValue}
                onSubmit={handleSubmit}
                placeholder={
                  session.mode === "build"
                    ? "Ex.: isso parece mais raiz, batalha, caminho, engrenagem ou pressão..."
                    : "Ex.: o projeto trava quando precisa decidir..."
                }
                suggestions={inputSuggestions}
                value={value}
              />
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
