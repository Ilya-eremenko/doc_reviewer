import { describe, expect, it } from "vitest";

import {
  analysisShortSummary,
  buildLayeredGateChecks,
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

  it("groups Layer 2 checks under Layer 1 and preserves the PASS/PARTIAL/FAIL status", () => {
    expect(
      buildLayeredGateChecks({
        layer_1: [
          {
            id: "L1-001",
            severity: "high",
            issue: "Solution quality and logic is incomplete.",
            evidence: "The validation method is not decision-relevant.",
          },
        ],
        layer_2: [
          {
            id: "L2-001",
            parent_layer_1_id: "L1-001",
            status: "partial",
            severity: "medium",
            title: "Does each central hypothesis use a validation method that answers the decision question?",
            atomic_issue: "The validation method does not answer the approval decision.",
            evidence: "The document names validation activities but not the decision threshold.",
            risk: "The committee cannot decide from the stated validation.",
            recommendation: "Tie each hypothesis to a decision threshold.",
          },
        ],
      }),
    ).toEqual([
      {
        id: "L1-001",
        severity: "high",
        issue: "Solution quality and logic is incomplete.",
        evidence: "The validation method is not decision-relevant.",
        layer2: [
          {
            id: "L2-001",
            parentLayer1Id: "L1-001",
            status: "partial",
            severity: "medium",
            title: "Does each central hypothesis use a validation method that answers the decision question?",
            issue: "The validation method does not answer the approval decision.",
            evidence: "The document names validation activities but not the decision threshold.",
            risk: "The committee cannot decide from the stated validation.",
            recommendation: "Tie each hypothesis to a decision threshold.",
          },
        ],
      },
    ]);
  });

  it("normalizes legacy Layer 2 markdown answers when structured status is absent", () => {
    const groups = buildLayeredGateChecks({
      layer_1: [
        {
          id: "L1-001",
          severity: "high",
          issue: "Solution quality and logic is incomplete.",
          evidence: "The validation method is not decision-relevant.",
        },
      ],
      layer_2_markdown:
        "### Atomic checks - Solution quality and logic: FAIL\n\n" +
        "- question: Does each central hypothesis use a validation method that answers the decision question?\n" +
        "  answer: NO\n" +
        "  evidence: Missing decision threshold.\n" +
        "  issue: Validation is not decision-relevant.",
      layer_2: [
        {
          id: "L2-001",
          parent_layer_1_id: "L1-001",
          severity: "high",
          title: "Does each central hypothesis use a validation method that answers the decision question?",
          atomic_issue: "Validation is not decision-relevant.",
          evidence: "Missing decision threshold.",
          risk: "The committee cannot decide.",
          recommendation: "Add decision threshold.",
        },
      ],
    });

    expect(groups[0]?.layer2[0]?.status).toBe("fail");
  });

  it("falls back to the Layer 2 markdown section order when titles are issue labels, not questions", () => {
    const groups = buildLayeredGateChecks({
      layer_1: [
        {
          id: "L1-001",
          severity: "high",
          issue: "Solution quality and logic is incomplete.",
          evidence: "The validation method is not decision-relevant.",
        },
      ],
      layer_2_markdown:
        "### Atomic checks - Solution quality and logic: FAIL\n\n" +
        "- question: Does each central hypothesis use a validation method that answers the decision question?\n" +
        "  answer: PARTIAL\n\n" +
        "- question: Is the end-state path explicit enough to evaluate the claimed scale-up?\n" +
        "  answer: NO",
      layer_2: [
        {
          id: "L2-001",
          parent_layer_1_id: "L1-001",
          severity: "medium",
          title: "Слабая статистическая значимость теста комиссии",
          atomic_issue: "Validation is weak.",
          evidence: "The evidence is incomplete.",
          risk: "The committee cannot decide.",
          recommendation: "Add decision threshold.",
        },
        {
          id: "L2-002",
          parent_layer_1_id: "L1-001",
          severity: "high",
          title: "Отсутствие целевого пути пользователя",
          atomic_issue: "The end-state path is missing.",
          evidence: "The path is incomplete.",
          risk: "The rollout cannot be evaluated.",
          recommendation: "Describe the path.",
        },
      ],
    });

    expect(groups[0]?.layer2.map((item) => item.status)).toEqual(["partial", "fail"]);
  });
});
