"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { getAnalysis, type AnalysisRecord } from "@/lib/api/documents";
import { submitFeedback } from "@/lib/api/feedback";
import { formatDate, formatLabel } from "@/lib/format";

export default function AnalysisDetailPage() {
  const params = useParams<{ analysisId: string }>();
  const [analysis, setAnalysis] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [usefulness, setUsefulness] = useState<"useful" | "partially_useful" | "useless">("useful");
  const [canUseForBenchmark, setCanUseForBenchmark] = useState(false);

  useEffect(() => {
    getAnalysis(params.analysisId)
      .then(setAnalysis)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load analysis"));
  }, [params.analysisId]);

  async function sendFeedback() {
    if (!analysis) {
      return;
    }
    setFeedbackStatus("");
    setError("");
    try {
      await submitFeedback(analysis.id, {
        usefulness,
        verdict_correct: null,
        has_false_findings: null,
        has_missed_findings: null,
        comment: feedbackComment || null,
        can_use_for_benchmark: canUseForBenchmark,
      });
      setFeedbackStatus("Feedback saved");
      setFeedbackComment("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    }
  }

  return (
    <AppShell>
      <main className="main stack">
        {error ? <section className="panel error">{error}</section> : null}
        {analysis ? (
          <>
            <section className="panel stack">
              <div className="toolbar">
                <div>
                  <h1>Analysis</h1>
                  <p className="muted">
                    {analysis.skill_name} · {analysis.provider} · {analysis.model}
                  </p>
                </div>
                <StatusBadge status={analysis.status} />
              </div>
              <div className="meta-grid">
                <div>
                  <div className="muted small">Verdict</div>
                  <strong>{formatLabel(analysis.verdict)}</strong>
                </div>
                <div>
                  <div className="muted small">Created</div>
                  <strong>{formatDate(analysis.created_at)}</strong>
                </div>
                <div>
                  <div className="muted small">Skill version</div>
                  <strong>{analysis.skill_version}</strong>
                </div>
              </div>
              {analysis.summary ? <p>{analysis.summary}</p> : null}
              {analysis.error_message ? <div className="error">{analysis.error_message}</div> : null}
            </section>
            <section className="panel stack">
              <h2>Structured Output</h2>
              <pre className="text-preview">{JSON.stringify(analysis.structured_output ?? {}, null, 2)}</pre>
            </section>
            {analysis.raw_output ? (
              <section className="panel stack">
                <h2>Raw Output</h2>
                <pre className="text-preview">{analysis.raw_output}</pre>
              </section>
            ) : null}
            <section className="panel stack">
              <h2>Feedback</h2>
              <div className="form-grid">
                <label>
                  Usefulness
                  <select value={usefulness} onChange={(event) => setUsefulness(event.target.value as typeof usefulness)}>
                    <option value="useful">Useful</option>
                    <option value="partially_useful">Partially useful</option>
                    <option value="useless">Useless</option>
                  </select>
                </label>
                <label className="checkbox-label">
                  <input
                    checked={canUseForBenchmark}
                    type="checkbox"
                    onChange={(event) => setCanUseForBenchmark(event.target.checked)}
                  />
                  Use for benchmark review
                </label>
              </div>
              <label>
                Comment
                <textarea value={feedbackComment} onChange={(event) => setFeedbackComment(event.target.value)} />
              </label>
              <div className="button-row">
                <button type="button" onClick={sendFeedback}>
                  Submit feedback
                </button>
                {feedbackStatus ? <span className="muted">{feedbackStatus}</span> : null}
              </div>
            </section>
          </>
        ) : (
          <section className="panel muted">Loading...</section>
        )}
      </main>
    </AppShell>
  );
}
