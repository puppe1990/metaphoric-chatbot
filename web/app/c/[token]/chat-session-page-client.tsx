"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Select, { type StylesConfig } from "react-select";
import { ChatShell } from "../../../components/chat-shell";
import {
  AgentRequestError,
  getGuidedSessionView,
  getProviderConfig,
  getSession,
  sendMessage,
  setProviderConfig as saveProviderConfig,
  startSession,
  type AgentApiErrorDetail,
  type ChatMode,
  type GuidedSessionView,
  type ProviderConfig,
} from "../../../lib/api";
import { NEW_SESSION_TOKEN } from "../../../lib/session";

type ChatSessionPageClientProps = {
  requestedMode: ChatMode;
  token: string;
};

const PROVIDER_LABELS: Record<string, string> = {
  groq: "Groq",
  nvidia: "NVIDIA NIM",
  local: "Local (mock)",
};

type SelectOption = {
  value: string;
  label: string;
};

const selectStyles: StylesConfig<SelectOption, false> = {
  control: (base, state) => ({
    ...base,
    borderRadius: "0.75rem",
    borderColor: state.isFocused ? "#171912" : "rgba(0,0,0,0.1)",
    boxShadow: state.isFocused ? "0 0 0 2px rgba(23,25,18,0.12)" : base.boxShadow,
    backgroundColor: "#fff",
    padding: "2px 4px",
    fontSize: "0.875rem",
    "&:hover": { borderColor: "#171912" },
  }),
  option: (base, state) => ({
    ...base,
    fontSize: "0.875rem",
    backgroundColor: state.isSelected ? "#171912" : state.isFocused ? "#f4f6f1" : "#fff",
    color: state.isSelected ? "#fff" : "#171912",
  }),
  singleValue: (base) => ({ ...base, color: "#171912" }),
  menu: (base) => ({ ...base, borderRadius: "0.75rem", overflow: "hidden" }),
};

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected chat failure.";
}

function getProviderRecoveryError(error: unknown) {
  if (!(error instanceof AgentRequestError)) {
    return null;
  }

  if (!error.detail || typeof error.detail !== "object") {
    return null;
  }

  return error.detail.action === "switch_provider_or_model" ? error.detail : null;
}

export function ChatSessionPageClient({ requestedMode, token }: ChatSessionPageClientProps) {
  const router = useRouter();
  const [availableViewportHeight, setAvailableViewportHeight] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecoverySaving, setIsRecoverySaving] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalModel, setModalModel] = useState("");
  const [modalProvider, setModalProvider] = useState("groq");
  const [pendingRecoveryMessage, setPendingRecoveryMessage] = useState<string | null>(null);
  const [providerConfig, setProviderConfigState] = useState<ProviderConfig | null>(null);
  const [providerLabel, setProviderLabel] = useState<string | null>(null);
  const [providerModel, setProviderModel] = useState<string | null>(null);
  const [recoveryDetail, setRecoveryDetail] = useState<AgentApiErrorDetail | null>(null);
  const [sessionView, setSessionView] = useState<GuidedSessionView | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const isRecoveryModalOpen = recoveryDetail !== null;
  const providerOptions: SelectOption[] = [
    { value: "groq", label: "Groq" },
    { value: "nvidia", label: "NVIDIA NIM" },
    { value: "local", label: "Local (mock)" },
  ];
  const selectedProviderOption = providerOptions.find((option) => option.value === modalProvider) ?? null;

  const modalModelOptions: SelectOption[] =
    modalProvider === "groq"
      ? (providerConfig?.groq_models ?? []).map((model) => ({ value: model, label: model }))
      : modalProvider === "nvidia"
        ? (providerConfig?.nvidia_models ?? []).map((model) => ({ value: model, label: model }))
        : [];
  const selectedModelOption = modalModelOptions.find((option) => option.value === modalModel) ?? null;

  const syncProviderBadge = (config: Pick<ProviderConfig, "provider" | "model">) => {
    setProviderLabel(PROVIDER_LABELS[config.provider] ?? config.provider);
    setProviderModel(config.model);
  };

  const openProviderRecoveryModal = (detail: AgentApiErrorDetail, config: ProviderConfig | null, submittedMessage: string) => {
    const suggestedProvider = detail.provider ?? config?.provider ?? "groq";
    const availableModels =
      suggestedProvider === "groq"
        ? (config?.groq_models ?? [])
        : suggestedProvider === "nvidia"
          ? (config?.nvidia_models ?? [])
          : [];
    const suggestedModel =
      detail.model && availableModels.includes(detail.model)
        ? detail.model
        : availableModels[0] ?? "";

    setPendingRecoveryMessage(submittedMessage);
    setModalProvider(suggestedProvider);
    setModalModel(suggestedModel);
    setRecoveryDetail(detail);
  };

  const handleRecoveryProviderChange = (nextProvider: string) => {
    setModalProvider(nextProvider);

    if (nextProvider === "groq") {
      setModalModel(providerConfig?.groq_models[0] ?? "");
      return;
    }

    if (nextProvider === "nvidia") {
      setModalModel(providerConfig?.nvidia_models[0] ?? "");
      return;
    }

    setModalModel("");
  };

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const previousHtmlOverflow = html.style.overflow;
    const previousBodyOverflow = body.style.overflow;

    html.style.overflow = "hidden";
    body.style.overflow = "hidden";

    return () => {
      html.style.overflow = previousHtmlOverflow;
      body.style.overflow = previousBodyOverflow;
    };
  }, []);

  useEffect(() => {
    const updateAvailableHeight = () => {
      const header = document.querySelector<HTMLElement>("[data-app-header]");
      const headerHeight = header?.offsetHeight ?? 0;
      setAvailableViewportHeight(Math.max(window.innerHeight - headerHeight, 0));
    };

    updateAvailableHeight();
    window.addEventListener("resize", updateAvailableHeight);

    return () => {
      window.removeEventListener("resize", updateAvailableHeight);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    getProviderConfig()
      .then((config) => {
        if (cancelled) {
          return;
        }

        setProviderConfigState(config);
        syncProviderBadge(config);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }

        setProviderConfigState(null);
        setProviderLabel(null);
        setProviderModel(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function hydrateSession() {
      setIsLoading(true);
      setError(null);

      try {
        if (token === NEW_SESSION_TOKEN) {
          const started = await startSession(requestedMode);
          if (cancelled) {
            return;
          }

          setSessionView(getGuidedSessionView(started));
          router.replace(`/c/${started.token}?mode=${started.mode}`);
          return;
        }

        const restored = await getSession(token);
        if (cancelled) {
          return;
        }

        setSessionView(getGuidedSessionView(restored));
      } catch (caughtError) {
        if (!cancelled) {
          setSessionView(null);
          setError(getErrorMessage(caughtError));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void hydrateSession();

    return () => {
      cancelled = true;
    };
  }, [requestedMode, retryKey, router, token]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!sessionView || isSubmitting) {
      return;
    }

    const content = draft.trim();
    if (!content) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const updated = await sendMessage(sessionView.token, content);
      setSessionView(getGuidedSessionView(updated));
      setDraft("");
      setPendingRecoveryMessage(null);
      setRecoveryDetail(null);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      const providerRecovery = getProviderRecoveryError(caughtError);
      if (providerRecovery) {
        openProviderRecoveryModal(providerRecovery, providerConfig, content);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRestart() {
    if (!sessionView || isRestarting) {
      return;
    }

    setIsRestarting(true);
    setError(null);

    try {
      const started = await startSession(sessionView.mode);
      setSessionView(getGuidedSessionView(started));
      setDraft("");
      router.replace(`/c/${started.token}?mode=${started.mode}`);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
    } finally {
      setIsRestarting(false);
    }
  }

  async function handleRecoverySaveAndRetry() {
    if (!sessionView || !pendingRecoveryMessage || isRecoverySaving) {
      return;
    }

    setIsRecoverySaving(true);
    setError(null);

    try {
      const nextModel = modalProvider === "local" ? "local" : modalModel;
      const savedConfig = await saveProviderConfig(modalProvider, nextModel);
      const nextConfig = providerConfig
        ? { ...providerConfig, provider: savedConfig.provider, model: savedConfig.model }
        : {
            provider: savedConfig.provider,
            model: savedConfig.model,
            groq_models: [],
            nvidia_models: [],
          };

      setProviderConfigState(nextConfig);
      syncProviderBadge(savedConfig);

      const updated = await sendMessage(sessionView.token, pendingRecoveryMessage);
      setSessionView(getGuidedSessionView(updated));
      setDraft("");
      setPendingRecoveryMessage(null);
      setRecoveryDetail(null);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      const providerRecovery = getProviderRecoveryError(caughtError);
      if (providerRecovery) {
        openProviderRecoveryModal(providerRecovery, providerConfig, pendingRecoveryMessage);
      } else {
        setRecoveryDetail(null);
      }
    } finally {
      setIsRecoverySaving(false);
    }
  }

  if (!sessionView) {
    return (
      <main className="min-h-screen px-4 py-6 text-ink sm:px-6 lg:px-8">
        <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-3xl flex-col justify-center gap-4 rounded-[2rem] border border-black/10 bg-white/80 p-8 shadow-[0_18px_70px_rgba(16,19,31,0.08)]">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">
            {token === NEW_SESSION_TOKEN ? "Iniciando sessão" : "Carregando sessão"}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">O chat depende do agent service.</h1>
          <p className="text-base leading-7 text-clay">
            {isLoading
              ? "Tentando conectar e recuperar o estado desta conversa."
              : "A conversa não pôde ser carregada agora."}
          </p>
          {error ? (
            <div role="alert" className="rounded-[1.4rem] border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
              {error}
            </div>
          ) : null}
          {!isLoading ? (
            <div className="flex flex-wrap gap-3">
              <button
                className="w-fit rounded-full bg-ink px-4 py-2 text-sm font-semibold text-fog"
                onClick={() => setRetryKey((value) => value + 1)}
                type="button"
              >
                Tentar novamente
              </button>
              <Link
                href="/"
                className="w-fit rounded-full border border-ink/10 bg-white px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-fog"
              >
                Voltar ao início
              </Link>
            </div>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main
      className="flex min-h-0 flex-col overflow-x-hidden overflow-y-hidden"
      style={availableViewportHeight ? { height: `${availableViewportHeight}px` } : undefined}
    >
      <div className="min-h-0 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          {error ? (
            <div role="alert" className="mb-4 rounded-[1.6rem] border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
              {error}
            </div>
          ) : null}
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <ChatShell
          activeModel={providerModel ?? undefined}
          activeProviderLabel={providerLabel ?? undefined}
          inputDisabled={isLoading || isSubmitting || isRestarting || isRecoverySaving}
          isThinking={isSubmitting || isRecoverySaving}
          inputValue={draft}
          onInputChange={(event) => setDraft(event.target.value)}
          onInputValueChange={setDraft}
          onInputSubmit={handleSubmit}
          onRestart={handleRestart}
          restartDisabled={isLoading || isSubmitting || isRestarting || isRecoverySaving}
          session={sessionView}
        />
      </div>
      {isRecoveryModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 px-4">
          <div
            aria-labelledby="provider-recovery-title"
            aria-modal="true"
            className="w-full max-w-2xl rounded-[1.8rem] border border-black/10 bg-white p-6 shadow-[0_28px_90px_rgba(23,25,18,0.22)] sm:p-7"
            role="dialog"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Troca rápida</p>
            <h2 id="provider-recovery-title" className="mt-2 text-2xl font-semibold tracking-tight text-ink">
              Trocar provider ou modelo
            </h2>
            <p className="mt-3 text-sm leading-6 text-clay">{recoveryDetail.message}</p>

            <div className="mt-6 flex flex-col gap-5">
              <fieldset className="flex flex-col gap-2">
                <label className="flex flex-col gap-2 text-sm text-ink" htmlFor="recovery-provider-select">
                  <span className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Provider</span>
                  <Select
                    inputId="recovery-provider-select"
                    isSearchable={false}
                    onChange={(option) => option && handleRecoveryProviderChange(option.value)}
                    options={providerOptions}
                    styles={selectStyles}
                    value={selectedProviderOption}
                  />
                </label>
              </fieldset>

              {modalProvider !== "local" ? (
                <label className="flex flex-col gap-2 text-sm text-ink" htmlFor="recovery-model-select">
                  <span className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">Modelo</span>
                  <Select
                    id="recovery-model-select"
                    inputId="recovery-model-select"
                    isSearchable
                    onChange={(option) => option && setModalModel(option.value)}
                    options={modalModelOptions}
                    placeholder="Selecione um modelo..."
                    styles={selectStyles}
                    value={selectedModelOption}
                  />
                </label>
              ) : (
                <p className="rounded-xl border border-black/10 bg-fog/70 px-4 py-3 text-sm text-clay">
                  Modo local usa respostas fixas e ignora a chamada ao provider externo.
                </p>
              )}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                className="rounded-full border border-ink bg-ink px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-ink/85 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isRecoverySaving || (modalProvider !== "local" && !modalModel)}
                onClick={handleRecoverySaveAndRetry}
                type="button"
              >
                {isRecoverySaving ? "Salvando..." : "Salvar e tentar de novo"}
              </button>
              <button
                className="rounded-full border border-black/10 bg-white px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-fog"
                onClick={() => setRecoveryDetail(null)}
                type="button"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
