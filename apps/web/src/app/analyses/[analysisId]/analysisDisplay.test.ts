import { describe, expect, it } from "vitest";

import {
  analysisShortSummary,
  devilsAdvocateRoleComments,
  splitDevilsAdvocateMarkdown,
  stripAssessmentHeading,
} from "./analysisDisplay";

describe("analysis display helpers", () => {
  it("uses the persisted analysis summary before structured fallback fields", () => {
    expect(
      analysisShortSummary({
        summary: "Persisted short summary.",
        structured_output: {
          summary: "Structured short summary.",
          narrative_summary: { executive_summary: "Narrative summary." },
        },
      }),
    ).toBe("Persisted short summary.");
  });

  it("falls back to structured summary fields when persisted summary is absent", () => {
    expect(
      analysisShortSummary({
        summary: null,
        structured_output: {
          narrative_summary: { executive_summary: "Narrative summary." },
        },
      }),
    ).toBe("Narrative summary.");
  });

  it("removes the leading assessment heading from reader-facing markdown", () => {
    expect(stripAssessmentHeading("Оценка документа\n\n**Рекомендация:** запросить доказательства.")).toBe(
      "**Рекомендация:** запросить доказательства.",
    );
  });

  it("leaves non-leading assessment headings intact", () => {
    expect(stripAssessmentHeading("**Рекомендация:** запросить доказательства.\n\n## Оценка документа")).toBe(
      "**Рекомендация:** запросить доказательства.\n\n## Оценка документа",
    );
  });

  it("splits Devil's Advocate markdown into pre-role, role synthesis, and JTBD sections", () => {
    const sections = splitDevilsAdvocateMarkdown(
      "🔴 Devil's Advocate — IC+Gate 3\n\n" +
        "Pre-flight summary\n- Stage: Gate-3\n\n" +
        "---\nThe Brutal Truth\n\nFatal flaw.\n\n" +
        "---\nRole comments / voter synthesis\n\nMP: reject.\nCPO: reject.\n\n" +
        "---\nActionable JTBDs\n\n1. Add a hard KPI gate.\n\n" +
        "=== IC Decision ===\nVerdict: Rework",
    );

    expect(sections).toEqual([
      {
        title: "Before Role comments",
        markdown:
          "🔴 Devil's Advocate — IC+Gate 3\n\nPre-flight summary\n- Stage: Gate-3\n\n---\nThe Brutal Truth\n\nFatal flaw.",
      },
      {
        title: "Role comments / voter synthesis",
        markdown: "Role comments / voter synthesis\n\nMP: reject.\nCPO: reject.",
      },
      {
        title: "Actionable JTBDs",
        markdown: "Actionable JTBDs\n\n1. Add a hard KPI gate.\n\n=== IC Decision ===\nVerdict: Rework",
      },
    ]);
  });

  it("extracts Devil's Advocate voter comments using the original skill comment contract", () => {
    expect(
      devilsAdvocateRoleComments({
        role_comments: [
          {
            voter: "MP",
            vote: "reject",
            rationale: "No incrementality proof.",
            comments: [
              {
                anchor_text: "CR contact to payment",
                body: "What is the baseline and control group?",
                comment_type: "missing_data",
                severity: "critical",
              },
            ],
          },
        ],
      }),
    ).toEqual([
      {
        id: "MP-0",
        voter: "MP",
        vote: "reject",
        anchorText: "CR contact to payment",
        body: "What is the baseline and control group?",
        commentType: "missing_data",
        severity: "critical",
      },
    ]);
  });
});
