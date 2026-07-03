import { readAccessToken } from "./session";

export function jsonAuthHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...extra,
  };
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}
