"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  deleteProviderKey,
  listProviderKeys,
  saveProviderKey,
  testProviderKey,
  type ProviderKeyRecord,
} from "@/lib/api/provider-settings";
import type { Provider } from "@/lib/api/documents";

const providers: Provider[] = ["openai_compatible", "anthropic_compatible", "hermes"];
const defaultOpenAIModels = [
  "anthropic/claude-opus-4.7",
  "anthropic/claude-sonnet-4.6",
  "deepseek/deepseek-v4-pro",
  "google/gemini-3.5-flash",
  "openai/gpt-5.5",
  "qwen/qwen3.5-397b-a17b",
];

function normalizeModelList(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
}

export default function SettingsPage() {
  const [keys, setKeys] = useState<ProviderKeyRecord[]>([]);
  const [provider, setProvider] = useState<Provider>("openai_compatible");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState(defaultOpenAIModels[0]);
  const [modelList, setModelList] = useState(defaultOpenAIModels.join("\n"));
  const [error, setError] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  async function refresh() {
    const response = await listProviderKeys();
    setKeys(response.provider_keys);
  }

  useEffect(() => {
    refresh()
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load provider keys"))
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    setTestMessage("");
    try {
      const availableModels = normalizeModelList(modelList);
      await saveProviderKey(provider, {
        api_key: apiKey,
        base_url: baseUrl || null,
        default_model: model,
        available_models: availableModels,
      });
      setApiKey("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save provider key");
    } finally {
      setPending(false);
    }
  }

  async function remove(providerName: Provider) {
    setPending(true);
    setError("");
    setTestMessage("");
    try {
      await deleteProviderKey(providerName);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete provider key");
    } finally {
      setPending(false);
    }
  }

  async function testKey(providerName: Provider) {
    setPending(true);
    setError("");
    setTestMessage("");
    try {
      const result = await testProviderKey(providerName);
      setTestMessage(`${providerName.replaceAll("_", " ")}: ${result.message}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to test provider key");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <main className="main stack">
        <div className="toolbar">
          <div>
            <h1>Settings</h1>
            <p className="muted">Provider credentials, base URLs, and default models.</p>
          </div>
          <span className="badge info">{keys.length} saved</span>
        </div>
        <form className="panel stack" onSubmit={submit}>
          <div>
            <h2>Provider Key</h2>
            <p className="muted">Saved keys are encrypted and displayed only by fingerprint.</p>
          </div>
          <div className="form-grid">
            <label>
              Provider
              <select value={provider} onChange={(event) => setProvider(event.target.value as Provider)}>
                {providers.map((item) => (
                  <option key={item} value={item}>
                    {item.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              API key
              <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            </label>
            <label>
              Base URL
              <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
            </label>
            <label>
              Default model
              <select value={model} onChange={(event) => setModel(event.target.value)}>
                {normalizeModelList(modelList).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Model allowlist
              <textarea
                rows={6}
                value={modelList}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  setModelList(nextValue);
                  const nextModels = normalizeModelList(nextValue);
                  if (nextModels.length > 0 && !nextModels.includes(model)) {
                    setModel(nextModels[0]);
                  }
                }}
              />
            </label>
          </div>
          {error ? <div className="error">{error}</div> : null}
          {testMessage ? <div className="success">{testMessage}</div> : null}
          <div>
            <button disabled={pending || !apiKey || !model} type="submit">
              {pending ? "Working..." : "Save key"}
            </button>
          </div>
        </form>
        <section className="panel stack">
          <div>
            <h2>Saved Provider Keys</h2>
            <p className="muted">Masked fingerprints and runtime defaults currently available to this account.</p>
          </div>
          {loading ? <div className="muted">Loading provider keys...</div> : null}
          {!loading && keys.length === 0 ? <div className="muted">No provider keys saved.</div> : null}
          {!loading && keys.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Model</th>
                    <th>Allowlist</th>
                    <th>Key</th>
                    <th>Base URL</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((item) => (
                    <tr key={item.provider}>
                      <td>{item.provider.replaceAll("_", " ")}</td>
                      <td>{item.default_model}</td>
                      <td className="small">{item.available_models.join(", ")}</td>
                      <td className="small">{item.api_key_fingerprint}</td>
                      <td>{item.base_url ?? "-"}</td>
                      <td>
                        <span className={item.has_key ? "badge ok" : "badge"}>{item.has_key ? "stored" : "missing"}</span>
                      </td>
                      <td className="button-row">
                        <button className="secondary" disabled={pending} type="button" onClick={() => testKey(item.provider)}>
                          Test
                        </button>
                        <button className="danger" disabled={pending} type="button" onClick={() => remove(item.provider)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </main>
    </AppShell>
  );
}
