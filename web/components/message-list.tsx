import React from "react";
import { isReceiveChoiceArtifact, type ChatArtifact, type ChatMessage } from "../lib/api";
import { MetaphorChoiceList } from "./metaphor-choice-list";

function getMessageTone(role: ChatMessage["role"]) {
  return role === "assistant"
    ? "border-ink/10 bg-white text-ink"
    : role === "user"
      ? "border-ink bg-ink text-fog"
      : "border-ember/25 bg-ember/10 text-ink";
}

function getMessageLabel(role: ChatMessage["role"]) {
  if (role === "assistant") return "Assistente";
  if (role === "user") return "Você";
  return "Sistema";
}

function findLatestAssistantMessageIndex(messages: ChatMessage[]) {
  return [...messages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find(({ message }) => message.role === "assistant")?.index ?? -1;
}

export function MessageList({
  artifacts = [],
  disabled = false,
  isThinking = false,
  messages,
  onChoiceSelect,
}: {
  messages: ChatMessage[];
  artifacts?: ChatArtifact[];
  disabled?: boolean;
  isThinking?: boolean;
  onChoiceSelect?: (label: "A" | "B" | "C" | "D" | "E") => void;
}) {
  const receiveChoiceArtifact = [...artifacts].reverse().find(
    (artifact) => isReceiveChoiceArtifact(artifact) && artifact.metadata?.selected_option == null,
  );
  const receiveChoiceMessageIndex = receiveChoiceArtifact ? findLatestAssistantMessageIndex(messages) : -1;

  return (
    <ol aria-label="Chat messages" className="space-y-3">
      {messages.map((message, index) => (
        <li
          key={`${message.role}-${index}`}
          className={[
            "max-w-[88%] rounded-lg border px-4 py-3 sm:px-5",
            message.role === "user" ? "ml-auto" : "mr-auto",
            getMessageTone(message.role),
          ].join(" ")}
        >
          <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] opacity-70">
            {getMessageLabel(message.role)}
          </p>
          <p className="whitespace-pre-wrap text-sm leading-6 sm:text-[0.98rem]">{message.content}</p>
          {index === receiveChoiceMessageIndex && receiveChoiceArtifact ? (
            <MetaphorChoiceList choices={receiveChoiceArtifact.choices} disabled={disabled} onSelect={onChoiceSelect} />
          ) : null}
        </li>
      ))}
      {isThinking ? (
        <li
          className={[
            "mr-auto max-w-[88%] rounded-lg border border-ink/10 bg-white px-4 py-3 text-ink sm:px-5",
            "animate-pulse",
          ].join(" ")}
        >
          <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] opacity-70">Assistente</p>
          <p className="whitespace-pre-wrap text-sm leading-6 sm:text-[0.98rem]">Pensando...</p>
        </li>
      ) : null}
    </ol>
  );
}
