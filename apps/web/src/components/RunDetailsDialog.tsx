"use client";

import { useEffect } from "react";

import type { AnalysisRecord } from "@/lib/api/documents";
import { formatDate, formatLabel } from "@/lib/format";

function shortHash(value: string | null | undefined): string {
  if (!value) return "n/a";
  return value.length > 16 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value;
}

function Chip({ label, value }: { label: string; value: string | null | undefined }) {
  return <span className="run-details-chip"><span>{label}</span><strong>{value || "n/a"}</strong></span>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="run-details-metric"><span>{label}</span><strong>{value}</strong></div>;
}

export function RunDetailsDialog({ analysis, onClose }: { analysis: AnalysisRecord; onClose: () => void }) {
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  const trace = analysis.source_trace;
  const parameters = analysis.run_parameters || {};

  return (
    <div className="run-details-backdrop" role="presentation" onClick={onClose}>
      <style>{styles}</style>
      <section aria-labelledby="run-details-title" aria-modal="true" className="run-details-dialog" role="dialog" onClick={(event) => event.stopPropagation()}>
        <header className="run-details-header">
          <div><span>Run metadata</span><h2 id="run-details-title">Run details</h2></div>
          <button type="button" onClick={onClose}>Close</button>
        </header>
        <div className="run-details-chips">
          <Chip label="Provider" value={formatLabel(analysis.provider)} />
          <Chip label="Model" value={analysis.model} />
          <Chip label="Skill" value={`${analysis.skill_name} · ${analysis.skill_version}`} />
          <Chip label="Created" value={formatDate(analysis.created_at)} />
        </div>
        <div className="run-details-metrics">
          <Metric label="Input" value={analysis.input_tokens === null ? "-" : new Intl.NumberFormat("en").format(analysis.input_tokens)} />
          <Metric label="Output" value={analysis.output_tokens === null ? "-" : new Intl.NumberFormat("en").format(analysis.output_tokens)} />
          <Metric label="Latency" value={analysis.latency_ms ? `${analysis.latency_ms} ms` : "-"} />
          <Metric label="Cost" value={analysis.estimated_cost ?? "-"} />
        </div>
        <div className="run-details-trace">
          <strong>Run trace</strong>
          <div className="run-details-chips">
            <Chip label="Source" value={trace?.source_slug} />
            <Chip label="Snapshot" value={shortHash(trace?.source_snapshot_id) !== "n/a" ? shortHash(trace?.source_snapshot_id) : trace?.snapshot_mode} />
            <Chip label="Revision" value={shortHash(trace?.source_revision)} />
            <Chip label="Fingerprint" value={shortHash(trace?.source_fingerprint)} />
            <Chip label="Prompt" value={shortHash(trace?.prompt_fingerprint)} />
            <Chip label="Started" value={formatDate(analysis.started_at)} />
            <Chip label="Completed" value={formatDate(analysis.completed_at)} />
            <Chip label="Params" value={`${Object.keys(parameters).length} keys`} />
          </div>
        </div>
        <details className="run-details-parameters"><summary>Run parameters</summary><pre>{JSON.stringify(parameters, null, 2)}</pre></details>
      </section>
    </div>
  );
}

const styles = `
.run-details-backdrop{position:fixed;z-index:50;inset:0;display:grid;place-items:center;background:rgba(17,24,39,.28);padding:24px}
.run-details-dialog{width:min(920px,100%);max-height:min(760px,calc(100vh - 48px));overflow:auto;display:grid;gap:16px;border:1px solid #d6dee8;border-radius:8px;background:#fff;box-shadow:0 16px 42px rgba(17,24,39,.12);padding:18px;color:#111827}
.run-details-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.run-details-header span,.run-details-chip span,.run-details-metric span{color:#5b6472;font-size:11px;text-transform:uppercase}
.run-details-header h2{margin:4px 0 0;font-size:20px}
.run-details-header button{min-height:36px;border:1px solid #d6dee8;border-radius:6px;background:#fff;padding:0 12px;color:#111827;cursor:pointer}
.run-details-chips{display:flex;flex-wrap:wrap;gap:8px}
.run-details-chip{display:grid;gap:3px;min-width:0;border:1px solid #d6dee8;border-radius:6px;padding:8px 10px;overflow-wrap:anywhere}
.run-details-chip strong,.run-details-metric strong{font-size:13px;color:#111827}
.run-details-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.run-details-metric{display:grid;gap:4px;border:1px solid #d6dee8;border-radius:6px;padding:10px}
.run-details-trace{display:grid;gap:10px;border:1px solid #d6dee8;border-radius:8px;padding:12px}
.run-details-trace>strong{color:#087d5f;font-size:12px;text-transform:uppercase}
.run-details-parameters{border:1px solid #d6dee8;border-radius:6px;padding:10px}
.run-details-parameters summary{cursor:pointer;color:#1d70b8}
.run-details-parameters pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:#fbfcfd;padding:12px;font-size:12px}
@media(max-width:640px){.run-details-backdrop{padding:10px}.run-details-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
`;
