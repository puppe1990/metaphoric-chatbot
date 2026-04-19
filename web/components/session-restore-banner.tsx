"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import type { RecentSession } from "../lib/session";
import { loadRecentSessions, rememberRecentSession } from "../lib/session";

type SessionRestoreBannerProps = {
  currentSession: Omit<RecentSession, "updatedAt">;
};

export function SessionRestoreBanner({ currentSession }: SessionRestoreBannerProps) {
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);

  useEffect(() => {
    rememberRecentSession(currentSession);
    setRecentSessions(
      loadRecentSessions().filter(
        (session) => session.token !== currentSession.token || session.mode !== currentSession.mode,
      ),
    );
  }, [currentSession]);

  if (recentSessions.length === 0) {
    return (
      <section className="rounded-lg border border-ink/10 bg-white/82 px-4 py-3 text-sm text-clay">
        Esta sessão será lembrada neste navegador para facilitar a retomada mais tarde.
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-ink/10 bg-white/82 px-4 py-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Restaurar sessão</p>
          <p className="mt-1 text-sm text-clay">Sessões recentes salvas neste navegador.</p>
        </div>
        <p className="text-xs uppercase tracking-[0.16em] text-clay">{recentSessions.length} disponíveis</p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {recentSessions.map((session) => (
          <Link
            key={`${session.token}-${session.mode}`}
            href={`/c/${session.token}?mode=${session.mode}`}
            className="rounded-lg border border-ink/10 bg-fog px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-white"
          >
            {session.mode === "build" ? "Construir" : "Receber"} · {session.progressLabel}
          </Link>
        ))}
      </div>
    </section>
  );
}
