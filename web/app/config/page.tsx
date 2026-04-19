"use client";

import React, { useEffect, useState } from "react";
import Select, { type StylesConfig } from "react-select";
import { getProviderConfig, setProviderConfig, type ProviderConfig } from "../../lib/api";

type Status = "idle" | "loading" | "saving" | "saved" | "error";

const PROVIDER_LABELS: Record<string, string> = {
  groq: "Groq",
  nvidia: "NVIDIA NIM",
  local: "Local (mock)",
};

type Option = { value: string; label: string };

const selectStyles: StylesConfig<Option> = {
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

export default function ConfigPage() {
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProviderConfig()
      .then((data) => {
        setConfig(data);
        setProvider(data.provider);
        setModel(data.model);
        setStatus("idle");
      })
      .catch((err) => {
        setError(String(err.message));
        setStatus("error");
      });
  }, []);

  function handleProviderChange(p: string) {
    setProvider(p);
    if (p === "groq") setModel((config?.groq_models ?? [])[0] ?? "llama-3.3-70b-versatile");
    if (p === "nvidia") setModel((config?.nvidia_models ?? [])[0] ?? "meta/llama-3.3-70b-instruct");
  }

  async function handleSave() {
    setStatus("saving");
    setError(null);
    try {
      await setProviderConfig(provider, model);
      setConfig((prev) => (prev ? { ...prev, provider, model } : prev));
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  const modelList =
    provider === "groq"
      ? (config?.groq_models ?? ["llama-3.3-70b-versatile"])
      : provider === "nvidia"
        ? (config?.nvidia_models ?? ["meta/llama-3.3-70b-instruct"])
        : [];

  const modelOptions: Option[] = modelList.map((m) => ({ value: m, label: m }));
  const selectedOption = modelOptions.find((o) => o.value === model) ?? null;
  const isDirty = config && (provider !== config.provider || model !== config.model);

  return (
    <main className="min-h-[calc(100dvh-5.5rem)] px-6 py-10 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto w-full max-w-2xl">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.32em] text-clay">Sistema</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Configurações</h1>
        <p className="mt-3 text-sm leading-6 text-clay">
          Escolha o provider e o modelo de linguagem usado pelo backend.
        </p>

        <section className="mt-8 rounded-[2rem] border border-black/10 bg-white/76 p-8 shadow-glow backdrop-blur">
          {status === "loading" ? (
            <p className="text-sm text-clay">Carregando configuração…</p>
          ) : (
            <div className="flex flex-col gap-6">
              <fieldset className="flex flex-col gap-2">
                <legend className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Provider</legend>
                <div className="mt-2 flex flex-wrap gap-3">
                  {Object.entries(PROVIDER_LABELS).map(([p, label]) => (
                    <button
                      key={p}
                      onClick={() => handleProviderChange(p)}
                      className={`rounded-full border px-5 py-2 text-sm font-semibold transition-colors ${
                        provider === p
                          ? "border-ink bg-ink text-white"
                          : "border-black/10 bg-white text-ink hover:bg-fog"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>

              {modelOptions.length > 0 && (
                <div className="flex flex-col gap-2">
                  <label
                    htmlFor="model-select"
                    className="text-xs font-semibold uppercase tracking-[0.28em] text-clay"
                  >
                    Modelo
                  </label>
                  <Select
                    inputId="model-select"
                    options={modelOptions}
                    value={selectedOption}
                    onChange={(opt) => opt && !Array.isArray(opt) && setModel((opt as Option).value)}
                    styles={selectStyles}
                    isSearchable
                    placeholder="Selecione um modelo…"
                  />
                </div>
              )}

              {provider === "local" && (
                <p className="rounded-xl border border-black/10 bg-fog/70 px-4 py-3 text-sm text-clay">
                  Modo local usa respostas fixas sem chamada de API. Útil para testes sem chave de API.
                </p>
              )}

              {provider === "nvidia" && (
                <p className="rounded-xl border border-black/10 bg-fog/70 px-4 py-3 text-sm text-clay">
                  Requer <code className="font-mono text-xs">NVIDIA_API_KEY</code> configurada no backend.
                </p>
              )}

              {error && (
                <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
              )}

              <div className="flex items-center gap-4">
                <button
                  onClick={handleSave}
                  disabled={status === "saving" || (!isDirty && status !== "error")}
                  className="rounded-full border border-ink bg-ink px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-ink/80 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {status === "saving" ? "Salvando…" : "Salvar"}
                </button>
                {status === "saved" && (
                  <p className="text-sm font-semibold text-green-600">Configuração salva.</p>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
