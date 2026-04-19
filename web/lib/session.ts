import type { ChatMode } from "./api";

export type RecentSession = {
  token: string;
  mode: ChatMode;
  progressLabel: string;
  updatedAt: string;
};

export const NEW_SESSION_TOKEN = "new";
const STORAGE_KEY = "metaphoric-chatbot:recent-sessions";
const MAX_RECENT_SESSIONS = 5;

function getStorage() {
  if (typeof window === "undefined" || typeof window.localStorage !== "object" || window.localStorage === null) {
    return null;
  }

  return window.localStorage;
}

function readStoredSessions(): RecentSession[] {
  const storage = getStorage();
  if (!storage || typeof storage.getItem !== "function") {
    return [];
  }

  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isRecentSession);
  } catch {
    return [];
  }
}

function isRecentSession(value: unknown): value is RecentSession {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<RecentSession>;
  return (
    typeof candidate.token === "string" &&
    (candidate.mode === "receive" || candidate.mode === "build") &&
    typeof candidate.progressLabel === "string" &&
    typeof candidate.updatedAt === "string"
  );
}

function writeStoredSessions(sessions: RecentSession[]) {
  const storage = getStorage();
  if (!storage || typeof storage.setItem !== "function") {
    return;
  }

  storage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function loadRecentSessions() {
  return readStoredSessions();
}

export function loadMostRecentSession() {
  return readStoredSessions()[0] ?? null;
}

export function rememberRecentSession(session: Omit<RecentSession, "updatedAt">) {
  if (session.token === NEW_SESSION_TOKEN) {
    return;
  }

  const nextSession: RecentSession = {
    ...session,
    updatedAt: new Date().toISOString(),
  };

  const current = readStoredSessions().filter((item) => item.token !== session.token);
  writeStoredSessions([nextSession, ...current].slice(0, MAX_RECENT_SESSIONS));
}

export function clearRecentSessions() {
  const storage = getStorage();
  if (!storage) {
    return;
  }

  if (typeof storage.removeItem === "function") {
    storage.removeItem(STORAGE_KEY);
    return;
  }

  if (typeof storage.setItem === "function") {
    storage.setItem(STORAGE_KEY, "[]");
  }
}
