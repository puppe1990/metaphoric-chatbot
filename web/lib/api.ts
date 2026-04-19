const DEFAULT_AGENT_BASE_URL = process.env.NEXT_PUBLIC_AGENT_BASE_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 8000;

export type ChatMode = "receive" | "build";
export type ChatRole = "assistant" | "user" | "system";

export type ChatMessage = {
  role: ChatRole;
  content: string;
};

export type AgentApiErrorDetail = {
  code?: string;
  message?: string;
  provider?: string;
  model?: string;
  retryable?: boolean;
  action?: string;
};

export class AgentRequestError extends Error {
  status: number;
  detail: string | AgentApiErrorDetail | null;

  constructor(status: number, detail: string | AgentApiErrorDetail | null, fallbackMessage: string) {
    const message =
      typeof detail === "object" && detail !== null && typeof detail.message === "string"
        ? detail.message
        : typeof detail === "string"
          ? detail
          : fallbackMessage;
    super(message);
    this.name = "AgentRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export const RECEIVE_CHOICE_ARTIFACT_TYPE = "receive_choice";

export type MetaphorChoice = {
  label: "A" | "B" | "C" | "D" | "E";
  text: string;
};

export type ArtifactMetadata = {
  clarifier_asked: boolean;
  internal_candidate_count: number;
  selected_option: "A" | "B" | "C" | "D" | "E" | null;
};

type BaseChatArtifact = {
  artifact_type: string;
  content: string;
  metadata: ArtifactMetadata | null;
  choices: MetaphorChoice[];
};

export type ReceiveChoiceArtifact = {
  artifact_type: typeof RECEIVE_CHOICE_ARTIFACT_TYPE;
  content: string;
  metadata: ArtifactMetadata | null;
  choices: MetaphorChoice[];
};

export type ChatArtifact = ReceiveChoiceArtifact | BaseChatArtifact;

export function isReceiveChoiceArtifact(artifact: ChatArtifact): artifact is ReceiveChoiceArtifact {
  return artifact.artifact_type === RECEIVE_CHOICE_ARTIFACT_TYPE && artifact.choices.length > 0;
}

export type SessionStartResponse = {
  token: string;
  mode: ChatMode;
  state: string;
  assistant_message: string;
  artifacts: ChatArtifact[];
};

export type SendMessageResponse = {
  token: string;
  mode: ChatMode;
  state: string;
  messages: ChatMessage[];
  artifacts: ChatArtifact[];
};

export type SessionResponse = {
  token: string;
  mode: ChatMode;
  state: string;
  messages: ChatMessage[];
  artifacts: ChatArtifact[];
};

export type GuidedSessionView = {
  token: string;
  mode: ChatMode;
  title: string;
  description: string;
  progressLabel: string;
  messages: ChatMessage[];
  artifacts: ChatArtifact[];
  artifactTitle: string;
  artifactBody: string;
  suggestions: string[];
};

const GUIDED_STARTERS: Record<
  ChatMode,
  Pick<GuidedSessionView, "title" | "progressLabel" | "artifactTitle" | "artifactBody"> & {
    prompt: string;
  }
> = {
  receive: {
    title: "Receber uma metáfora",
    progressLabel: "intake_problem",
    prompt: "Descreva o problema em uma frase simples.",
    artifactTitle: "Receita da metáfora",
    artifactBody: "O shell vai mostrar a forma, o contraste e o gesto da imagem quando o fluxo ganhar backend.",
  },
  build: {
    title: "Construir minha metáfora",
    progressLabel: "sharpen_image",
    prompt: "Nomeie a coisa concreta que você quer transformar em imagem.",
    artifactTitle: "Mapa simbólico",
    artifactBody: "Aqui entra o trabalho de lapidar imagem, ritmo e contraste antes da primeira resposta real.",
  },
};

const SUGGESTIONS_BY_MODE_AND_STATE: Record<ChatMode, Record<string, string[]>> = {
  receive: {
    intake_problem: [
      "Estou travado para tomar uma decisão.",
      "Tenho pressa e não consigo organizar as ideias.",
      "Sei o que quero, mas fico adiando.",
    ],
    intake_feeling: ["Ansiedade.", "Pressa.", "Confusão."],
    intake_desired_shift: [
      "Quero clareza e menos pressa.",
      "Quero sentir firmeza para escolher.",
      "Quero ver o próximo passo.",
    ],
    symbolic_mapping: [
      "Pode gerar uma metáfora curta.",
      "Quero algo mais direto.",
      "Prefiro uma imagem mais simples.",
    ],
    generate_metaphor: ["Mais curto.", "Mais concreto.", "Mais suave."],
    refine_output: ["Mais curto.", "Mais prático.", "Troque a imagem central."],
  },
  build: {
    intake_problem: [
      "Quero chegar em alguém por quem sinto atração.",
      "Quero explicar uma ansiedade que me acelera.",
      "Tenho uma ideia, mas ela fica confusa.",
    ],
    identify_core_conflict: ["Desejo versus medo.", "Pressa versus clareza.", "Controle versus espontaneidade."],
    offer_symbolic_fields: [
      "Natureza: plantio, colheita, raiz, crescimento.",
      "Guerra / estratégia: batalha, território, ataque, defesa.",
      "Jornada / viagem: caminho, mapa, destino.",
      "Máquina / engenharia: sistema, engrenagem, processo.",
      "Energia / física: calor, pressão, força.",
    ],
    user_selects_symbol: [
      "Quero ir por natureza.",
      "Quero ir por guerra / estratégia.",
      "Quero ir por jornada / viagem.",
      "Quero ir por máquina / engenharia.",
      "Quero ir por energia / física.",
    ],
    user_attempt: [
      "Isso parece uma raiz tentando firmar espaço em chão ruim.",
      "Isso parece uma batalha em que eu gasto energia cedo demais.",
      "Isso parece um caminho sem mapa claro.",
      "Isso parece um sistema rodando, mas sem encaixar direito.",
      "Isso parece pressão acumulando sem virar movimento.",
    ],
    coach_feedback: ["Quero deixar mais concreto.", "Quero menos clichê.", "Quero mais movimento."],
    rewrite_together: ["Mais curto.", "Mais estranho.", "Mais claro."],
  },
};

export function normalizeMode(mode: string | string[] | undefined): ChatMode {
  const value = Array.isArray(mode) ? mode[0] : mode;
  return value === "build" ? "build" : "receive";
}

function getAgentUnavailableError() {
  return new Error(`Agent service is unavailable. Verify it is running at ${DEFAULT_AGENT_BASE_URL}.`);
}

async function parseResponseBody(response: Response) {
  const raw = await response.text();
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${DEFAULT_AGENT_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
    });
    const payload = await parseResponseBody(response);

    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? (payload.detail as string | AgentApiErrorDetail | null)
          : typeof payload === "string"
            ? payload
            : null;
      throw new AgentRequestError(
        response.status,
        detail,
        `Agent request failed (${response.status}): ${response.statusText}`,
      );
    }

    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        `Agent service timed out after ${REQUEST_TIMEOUT_MS}ms. Verify it is running at ${DEFAULT_AGENT_BASE_URL}.`,
      );
    }

    if (error instanceof TypeError) {
      throw getAgentUnavailableError();
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getModeMeta(mode: ChatMode) {
  return GUIDED_STARTERS[mode];
}

export function getGuidedSessionView(
  session: Pick<SessionResponse, "token" | "mode" | "state"> &
    Partial<Pick<SessionResponse, "messages">> &
    Partial<Pick<SessionResponse, "artifacts">> &
    Partial<Pick<SessionStartResponse, "assistant_message">>,
) {
  const mode = session.mode;
  const meta = GUIDED_STARTERS[mode];
  const messages =
    session.messages && session.messages.length > 0
      ? session.messages
      : session.assistant_message
        ? [{ role: "assistant" as const, content: session.assistant_message }]
        : [{ role: "assistant" as const, content: meta.prompt }];

  return {
    token: session.token,
    mode,
    description:
      mode === "build"
        ? "Você está lapidando uma imagem concreta para a abstração que quer explicar."
        : "Você está descrevendo um problema para receber uma metáfora curta, clara e útil.",
    progressLabel: session.state,
    title: meta.title,
    messages,
    artifacts: session.artifacts ?? [],
    artifactTitle: meta.artifactTitle,
    artifactBody: meta.artifactBody,
    suggestions: SUGGESTIONS_BY_MODE_AND_STATE[mode][session.state] ?? [],
  } satisfies GuidedSessionView;
}

export async function startSession(mode: ChatMode): Promise<SessionStartResponse> {
  return requestJson<SessionStartResponse>("/api/chat/start", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ mode }),
  });
}

export async function getSession(token: string): Promise<SessionResponse> {
  return requestJson<SessionResponse>(`/api/chat/session/${token}`, {
    method: "GET",
  });
}

export async function sendMessage(token: string, content: string): Promise<SendMessageResponse> {
  return requestJson<SendMessageResponse>("/api/chat/message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token, content }),
  });
}

export type ProviderConfig = {
  provider: string;
  model: string;
  groq_models: string[];
  nvidia_models: string[];
};

export async function getProviderConfig(): Promise<ProviderConfig> {
  return requestJson<ProviderConfig>("/api/config", { method: "GET" });
}

export async function setProviderConfig(provider: string, model: string): Promise<{ provider: string; model: string }> {
  return requestJson("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model }),
  });
}
