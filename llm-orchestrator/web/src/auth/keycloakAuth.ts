import { createPkcePair, randomOAuthState } from "./pkce";
import {
  clearAccessToken,
  persistAccessToken,
  readAccessToken,
} from "./session";
import { readKeycloakConfig, redirectUri, type KeycloakConfig } from "./keycloakConfig";

const PKCE_VERIFIER_KEY = "llm-orchestrator.oauth.pkce_verifier";
const OAUTH_STATE_KEY = "llm-orchestrator.oauth.state";

type TokenResponse = {
  access_token?: string;
  refresh_token?: string;
  id_token?: string;
  token_type?: string;
  expires_in?: number;
  error?: string;
  error_description?: string;
};

export class KeycloakAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "KeycloakAuthError";
  }
}

function requireConfig(): KeycloakConfig {
  const cfg = readKeycloakConfig();
  if (!cfg) {
    throw new KeycloakAuthError("Keycloak is not configured");
  }
  return cfg;
}

function authEndpoint(issuer: string): string {
  return `${issuer}/protocol/openid-connect/auth`;
}

function tokenEndpoint(issuer: string): string {
  return `${issuer}/protocol/openid-connect/token`;
}

function clearOAuthTransient(): void {
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
}

function stripOAuthQueryFromUrl(): void {
  const url = new URL(window.location.href);
  url.searchParams.delete("code");
  url.searchParams.delete("state");
  url.searchParams.delete("session_state");
  url.searchParams.delete("iss");
  url.searchParams.delete("error");
  url.searchParams.delete("error_description");
  const next = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState({}, "", next || "/");
}

export async function startKeycloakLogin(): Promise<void> {
  const cfg = requireConfig();
  const { verifier, challenge } = await createPkcePair();
  const state = randomOAuthState();
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(OAUTH_STATE_KEY, state);

  const url = new URL(authEndpoint(cfg.issuer));
  url.searchParams.set("client_id", cfg.clientId);
  url.searchParams.set("redirect_uri", redirectUri());
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", "openid profile email");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");

  window.location.assign(url.toString());
}

async function exchangeCodeForToken(code: string, verifier: string): Promise<string> {
  const cfg = requireConfig();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: cfg.clientId,
    code,
    redirect_uri: redirectUri(),
    code_verifier: verifier,
  });

  const res = await fetch(tokenEndpoint(cfg.issuer), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const json = (await res.json()) as TokenResponse;
  if (!res.ok) {
    throw new KeycloakAuthError(
      json.error_description ?? json.error ?? `Token exchange failed (${res.status})`
    );
  }
  const token = json.access_token?.trim();
  if (!token) {
    throw new KeycloakAuthError("Keycloak did not return an access token");
  }
  return token;
}

/** Returns true when an OAuth callback was handled (success or error). */
export async function tryCompleteLoginFromUrl(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");
  if (error) {
    const desc = params.get("error_description") ?? error;
    stripOAuthQueryFromUrl();
    clearOAuthTransient();
    throw new KeycloakAuthError(desc);
  }

  const code = params.get("code");
  if (!code) return false;

  const state = params.get("state");
  const savedState = sessionStorage.getItem(OAUTH_STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!state || !savedState || state !== savedState || !verifier) {
    stripOAuthQueryFromUrl();
    clearOAuthTransient();
    throw new KeycloakAuthError("Invalid OAuth state — try logging in again");
  }

  try {
    const token = await exchangeCodeForToken(code, verifier);
    persistAccessToken(token);
  } finally {
    stripOAuthQueryFromUrl();
    clearOAuthTransient();
  }
  return true;
}

export function logoutLocally(): void {
  clearAccessToken();
}

export function readSessionLabel(): string | null {
  const token = readAccessToken();
  if (!token) return null;
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const json = JSON.parse(
      atob(part.replace(/-/g, "+").replace(/_/g, "/"))
    ) as { preferred_username?: string; email?: string; name?: string };
    return json.preferred_username ?? json.email ?? json.name ?? null;
  } catch {
    return null;
  }
}
