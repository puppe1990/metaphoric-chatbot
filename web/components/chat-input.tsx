import React from "react";

type ChatInputProps = {
  value: string;
  onChange: React.ChangeEventHandler<HTMLTextAreaElement>;
  onValueChange?: (value: string) => void;
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  formRef?: React.RefObject<HTMLFormElement | null>;
  placeholder?: string;
  helperText?: string;
  suggestions?: string[];
  disabled?: boolean;
};

export function ChatInput({
  disabled = false,
  formRef,
  helperText = "Envie sua resposta para avançar o estado guiado desta conversa.",
  onChange,
  onValueChange,
  onSubmit,
  placeholder = "Escreva sua resposta...",
  value,
  suggestions = [],
}: ChatInputProps) {
  const handleSuggestionClick = (suggestion: string) => {
    onValueChange?.(suggestion);
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key !== "Enter") {
      return;
    }

    if (event.shiftKey || event.altKey || event.ctrlKey || event.metaKey || event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  };

  return (
    <form className="border-t border-ink/10 bg-fog/85 px-4 py-4 backdrop-blur sm:px-5" onSubmit={onSubmit} ref={formRef}>
      <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-clay">
        Sua próxima linha
      </label>
      <div className="rounded-lg border border-ink/10 bg-white p-3">
        <textarea
          aria-label="Message input"
          className="min-h-[84px] w-full resize-none border-0 bg-transparent px-1 py-1 text-sm leading-6 text-ink outline-none placeholder:text-clay/70"
          disabled={disabled}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          value={value}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => handleSuggestionClick(suggestion)}
              className="rounded-lg border border-ink/10 bg-fog px-3 py-1.5 text-left text-xs font-medium text-clay transition-colors hover:border-ink/20 hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
              disabled={disabled}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-clay">
        <p>{helperText}</p>
        <button
          className="rounded-lg bg-ink px-4 py-2 font-semibold text-fog transition-transform active:translate-y-px disabled:cursor-not-allowed disabled:opacity-70"
          disabled={disabled}
          type="submit"
        >
          Enviar
        </button>
      </div>
    </form>
  );
}
