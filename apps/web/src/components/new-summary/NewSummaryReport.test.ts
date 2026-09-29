import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./NewSummaryReport.tsx", import.meta.url), "utf8");

describe("AI Summary required elements", () => {
  it("keeps distinct green, orange, red, and plain fraction presentation", () => {
    expect(source).toContain('partial: "Частично подтверждено"');
    expect(source).toContain('partial: "Partially confirmed"');
    expect(source).toContain('tone === "fraction" ? item.status : text[tone]');
    expect(source).toContain('new-summary-required li.partial .new-summary-required__marker');
    expect(source).toContain('new-summary-required li.fraction .new-summary-required__title span');
    expect(source).toContain('background: var(--danger-bg)');
  });
});

describe("AI Summary identified problems", () => {
  it("omits the panel when no confirmed problems exist", () => {
    expect(source).toContain("{content.critical_problems.length ? (");
  });
});

describe("AI Summary traction", () => {
  it("combines only matching Revenue and DTB horizons", () => {
    expect(source).toContain("JSON.stringify(tables[0].periods) !== JSON.stringify(tables[1].periods)");
    expect(source).toContain("tractionTables(traction, text.metric)");
    expect(source).toContain("metric_label: metricHeading");
  });
});
