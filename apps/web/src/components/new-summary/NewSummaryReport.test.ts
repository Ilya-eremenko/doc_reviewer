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
