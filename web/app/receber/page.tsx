import React from "react";
import { ModePageHero } from "../../components/mode-page-hero";

export default function ReceiveModePage() {
  return (
    <ModePageHero
      description="Traga um conflito, um impasse ou uma sensação difícil de nomear."
      helper="Você descreve o que está pegando, recebe uma imagem enxuta e pode refiná-la até ela soar precisa."
      startHref="/c/new?mode=receive"
      startLabel="Começar sessão de recebimento"
      title="Receber uma metáfora"
    />
  );
}
