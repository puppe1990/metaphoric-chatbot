import React from "react";

type ArtifactPanelProps = {
  title: string;
  body: string;
  notes: string[];
  sessionToken?: string;
};

export function ArtifactPanel({ body, notes, sessionToken, title }: ArtifactPanelProps) {
  return (
    <aside className="rounded-[2rem] border border-black/10 bg-[linear-gradient(180deg,rgba(255,252,247,0.94),rgba(244,237,228,0.86))] p-6 shadow-[0_16px_60px_rgba(16,19,31,0.08)]">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Painel de artefatos</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink">{title}</h2>
      <p className="mt-4 text-sm leading-6 text-clay">{body}</p>

      <div className="mt-6 rounded-[1.4rem] border border-black/10 bg-white/80 p-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-clay">Sessão</p>
        <p className="mt-2 text-sm font-medium text-ink">{sessionToken ?? "Sessão guiada sem token carregado."}</p>
      </div>

      <ul className="mt-6 space-y-3 text-sm leading-6 text-ink">
        {notes.map((note) => (
          <li key={note} className="rounded-[1.1rem] border border-black/10 bg-white/70 px-4 py-3">
            {note}
          </li>
        ))}
      </ul>
    </aside>
  );
}
