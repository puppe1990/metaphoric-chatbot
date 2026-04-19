import {
  isReceiveChoiceArtifact,
  isReceiveFinalComparisonArtifact,
  type ChatArtifact,
  type ChatMessage,
  type GuidedSessionView,
} from "./api";

function getMarkdownHeading(role: ChatMessage["role"]) {
  if (role === "assistant") return "Assistente";
  if (role === "user") return "Voce";
  return "System";
}

function findLatestAssistantMessageIndex(messages: ChatMessage[]) {
  return [...messages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find(({ message }) => message.role === "assistant")?.index ?? -1;
}

function findPresentedChoices(artifacts: ChatArtifact[], messages: ChatMessage[]) {
  const receiveChoiceArtifact = [...artifacts].reverse().find(
    (artifact) => isReceiveChoiceArtifact(artifact) && artifact.metadata?.selected_option == null,
  );

  if (!receiveChoiceArtifact) {
    return null;
  }

  return {
    artifact: receiveChoiceArtifact,
    messageIndex: findLatestAssistantMessageIndex(messages),
  };
}

function findFinalComparison(artifacts: ChatArtifact[], messages: ChatMessage[]) {
  const comparisonArtifact = [...artifacts].reverse().find(isReceiveFinalComparisonArtifact);
  if (!comparisonArtifact) {
    return null;
  }

  return {
    artifact: comparisonArtifact,
    messageIndex: findLatestAssistantMessageIndex(messages),
  };
}

export function buildChatMarkdown(session: GuidedSessionView) {
  const presentedChoices = findPresentedChoices(session.artifacts, session.messages);
  const finalComparison = findFinalComparison(session.artifacts, session.messages);
  const lines: string[] = [
    `# ${session.title}`,
    "",
    `- Token: ${session.token}`,
    `- Modo: ${session.mode}`,
    `- Progresso: ${session.progressLabel}`,
  ];

  for (const [index, message] of session.messages.entries()) {
    lines.push("", `## ${getMarkdownHeading(message.role)}`, "", message.content);

    if (presentedChoices && presentedChoices.messageIndex === index) {
      lines.push("", "### Opcoes apresentadas", "");

      for (const choice of presentedChoices.artifact.choices) {
        lines.push(`- ${choice.label}: ${choice.text}`);
      }
    }

    if (finalComparison && finalComparison.messageIndex === index) {
      lines.push("", "### Comparação final", "");

      for (const variant of finalComparison.artifact.comparison_variants) {
        lines.push(`#### ${variant.title}`, "", variant.text, "");
      }
    }
  }

  lines.push("");

  return lines.join("\n");
}

export function downloadChatMarkdown(session: GuidedSessionView) {
  const markdown = buildChatMarkdown(session);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = objectUrl;
  link.download = `conversa-${session.token}.md`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(objectUrl);
}
