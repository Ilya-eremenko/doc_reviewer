import type { NewSummaryLanguage, NewSummaryRequiredElement } from "./newSummary";

export function confirmedFirst<T>(items: T[], status: (item: T) => "confirmed" | "insufficient"): T[] {
  return [...items].sort((a, b) => Number(status(b) === "confirmed") - Number(status(a) === "confirmed"));
}

export function gate2HypothesisSummary(item: NewSummaryRequiredElement, language: NewSummaryLanguage, newFormat = false): string | null {
  const gate2 = item.id === "gate2_hypothesis_results";
  if ((!gate2 && !(newFormat && item.id === "stream_review_1_solution_validation")) || item.detail?.type !== "solution_validation" || !item.detail.items.length) {
    return null;
  }
  const total = item.detail.items.length;
  const confirmed = item.detail.items.filter((entry) => entry.verdict === "confirmed").length;
  const insufficient = total - confirmed;
  if (!newFormat) {
    return language === "ru"
      ? `Результаты проверки гипотез из Gate: ${confirmed} гипотез из ${total} подтверждены, ${insufficient} гипотез из ${total} недостаточно подтверждены.`
      : `Gate hypothesis validation: ${confirmed} of ${total} hypotheses confirmed, ${insufficient} of ${total} insufficiently confirmed.`;
  }
  const noun = (count: number, forms: [string, string, string]) => {
    const lastTwo = count % 100;
    if (lastTwo >= 11 && lastTwo <= 14) return forms[2];
    const last = count % 10;
    return last === 1 ? forms[0] : last >= 2 && last <= 4 ? forms[1] : forms[2];
  };
  if (language === "ru") {
    const forms: [string, string, string] = gate2 ? ["гипотеза", "гипотезы", "гипотез"] : ["проверка", "проверки", "проверок"];
    const heading = gate2 ? "Результаты проверки гипотез из Gate 1" : "Подтвержденные решения";
    return `${heading}: ${confirmed} ${noun(confirmed, forms)} из ${total} ${confirmed === 1 ? "подтверждена" : "подтверждены"}, ${insufficient} ${noun(insufficient, forms)} из ${total} недостаточно ${insufficient === 1 ? "подтверждена" : "подтверждены"}.`;
  }
  const label = gate2 ? "Gate 1 hypothesis validation" : "Solution validation";
  return `${label}: ${confirmed} of ${total} ${gate2 ? "hypotheses" : "checks"} confirmed, ${insufficient} of ${total} insufficiently confirmed.`;
}
