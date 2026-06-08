"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { AdminTabs } from "@/components/AdminTabs";
import { AppShell } from "@/components/AppShell";
import { listAdminAnalyses, type AdminAnalysis, type RunStatus } from "@/lib/api/admin";
import type { Provider } from "@/lib/api/documents";
import { formatDate, formatLabel } from "@/lib/format";

const providers: (Provider | "")[] = ["", "openai_compatible", "anthropic_compatible", "hermes"];
const statuses: (RunStatus | "")[] = ["", "queued", "running", "completed", "failed", "cancelled"];

export default function AdminAnalysesPage() {
  const [analyses, setAnalyses] = useState<AdminAnalysis[]>([]);
  const [provider, setProvider] = useState<Provider | "">("");
  const [status, setStatus] = useState<RunStatus | "">("");
  const [model, setModel] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await listAdminAnalyses({ provider, status, model });
    setAnalyses(response.analyses);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin analyses"));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin analyses"));
  }

  return (
    <AppShell>
      <main className="main stack">
        <AdminTabs />
        <h1>Admin Analyses</h1>
        <form className="panel form-grid" onSubmit={submit}>
          <label>
            Provider
            <select value={provider} onChange={(event) => setProvider(event.target.value as Provider | "")}>
              {providers.map((item) => (
                <option key={item || "all"} value={item}>
                  {item ? formatLabel(item) : "All"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as RunStatus | "")}>
              {statuses.map((item) => (
                <option key={item || "all"} value={item}>
                  {item ? formatLabel(item) : "All"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label>
            &nbsp;
            <button type="submit">Apply filters</button>
          </label>
        </form>
        {error ? <div className="error">{error}</div> : null}
        <section className="panel table-wrap">
          <table>
            <thead>
              <tr>
                <th>Document</th>
                <th>User</th>
                <th>Provider</th>
                <th>Skill</th>
                <th>Status</th>
                <th>Verdict</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((item) => (
                <tr key={item.id}>
                  <td>{item.document_title}</td>
                  <td>{item.user_login}</td>
                  <td>{formatLabel(item.provider)} / {item.model}</td>
                  <td>{item.skill_name} {item.skill_version}</td>
                  <td>{formatLabel(item.status)}</td>
                  <td>{formatLabel(item.verdict)}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>
                    <Link className="secondary-link" href={`/analyses/${item.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </AppShell>
  );
}
