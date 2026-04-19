import React from "react";
import type { MetaphorChoice } from "../lib/api";

type MetaphorChoiceListProps = {
  choices: MetaphorChoice[];
  disabled?: boolean;
  onSelect?: (label: MetaphorChoice["label"]) => void;
};

export function MetaphorChoiceList({ choices, disabled = false, onSelect }: MetaphorChoiceListProps) {
  if (choices.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2" role="group" aria-label="Metaphor choices">
      {choices.map((choice) => (
        <button
          key={choice.label}
          aria-label={`${choice.label} ${choice.text}`}
          className="flex w-full items-start gap-3 rounded-lg border border-ink/10 bg-fog px-3 py-3 text-left text-ink transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          onClick={() => onSelect?.(choice.label)}
          type="button"
        >
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-ink/15 bg-white text-xs font-semibold uppercase tracking-[0.16em]">
            {choice.label}
          </span>
          <span className="pt-0.5 text-sm leading-6 sm:text-[0.98rem]">{choice.text}</span>
        </button>
      ))}
    </div>
  );
}
