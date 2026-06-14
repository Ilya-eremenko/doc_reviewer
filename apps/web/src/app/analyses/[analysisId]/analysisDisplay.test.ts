import { describe, expect, it } from "vitest";

import {
  analysisShortSummary,
  buildDocumentCommentAnchors,
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

  it("matches repeated Devil's Advocate anchors to parsed document text", () => {
    const comments = [
      {
        id: "MP-0",
        voter: "MP",
        vote: "reject",
        anchorText: "CR contact to payment",
        body: "What is the baseline and control group?",
        commentType: "missing_data",
        severity: "critical",
      },
      {
        id: "CPO-0",
        voter: "CPO",
        vote: "reject",
        anchorText: "CR contact to payment",
        body: "Split this by buyer and seller segment.",
        commentType: "scope_gap",
        severity: "high",
      },
      {
        id: "VertDir-0",
        voter: "VertDir",
        vote: "approve",
        anchorText: "buyer trust uplift",
        body: "This direction is plausible.",
        commentType: "supporting_signal",
        severity: "low",
      },
    ];

    expect(
      buildDocumentCommentAnchors(
        "The document says CR contact to payment is below target. Later it cites buyer trust uplift.",
        comments,
      ).anchors,
    ).toEqual([
      {
        id: "anchor-1",
        anchorText: "CR contact to payment",
        commentIds: ["MP-0", "CPO-0"],
        commentCount: 2,
        tone: "bad",
      },
      {
        id: "anchor-2",
        anchorText: "buyer trust uplift",
        commentIds: ["VertDir-0"],
        commentCount: 1,
        tone: "good",
      },
    ]);
  });

  it("keeps comments visible when their anchor is not present in parsed text", () => {
    const comments = [
      {
        id: "MP-0",
        voter: "MP",
        vote: "reject",
        anchorText: "missing exact quote",
        body: "The quote is not in parsed text.",
        commentType: "missing_anchor",
        severity: "high",
      },
    ];

    expect(buildDocumentCommentAnchors("Parsed document text.", comments).unmatchedComments).toEqual(comments);
  });

  it("groups Layer 2 checks under Layer 1 and preserves the PASS/PARTIAL/FAIL status", () => {
    expect(
      buildLayeredGateChecks({
        layer_1_markdown:
          "## Layer 1\n\n" +
          "### Solution quality and logic: FAIL\n" +
          "- id: L1-001\n" +
          "  severity: high\n" +
          "  issue: Solution quality and logic is incomplete.\n" +
          "  evidence: The validation method is not decision-relevant.",
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
            question: "Does each central hypothesis use a validation method that answers the decision question?",
            answer: "PARTIAL",
            issue: "The validation method does not answer the approval decision.",
            evidence: "The document names validation activities but not the decision threshold.",
          },
        ],
      }),
    ).toEqual([
      {
        id: "L1-001",
        title: "Solution Quality and Logic",
        description: "Hypothesis validation, decision logic, and product friction",
        status: "fail",
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
            question: "Does each central hypothesis use a validation method that answers the decision question?",
            answer: "PARTIAL",
            issue: "The validation method does not answer the approval decision.",
            evidence: "The document names validation activities but not the decision threshold.",
          },
        ],
      },
    ]);
  });

  it("keeps markdown-only PASS Layer 1 sections and their Layer 2 clarifying answers visible", () => {
    expect(
      buildLayeredGateChecks({
        layer_1_markdown:
          "## Layer 1\n\n" +
          "### Problem framing and segments: PASS\n" +
          "- No material issue\n\n" +
          "### Solution quality and logic: FAIL\n" +
          "- id: L1_SOL_01\n" +
          "  severity: high\n" +
          "  issue: Payment flow friction.\n" +
          "  evidence: FAQ 2.",
        layer_1: [
          {
            id: "L1_SOL_01",
            severity: "high",
            issue: "Payment flow friction.",
            evidence: "FAQ 2.",
          },
        ],
        layer_2_markdown:
          "## Layer 2\n\n" +
          "### Atomic checks - Problem framing and segments: PASS\n" +
          "- question: Can the reviewer identify the target segment, pain point, and intended behavior change without reconstructing missing logic by inference?\n" +
          "  answer: YES\n" +
          "  evidence: FAQ 1\n\n" +
          "### Atomic checks - Solution quality and logic: FAIL\n" +
          "- question: Does each central hypothesis use a validation method that actually answers the decision question?\n" +
          "  answer: PARTIAL\n" +
          "  evidence: FAQ 2.\n" +
          "  id: L2_SOL_01\n" +
          "  parent_layer_1_id: L1_SOL_01\n" +
          "  status: partial\n" +
          "  severity: high\n" +
          "  title: Payment CJM Friction\n" +
          "  atomic_issue: The pilot's payment flow has high drop-off rates.",
        layer_2: [
          {
            id: "L2_SOL_01",
            parent_layer_1_id: "L1_SOL_01",
            status: "partial",
            severity: "high",
            title: "Payment CJM Friction",
            atomic_issue: "The pilot's payment flow has high drop-off rates.",
            evidence: "FAQ 2.",
          },
        ],
      })[0],
    ).toEqual({
      id: "layer-1-problem-framing-and-segments",
      title: "Problem Framing and Segments",
      description: "Target segment, pain, behavior change, and Gate 1 hypothesis framing",
      status: "pass",
      severity: null,
      issue: "No material issue",
      evidence: null,
      layer2: [
        {
          id: "layer-2-problem-framing-and-segments-1",
          parentLayer1Id: "layer-1-problem-framing-and-segments",
          status: "pass",
          severity: null,
          title:
            "Can the reviewer identify the target segment, pain point, and intended behavior change without reconstructing missing logic by inference?",
          question:
            "Can the reviewer identify the target segment, pain point, and intended behavior change without reconstructing missing logic by inference?",
          answer: "YES",
          issue: "No material issue",
          evidence: "FAQ 1",
        },
      ],
    });
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
          question: "Does each central hypothesis use a validation method that answers the decision question?",
          answer: "NO",
          issue: "Validation is not decision-relevant.",
          evidence: "Missing decision threshold.",
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
          issue: "Validation is weak.",
          answer: "PARTIAL",
          evidence: "The evidence is incomplete.",
        },
        {
          id: "L2-002",
          parent_layer_1_id: "L1-001",
          severity: "high",
          title: "Отсутствие целевого пути пользователя",
          issue: "The end-state path is missing.",
          answer: "NO",
          evidence: "The path is incomplete.",
        },
      ],
    });

    expect(groups[0]?.layer2.map((item) => item.status)).toEqual(["partial", "fail"]);
  });
});
