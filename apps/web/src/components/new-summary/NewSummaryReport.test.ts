import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";
import { confirmedFirst, gate2HypothesisSummary } from "../../lib/newSummaryRequired";

const source = readFileSync(new URL("./NewSummaryReport.tsx", import.meta.url), "utf8");

describe("AI Summary required elements", () => {
  it("keeps distinct green, orange, red, and plain fraction presentation", () => {
    expect(source).toContain('partial: "Частично подтверждено"');
    expect(source).toContain('partial: "Partially confirmed"');
    expect(source).toContain('tone === "fraction" ? item.status : text[tone]');
    expect(source).toContain('new-summary-required li.partial .new-summary-required__marker');
    expect(source).toContain('new-summary-required li.fraction .new-summary-required__title .new-summary-required__status');
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
    expect(source).toContain("padding-inline: 0;");
    expect(source).toContain('role="tooltip"');
    expect(source).toContain('.new-summary-help:hover + .new-summary-help__tooltip');
    expect(source).not.toContain('requiredIntro:');
    expect(source).toContain('.new-summary-required > ul > li:first-child { border-top: 0; }');
    expect(source).toContain('<InlineVerdict text={item.text}');
  });

  it("counts Gate 2 hypotheses and separates verdicts while preserving their visual grouping", () => {
    expect(source).toContain("gate2HypothesisSummary(item, language)");
    const item = {
      id: "gate2_hypothesis_results", label: "Результаты проверки гипотез из Gate 1", status: "1/3" as const,
      detail: { type: "solution_validation" as const, items: [
        { text: "Первое", verdict: "insufficient" as const },
        { text: "Второе", verdict: "confirmed" as const },
        { text: "Третье", verdict: "insufficient" as const },
      ] },
    };
    expect(gate2HypothesisSummary(item, "ru")).toBe("Результаты проверки гипотез из Gate: 1 гипотез из 3 подтверждены, 2 гипотез из 3 недостаточно подтверждены.");
    expect(confirmedFirst(item.detail.items, (entry) => entry.verdict).map((entry) => entry.text)).toEqual(["Второе", "Первое", "Третье"]);
    expect(source).toContain("confirmedFirst(detail.items, (item) => item.verdict)");
    expect(source).toContain("margin-left: 3ch;");
    expect(source).toContain(".new-summary-plan-detail > .new-summary-appendix-list + h4");
    expect(source).toContain("margin-top: 12px;");
  });

});
