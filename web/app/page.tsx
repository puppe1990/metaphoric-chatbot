import React from "react";
import { ModeCard } from "../components/mode-card";
import { RecentConversationsPanel } from "../components/recent-conversations-panel";

const modes = [
  {
    title: "Receber uma metáfora",
    description: "Descreva um conflito e receba uma metáfora curta, concreta e refinável.",
    href: "/receber",
  },
  {
    title: "Construir minha metáfora",
    description: "Transforme abstração em imagem com crítica técnica e reescrita guiada.",
    href: "/construir",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-[calc(100dvh-5.5rem)] px-6 py-10 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
        <section className="grid gap-6 rounded-[2rem] border border-black/10 bg-white/76 p-8 shadow-glow backdrop-blur sm:p-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
          <div className="max-w-3xl">
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.32em] text-clay">
              Metaphoric Chatbot
            </p>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl lg:text-6xl">
              Um chat guiado para receber metáforas ou aprender a construí-las.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-clay sm:text-lg">
              Escolha se você quer receber uma metáfora pronta ou aprender a construir uma.
              A experiência permanece apenas em texto, estruturada e calma.
            </p>
          </div>

          <aside className="rounded-[1.75rem] border border-black/10 bg-white/82 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Visão geral</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
              Dois caminhos para trabalhar uma imagem com calma e precisão.
            </h2>
            <p className="mt-3 text-sm leading-6 text-clay sm:text-base">
              Escolha um modo para começar quando quiser.
            </p>

            <div className="mt-6 space-y-4">
              <div className="rounded-[1.4rem] border border-black/10 bg-fog/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Receber</p>
                <p className="mt-2 text-sm leading-6 text-clay">
                  Receba uma imagem curta para enxergar o problema por outro ângulo.
                </p>
              </div>

              <div className="rounded-[1.4rem] border border-black/10 bg-fog/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Construir</p>
                <p className="mt-2 text-sm leading-6 text-clay">
                  Parta de uma ideia abstrata e lapide uma imagem concreta até ela ganhar força.
                </p>
              </div>
            </div>
          </aside>
        </section>

        <section aria-label="Choose a mode" className="grid gap-5 lg:grid-cols-2">
          {modes.map((mode) => (
            <ModeCard key={mode.title} description={mode.description} href={mode.href} title={mode.title} />
          ))}
        </section>

        <RecentConversationsPanel />
      </div>
    </main>
  );
}
