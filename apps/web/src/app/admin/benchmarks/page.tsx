"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { AdminTabs } from "@/components/AdminTabs";
import { AppShell } from "@/components/AppShell";
import { listAdminBenchmarks, type AdminBenchmark, type RunStatus } from "@/lib/api/admin";
import type { Provider } from "@/lib/api/documents";
import { formatDate, formatLabel } from "@/lib/format";

const providers: (Provider | "")[] = ["", "openai_compatible", "anthropic_compatible", "hermes"];
const statuses: (RunStatus | "")[] = ["", "queued", "running", "completed", "failed", "cancelled"];

export default function AdminBenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<AdminBenchmark[]>([]);
  const [provider, setProvider] = useState<Provider | "">("");
  const [status, setStatus] = useState<RunStatus | "">("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await listAdminBenchmarks({ provider, status });
    setBenchmarks(response.benchmarks);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin benchmarks"));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin benchmarks"));
  }

  return (
    <AppShell>
      <main className="main stack">
        <AdminTabs />
        <h1>Admin Benchmarks</h1>
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
            &nbsp;
            <button type="submit">Apply filters</button>
          </label>
        </form>
        {error ? <div className="error">{error}</div> : null}
        <section className="panel table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Started by</th>
                <th>Provider</th>
                <th>Skill</th>
                <th>Status</th>
                <th>Scores</th>
                <th>Completed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.started_by_login}</td>
                  <td>{formatLabel(item.provider)} / {item.model}</td>
                  <td>{item.skill_name} {item.skill_version}</td>
                  <td>{formatLabel(item.status)}</td>
                  <td>{item.overall_score ?? "-"} / {item.layer_1_score ?? "-"} / {item.layer_2_score ?? "-"}</td>
                  <td>{formatDate(item.completed_at)}</td>
                  <td>
                    <Link className="secondary-link" href={`/benchmarks/${item.id}`}>
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
