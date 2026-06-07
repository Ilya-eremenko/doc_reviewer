import { apiFetch } from "./client";
import type { Provider } from "./documents";

export type ProviderKeyRecord = {
  provider: Provider;
  base_url: string | null;
  default_model: string;
  api_key_fingerprint: string;
  has_key: boolean;
};

export type ProviderKeysListResponse = {
  provider_keys: ProviderKeyRecord[];
};

export async function listProviderKeys(): Promise<ProviderKeysListResponse> {
  return apiFetch<ProviderKeysListResponse>("/settings/provider-keys");
}

export async function saveProviderKey(
  provider: Provider,
  payload: { api_key: string; base_url?: string | null; default_model: string },
): Promise<ProviderKeyRecord> {
  return apiFetch<ProviderKeyRecord>(`/settings/provider-keys/${provider}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteProviderKey(provider: Provider): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/settings/provider-keys/${provider}`, { method: "DELETE" });
}
