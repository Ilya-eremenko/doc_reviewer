"use client";

import { FormEvent, useEffect, useState } from "react";

import { AdminTabs } from "@/components/AdminTabs";
import { AppShell } from "@/components/AppShell";
import { listAdminFeedback, markAdminFeedbackProcessed, type AdminFeedback } from "@/lib/api/admin";
import { formatDate, formatLabel } from "@/lib/format";

export default function AdminFeedbackPage() {
  const [feedback, setFeedback] = useState<AdminFeedback[]>([]);
  const [model, setModel] = useState("");
  const [verdict, setVerdict] = useState("");
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await listAdminFeedback({ model, verdict });
    setFeedback(response.feedback);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin feedback"));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin feedback"));
  }

  async function markProcessed(feedbackId: string) {
    setPending(feedbackId);
    setError("");
    try {
      await markAdminFeedbackProcessed(feedbackId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark feedback processed");
    } finally {
      setPending("");
    }
  }

  return (
    <AppShell>
      <main className="main stack">
        <AdminTabs />
        <h1>Admin Feedback</h1>
        <form className="panel form-grid" onSubmit={submit}>
          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label>
            Verdict
            <input value={verdict} onChange={(event) => setVerdict(event.target.value)} />
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
                <th>User</th>
                <th>Document</th>
                <th>Provider</th>
                <th>Usefulness</th>
                <th>Verdict</th>
                <th>Comment</th>
                <th>Processed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {feedback.map((item) => (
                <tr key={item.id}>
                  <td>{item.user_login}</td>
                  <td>{item.document_title}</td>
                  <td>{formatLabel(item.provider)} / {item.model}</td>
                  <td>{formatLabel(item.usefulness)}</td>
                  <td>{formatLabel(item.analysis_verdict)}</td>
                  <td>{item.comment ?? "-"}</td>
                  <td>{formatDate(item.processed_at)}</td>
                  <td>
                    <button
                      className="secondary"
                      disabled={Boolean(item.processed_at) || pending === item.id}
                      type="button"
                      onClick={() => markProcessed(item.id)}
                    >
                      Mark processed
                    </button>
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
