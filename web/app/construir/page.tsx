import React from "react";
import { ModePageHero } from "../../components/mode-page-hero";

export default function BuildModePage() {
  return (
    <ModePageHero
      description="Escolha a situação que você quer traduzir e trabalhe a imagem em etapas."
      helper="Você parte de um rascunho, recebe crítica guiada e reescreve até a metáfora ficar concreta, nítida e viva."
      startHref="/c/new?mode=build"
      startLabel="Começar sessão de construção"
      title="Construir minha metáfora"
    />
  );
}
