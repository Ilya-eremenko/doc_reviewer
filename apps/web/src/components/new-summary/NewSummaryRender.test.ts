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
      { label: "Прототип", url: "https://example.com/mockup" }, { label: "Design", url: "HTTPS://example.com/design" }, { label: "Unsafe", url: "javascript:alert(1)" },
    ] } },
  ],
};

describe("new-summary-v4 rendering", () => {
  it("renders v7 traction as one four-metric table and marks a mismatched total", () => {
    const updated: NewSummaryContent = { ...content, schema_version: "new-summary-v7", required_elements: [], traction_summary: {
      periods: ["2026", "Total"], rows: [
        { label: "DTB Uplift (Cumul)", values: ["2%", "—"] },
        { label: "Revenue from DTB", values: ["10", "10"] },
        { label: "Revenue non-DTB", values: ["20", "20"] },
        { label: "Total Revenue", values: ["35", "35"], mismatch_periods: ["2026"] },
      ],
    } };
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { report: { analysis_id: "test", ru: updated, en: { ...updated, language: "en" } } }));
    expect(html.match(/<table>/g)).toHaveLength(1);
    expect(html).toContain("<th>DTB Uplift (Cumul)</th>");
    expect(html).toContain("<th>Total Revenue</th>");
    expect(html).toContain('class="new-summary-traction-mismatch"');
    expect(html).toContain("Не равно Rev. from DTB + Rev. non-DTB");
  });

  it("renders v6 metric counts, blue links, additional stops and colored launches", () => {
    const updated: NewSummaryContent = { ...content, schema_version: "new-summary-v6", required_elements: [
      ...content.required_elements,
      { id: "gate2_metric_linkage", label: "Связь метрик.", status: "частично подтверждено", detail: {
        type: "metric_binding", input_metrics: [{ metric: "Конверсия", binding: "confirmed", evidence: "Связана с целью." }],
        output_metrics: [{ metric: "Объем", binding: "insufficient", evidence: "Связь не показана." }],
      } },
      { id: "gate2_stop_criteria", label: "Stop-критерии", status: "есть", evidence: "Основной критерий.", detail: {
        type: "stop_criteria", primary_criterion: "Основной критерий", criteria: ["Дополнительный критерий."],
      } },
      { id: "gate3_stop_criteria", label: "Stop-критерии", status: "есть", detail: { type: "stop_criteria", criteria: [] } },
    ] };
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { embedded: true, report: { analysis_id: "test", ru: updated, en: { ...updated, language: "en" } } }));
    expect(html).toContain('<strong>Связь метрик:</strong><span> связь 1 метрики из 2 подтверждена, связь 1 метрики из 2 недостаточно подтверждена.</span>');
    expect(html).toContain('class="new-summary-source-link" href="https://example.com/mockup"');
    expect(html).toContain('class="new-summary-status-chip launch-partial">Частично выполнено</span>');
    expect(html.match(/<h4>Дополнительные найденные Stop критерии<\/h4>/g)).toHaveLength(1);
    expect(html).not.toContain("Качество документа</span>");
  });

  it("does not invent metric counts for an empty v6 list", () => {
    const updated: NewSummaryContent = { ...content, schema_version: "new-summary-v6", required_elements: [{
      id: "gate2_metric_linkage", label: "Метрики", status: "нет", detail: { type: "metric_binding", input_metrics: [], output_metrics: [] },
    }] };
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { report: { analysis_id: "test", ru: updated, en: updated } }));
    expect(html).not.toContain("0 из 0");
    expect(html).not.toContain('class="new-summary-required__status"');
  });

  it("renders source metrics in body rows, structured plan-fact and safe source links", () => {
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { embedded: true, report: { analysis_id: "test", ru: content, en: { ...content, language: "en" } } }));
    expect(html).toContain("<th>Output-метрики — uplifts</th>");
    expect(html).toContain("<tbody><tr><th>Выручка, млн ₽</th>");
    expect(html).toContain("План-факт по запускам");
    expect(html).toContain("Пилот — Частично выполнено. Один регион");
    expect(html).toContain("<th>Метрика</th><th>План</th><th>Факт</th>");
    expect(html).toContain('href="https://example.com/mockup"');
    expect(html).toContain('href="HTTPS://example.com/design"');
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("<h2>Выявленные проблемы</h2>");
    expect(html).not.toContain("<span>Качество документа");
  });

  it("preserves distinguishing labels when a table has multiple source rows", () => {
    const table = { metric_label: "Revenue", periods: ["2026"], rows: [] };
    expect(tractionRowLabel(table, "Scenario A")).toBe("Revenue: Scenario A");
    expect(tractionRowLabel(table, "Incremental Revenue")).toBe("Incremental Revenue");
  });

  it("renders v5 heading counts unbolded and metric evidence before its verdict", () => {
    const updated: NewSummaryContent = { ...content, schema_version: "new-summary-v5", required_elements: [
      { id: "gate2_hypothesis_results", label: "Hypotheses", status: "1/1", detail: {
        type: "solution_validation", items: [{ text: "Пилот подтвердил спрос.", verdict: "confirmed" }],
      } },
      { id: "stream_review_1_solution_validation", label: "Solutions", status: "1/1", detail: {
        type: "solution_validation", items: [{ text: "Прототип подтвердил решение.", verdict: "confirmed" }],
      } },
      { id: "gate2_metric_linkage", label: "Метрики", status: "есть", detail: {
        type: "metric_binding", input_metrics: [{ metric: "Конверсия", evidence: "Измеряет достижение цели.", binding: "confirmed" }], output_metrics: [],
      } },
    ] };
    const html = renderToStaticMarkup(React.createElement(NewSummaryReportView, { embedded: true, report: { analysis_id: "test", ru: updated, en: { ...updated, language: "en" } } }));
    expect(html).toContain('<strong>Результаты проверки гипотез из Gate 1:</strong><span> 1 гипотеза');
    expect(html).toContain('<strong>Подтверждение решения через количественники, прототипы или фейкдоры:</strong><span> 1 проверка');
    expect(html).toContain('<strong>Конверсия</strong> — Измеряет достижение <span class="new-summary-inline-tail">цели.<span');
    expect(html.indexOf("Измеряет достижение")).toBeLessThan(html.indexOf("Связь подтверждена"));
    expect(html).not.toContain('<p class="new-summary-validation-evidence">');
  });
});
