export interface KeycloakConfig {
  issuer: string;
  clientId: string;
}

const DEFAULT_ISSUER = "https://keycloak.chilik.net/realms/llm-orchestrator";
const DEFAULT_CLIENT_ID = "llm-orchestrator-web";

function envOrDefault(value: string | undefined, fallback: string): string {
  const trimmed = (value ?? "").trim();
  return trimmed || fallback;
}

export function readKeycloakConfig(): KeycloakConfig | null {
  const issuer = envOrDefault(
    import.meta.env.VITE_KEYCLOAK_ISSUER,
    DEFAULT_ISSUER
  ).replace(/\/$/, "");
  const clientId = envOrDefault(
    import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
    DEFAULT_CLIENT_ID
  );
  if (!issuer || !clientId) return null;
  return { issuer, clientId };
}

export function redirectUri(): string {
  return `${window.location.origin}/`;
}
