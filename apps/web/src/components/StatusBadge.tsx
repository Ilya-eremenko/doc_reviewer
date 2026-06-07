import type { ParseStatus, RunStatus } from "@/lib/api/documents";

const statusClass: Record<string, string> = {
  completed: "badge ok",
  active: "badge ok",
  queued: "badge info",
  running: "badge info",
  failed: "badge danger",
  cancelled: "badge danger",
  unknown: "badge",
};

export function StatusBadge({ status }: { status: ParseStatus | RunStatus | string }) {
  return <span className={statusClass[status] ?? "badge"}>{status.replaceAll("_", " ")}</span>;
}
