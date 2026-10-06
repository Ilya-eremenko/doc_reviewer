import React from "react";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ts from "typescript";
import type { NewSummaryContent } from "../../lib/newSummary";
import * as requiredHelpers from "../../lib/newSummaryRequired";

// The project test runner preserves JSX; transpile this leaf renderer to test real HTML, not source strings.
const compiled = ts.transpileModule(readFileSync(new URL("./NewSummaryReport.tsx", import.meta.url), "utf8"), {
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const module = { exports: {} as typeof import("./NewSummaryReport") };
const require = createRequire(import.meta.url);
new Function("require", "exports", compiled)((name: string) => name === "@/lib/newSummaryRequired" ? requiredHelpers : require(name), module.exports);
const { NewSummaryReportView, tractionRowLabel } = module.exports;

const content: NewSummaryContent = {
  schema_version: "new-summary-v4", language: "ru", title: "AI Summary Example", stage: "Progress Review",
  context: "Краткий контекст инициативы.", critical_problems: [],
  traction_summary: { tables: [{ metric: "revenue", metric_label: "Выручка, млн ₽", periods: ["2026", "Total"],
    rows: [{ label: "Итоговый инкрементальный прирост", values: ["10", "10"] }] }] },
  required_elements: [
    { id: "progress_review_plan_fact_last_half_year", label: "План-факт", status: "частично подтверждено", detail: {
      type: "plan_fact", launches: [{ output: "Пилот", status: "partial", comment: "Один регион" }],
      metrics: [{ metric: "Пользователи", planned: "100", actual: "80" }],
    } },
    { id: "gate2_user_flow", label: "Mockups", status: "есть", detail: { type: "source_links", availability: "provided", links: [
      { label: "Прототип", url: "https://example.com/mockup" }, { label: "Unsafe", url: "javascript:alert(1)" },
    ] } },
  ],
};

describe("new-summary-v4 rendering", () => {
  it("renders source metrics in body rows, structured plan-fact and safe source links", () => {
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { embedded: true, report: { analysis_id: "test", ru: content, en: { ...content, language: "en" } } }));
    expect(html).toContain("<th>Output-метрики — uplifts</th>");
    expect(html).toContain("<tbody><tr><th>Выручка, млн ₽</th>");
    expect(html).toContain("План-факт по запускам");
    expect(html).toContain("Пилот — Частично выполнено. Один регион");
    expect(html).toContain("<th>Метрика</th><th>План</th><th>Факт</th>");
    expect(html).toContain('href="https://example.com/mockup"');
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("<h2>Выявленные проблемы</h2>");
    expect(html).not.toContain("<span>Качество документа");
  });

  it("preserves distinguishing labels when a table has multiple source rows", () => {
    const table = { metric_label: "Revenue", periods: ["2026"], rows: [] };
    expect(tractionRowLabel(table, "Scenario A")).toBe("Revenue: Scenario A");
    expect(tractionRowLabel(table, "Incremental Revenue")).toBe("Incremental Revenue");
  });
});
