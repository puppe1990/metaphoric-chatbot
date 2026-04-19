"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import type { RecentSession } from "../lib/session";
import { loadRecentSessions } from "../lib/session";

export function RecentConversationsPanel() {
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);

  useEffect(() => {
    setRecentSessions(loadRecentSessions());
  }, []);

  if (recentSessions.length === 0) {
    return null;
  }

  return (
    <section className="rounded-[1.75rem] border border-black/10 bg-white/78 p-6 shadow-glow backdrop-blur">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Conversas antigas</p>
          <p className="mt-1 text-sm text-clay">Retome qualquer sessão recente salva neste navegador.</p>
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
