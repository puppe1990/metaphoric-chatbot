import React from "react";
import Link from "next/link";

const navigationLinks = [
  { href: "/", label: "Início" },
  { href: "/receber", label: "Receber uma metáfora" },
  { href: "/construir", label: "Construir minha metáfora" },
  { href: "/config", label: "Configurações" },
];

export function AppHeader() {
  return (
    <header className="border-b border-black/10 bg-white/70 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-6 py-4 sm:px-8 lg:flex-row lg:items-center lg:justify-between lg:px-12">
        <Link href="/" className="w-fit">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-clay">Metaphoric Chatbot</p>
            <p className="mt-2 text-sm text-clay">Navegação do sistema</p>
          </div>
        </Link>

        <nav aria-label="Navegação principal" className="flex flex-wrap gap-2">
          {navigationLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-full border border-black/10 bg-white px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-fog"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
