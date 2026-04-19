import React from "react";
import { ModeCard } from "../components/mode-card";

const modes = [
  {
    title: "Receber uma metáfora",
    description: "Descreva um conflito e receba uma metáfora curta, concreta e refinável.",
    href: "/c/new?mode=receive",
  },
  {
    title: "Construir minha metáfora",
    description: "Transforme abstração em imagem com crítica técnica e reescrita guiada.",
    href: "/c/new?mode=build",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-10 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-6xl flex-col justify-center gap-10">
        <section className="max-w-3xl">
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
        </section>

        <section aria-label="Choose a mode" className="grid gap-5 lg:grid-cols-2">
          {modes.map((mode) => (
            <ModeCard key={mode.title} description={mode.description} href={mode.href} title={mode.title} />
          ))}
        </section>
      </div>
    </main>
  );
}
