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

  it("shows new structured details below their required element while retaining old appendices", () => {
    expect(source).toContain("item.detail ? (");
    expect(source).toContain("<RequiredDetailContent detail={item.detail}");
    expect(source).toContain("<RequiredDetailsPanel content={content}");
  });

  it("keeps optional sections and evidence hidden when no content is present", () => {
    expect(source).toContain("{item.evidence ? <p>{item.evidence}</p> : null}");
    expect(source).toContain("{content.critical_problems?.length ? (");
    expect(source).toContain("{content.other?.length ? (");
    expect(source).toContain('detail.type === "hypotheses_with_thresholds"');
    expect(source).toContain("table-layout: fixed;");
  });

  it("shows document quality below the stage and aligns controls with content", () => {
    expect(source).toContain("content.document_quality_percent");
    expect(source).toContain("{text.quality} - {content.document_quality_percent}%");
    expect(source).not.toContain("AI Summary · скилл new-summary");
    expect(source).toContain(".new-summary-quality {");
    expect(source).toContain(".new-summary-toolbar {");
    expect(source).toContain("justify-content: flex-start;");
    expect(source).toContain("padding-inline: 22px;");
  });
});
