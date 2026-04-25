/**
 * In dev, Vite proxies `/api` → backend (see vite.config.ts).
 * In prod, nginx (or same host) should reverse-proxy `/api` to the API service, or set absolute URL.
 */
export function getApiBaseUrl(): string {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (v !== undefined && v !== null && String(v).trim() !== "") {
    return String(v).replace(/\/$/, "");
  }
  return "";
}

export function apiUrl(path: string): string {
  const b = getApiBaseUrl();
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!b) return p;
  return `${b}${p}`;
}
