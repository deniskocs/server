const ACCESS_TOKEN_KEY = "llm-orchestrator.access_token";

type SessionListener = (token: string | null) => void;

const listeners = new Set<SessionListener>();

export function readAccessToken(): string | null {
  try {
    const t = sessionStorage.getItem(ACCESS_TOKEN_KEY)?.trim();
    if (!t || t === "undefined" || t === "null") return null;
    return t;
  } catch {
    return null;
  }
}

export function persistAccessToken(raw: string): void {
  try {
    const t = raw.trim();
    if (!t) return;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, t);
    notify();
  } catch {
    /* ignore */
  }
}

export function clearAccessToken(): void {
  try {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    notify();
  } catch {
    /* ignore */
  }
}

export function isAuthenticated(): boolean {
  return readAccessToken() != null;
}

export function subscribeSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notify(): void {
  const token = readAccessToken();
  for (const listener of listeners) listener(token);
}
