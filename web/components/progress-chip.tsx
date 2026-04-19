import React from "react";

function formatProgressLabel(label: string) {
  return label
    .replace(/_/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase()
    .replace(/^\w|\s\w/g, (match) => match.toUpperCase());
}

export function ProgressChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-lg border border-ink/10 bg-white px-3 py-1.5 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-clay">
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-ember" />
      {formatProgressLabel(label)}
    </span>
  );
}
