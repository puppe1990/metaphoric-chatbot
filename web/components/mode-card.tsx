import React from "react";
import Link from "next/link";

type ModeCardProps = {
  title: string;
  description: string;
  href: string;
};

export function ModeCard({ description, href, title }: ModeCardProps) {
  return (
    <Link
      href={href}
      className="mode-card group flex h-full flex-col gap-4 transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ember focus-visible:ring-offset-2"
    >
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Modo guiado</p>
        <span className="rounded-full border border-black/10 px-3 py-1 text-[0.68rem] font-medium uppercase tracking-[0.22em] text-clay">
          Ir
        </span>
      </div>

      <div className="space-y-3">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">{title}</h2>
        <p className="max-w-xl text-sm leading-6 text-clay sm:text-base">{description}</p>
      </div>

      <div className="mt-auto flex items-center justify-between border-t border-black/10 pt-4 text-sm text-ink">
        <span>Começar</span>
        <span aria-hidden="true" className="text-lg leading-none">
          →
        </span>
      </div>
    </Link>
  );
}
