export interface KeycloakConfig {
  issuer: string;
  clientId: string;
}

const DEFAULT_ISSUER = "https://keycloak.chilik.net/realms/llm-orchestrator";
const DEFAULT_CLIENT_ID = "llm-orchestrator-web";

export function readKeycloakConfig(): KeycloakConfig | null {
  const issuer = (
    import.meta.env.VITE_KEYCLOAK_ISSUER ?? DEFAULT_ISSUER
  ).trim().replace(/\/$/, "");
  const clientId = (
    import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? DEFAULT_CLIENT_ID
  ).trim();
  if (!issuer || !clientId) return null;
  return { issuer, clientId };
}

export function redirectUri(): string {
  return `${window.location.origin}/`;
}
