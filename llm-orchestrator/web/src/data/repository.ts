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

type ModelsDto = { rows: ConfigRowViewModel[]; count: number };

export async function fetchModels(): Promise<ModelsDto> {
  const r = await fetch(apiUrl("/api/orchestrator/models"), {
    headers: { Accept: "application/json" },
  });
  return readJson<ModelsDto>(r);
}

export async function createConfig(
  fileName: string,
  text: string
): Promise<ModelsDto> {
  const r = await fetch(apiUrl("/api/orchestrator/configs"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ fileName, text }),
  });
  return readJson<ModelsDto>(r);
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
): Promise<ModelsDto> {
  const r = await fetch(
    apiUrl(`/api/orchestrator/configs/${encodeURIComponent(configId)}/file-text`),
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ text }),
    }
  );
  return readJson<ModelsDto>(r);
}

type ModelsAction =
  | "download"
  | "start"
  | "stop"
  | "delete_model"
  | "delete_config";

async function postModelsAction(
  configFile: string,
  action: ModelsAction
): Promise<void> {
  const r = await fetch(apiUrl("/api/orchestrator/models/actions"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ action, configFile }),
  });
  await readJson<unknown>(r);
}

export async function downloadModel(configFile: string): Promise<void> {
  return postModelsAction(configFile, "download");
}

export async function startModel(configFile: string): Promise<void> {
  return postModelsAction(configFile, "start");
}

export async function stopModel(configFile: string): Promise<void> {
  return postModelsAction(configFile, "stop");
}

export async function deleteModelWeights(configFile: string): Promise<void> {
  return postModelsAction(configFile, "delete_model");
}

export async function deleteConfigFile(configFile: string): Promise<void> {
  return postModelsAction(configFile, "delete_config");
}

export { ApiError };
