import type { NewSummaryLanguage, NewSummaryRequiredElement } from "./newSummary";

export function confirmedFirst<T>(items: T[], status: (item: T) => "confirmed" | "insufficient"): T[] {
  return [...items].sort((a, b) => Number(status(b) === "confirmed") - Number(status(a) === "confirmed"));
}

export function gate2HypothesisSummary(item: NewSummaryRequiredElement, language: NewSummaryLanguage): string | null {
  if (item.id !== "gate2_hypothesis_results" || item.detail?.type !== "solution_validation" || !item.detail.items.length) {
    return null;
  }
  const total = item.detail.items.length;
  const confirmed = item.detail.items.filter((entry) => entry.verdict === "confirmed").length;
  const insufficient = total - confirmed;
  return language === "ru"
    ? `Результаты проверки гипотез из Gate: ${confirmed} гипотез из ${total} подтверждены, ${insufficient} гипотез из ${total} недостаточно подтверждены.`
    : `Gate hypothesis validation: ${confirmed} of ${total} hypotheses confirmed, ${insufficient} of ${total} insufficiently confirmed.`;
}
