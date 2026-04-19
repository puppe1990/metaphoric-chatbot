import React from "react";
import Link from "next/link";

type ModePageHeroProps = {
  title: string;
  description: string;
  helper: string;
  startHref: string;
  startLabel: string;
};

export function ModePageHero({ description, helper, startHref, startLabel, title }: ModePageHeroProps) {
  return (
    <main className="min-h-[calc(100dvh-5.5rem)] px-6 py-10 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto grid w-full max-w-6xl gap-6 rounded-[2rem] border border-black/10 bg-white/78 p-8 shadow-glow backdrop-blur sm:p-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
        <section className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-clay">Modo guiado</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">{title}</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-clay sm:text-lg">{description}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href={startHref}
              className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-fog transition-opacity hover:opacity-92"
            >
              {startLabel}
            </Link>
            <Link
              href="/"
              className="rounded-full border border-black/10 bg-white px-5 py-3 text-sm font-semibold text-ink transition-colors hover:bg-fog"
            >
              Voltar ao início
            </Link>
          </div>
        </section>

        <aside className="rounded-[1.75rem] border border-black/10 bg-fog/80 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Antes de começar</p>
          <p className="mt-3 text-sm leading-6 text-clay sm:text-base">{helper}</p>
        </aside>
      </div>
    </main>
  );
}
