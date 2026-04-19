"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChatShell } from "../../../components/chat-shell";
import {
  getGuidedSessionView,
  getSession,
  sendMessage,
  startSession,
  type ChatMode,
  type GuidedSessionView,
} from "../../../lib/api";
import { NEW_SESSION_TOKEN } from "../../../lib/session";

type ChatSessionPageClientProps = {
  requestedMode: ChatMode;
  token: string;
};

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected chat failure.";
}

export function ChatSessionPageClient({ requestedMode, token }: ChatSessionPageClientProps) {
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRestarting, setIsRestarting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sessionView, setSessionView] = useState<GuidedSessionView | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function hydrateSession() {
      setIsLoading(true);
      setError(null);

      try {
        if (token === NEW_SESSION_TOKEN) {
          const started = await startSession(requestedMode);
          if (cancelled) {
            return;
          }

          setSessionView(getGuidedSessionView(started));
          router.replace(`/c/${started.token}?mode=${started.mode}`);
          return;
        }

        const restored = await getSession(token);
        if (cancelled) {
          return;
        }

        setSessionView(getGuidedSessionView(restored));
      } catch (caughtError) {
        if (!cancelled) {
          setSessionView(null);
          setError(getErrorMessage(caughtError));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void hydrateSession();

    return () => {
      cancelled = true;
    };
  }, [requestedMode, retryKey, router, token]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!sessionView || isSubmitting) {
      return;
    }

    const content = draft.trim();
    if (!content) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const updated = await sendMessage(sessionView.token, content);
      setSessionView(getGuidedSessionView(updated));
      setDraft("");
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRestart() {
    if (!sessionView || isRestarting) {
      return;
    }

    setIsRestarting(true);
    setError(null);

    try {
      const started = await startSession(sessionView.mode);
      setSessionView(getGuidedSessionView(started));
      setDraft("");
      router.replace(`/c/${started.token}?mode=${started.mode}`);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
    } finally {
      setIsRestarting(false);
    }
  }

  if (!sessionView) {
    return (
      <main className="min-h-screen px-4 py-6 text-ink sm:px-6 lg:px-8">
        <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-3xl flex-col justify-center gap-4 rounded-[2rem] border border-black/10 bg-white/80 p-8 shadow-[0_18px_70px_rgba(16,19,31,0.08)]">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">
            {token === NEW_SESSION_TOKEN ? "Iniciando sessão" : "Carregando sessão"}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">O chat depende do agent service.</h1>
          <p className="text-base leading-7 text-clay">
            {isLoading
              ? "Tentando conectar e recuperar o estado desta conversa."
              : "A conversa não pôde ser carregada agora."}
          </p>
          {error ? (
            <div role="alert" className="rounded-[1.4rem] border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
              {error}
            </div>
          ) : null}
          {!isLoading ? (
            <div className="flex flex-wrap gap-3">
              <button
                className="w-fit rounded-full bg-ink px-4 py-2 text-sm font-semibold text-fog"
                onClick={() => setRetryKey((value) => value + 1)}
                type="button"
              >
                Tentar novamente
              </button>
              <Link
                href="/"
                className="w-fit rounded-full border border-ink/10 bg-white px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-fog"
              >
                Voltar ao início
              </Link>
            </div>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className="grid h-[100dvh] grid-rows-[auto_1fr] overflow-hidden pt-4">
      <div className="min-h-0 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          {error ? (
            <div role="alert" className="mb-4 rounded-[1.6rem] border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
              {error}
            </div>
          ) : null}
        </div>
      </div>
      <div className="min-h-0">
        <ChatShell
          inputDisabled={isLoading || isSubmitting || isRestarting}
          inputValue={draft}
          onInputChange={(event) => setDraft(event.target.value)}
          onInputValueChange={setDraft}
          onInputSubmit={handleSubmit}
          onRestart={handleRestart}
          restartDisabled={isLoading || isSubmitting || isRestarting}
          session={sessionView}
        />
      </div>
    </main>
  );
}
