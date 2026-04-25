import type { ConfigRowViewModel } from "./types";
import { apiUrl } from "./apiBase";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const t = await r.text();
    throw new ApiError(t || r.statusText, r.status);
  }
  return r.json() as Promise<T>;
}

type TableDto = { rows: ConfigRowViewModel[]; count: number };

export async function fetchTable(): Promise<TableDto> {
  const r = await fetch(apiUrl("/api/orchestrator/table"), {
    headers: { Accept: "application/json" },
  });
  return readJson<TableDto>(r);
}

export async function createConfig(
  fileName: string,
  text: string
): Promise<TableDto> {
  const r = await fetch(apiUrl("/api/orchestrator/configs"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ fileName, text }),
  });
  return readJson<TableDto>(r);
}

export async function getConfigFileText(
  configId: string
): Promise<{ fileName: string; text: string } | null> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/file-text`)
  );
  if (r.status === 404) return null;
  return readJson<{ fileName: string; text: string }>(r);
}

export async function updateConfigFileText(
  configId: string,
  text: string
): Promise<TableDto> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/file-text`),
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ text }),
    }
  );
  return readJson<TableDto>(r);
}

export async function downloadModel(configId: string): Promise<void> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/actions`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ action: "download" }),
    }
  );
  await readJson<unknown>(r);
}

export async function startModel(configId: string): Promise<void> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/actions`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ action: "start" }),
    }
  );
  await readJson<unknown>(r);
}

export async function stopModel(configId: string): Promise<void> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/actions`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ action: "stop" }),
    }
  );
  await readJson<unknown>(r);
}

export async function deleteModelWeights(configId: string): Promise<void> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/actions`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ action: "delete_model" }),
    }
  );
  await readJson<unknown>(r);
}

export async function deleteConfigFile(configId: string): Promise<void> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/actions`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ action: "delete_config" }),
    }
  );
  await readJson<unknown>(r);
}

export { ApiError };
