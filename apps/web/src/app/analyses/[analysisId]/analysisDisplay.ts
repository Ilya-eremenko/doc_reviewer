import type { AnalysisRecord } from "@/lib/api/documents";

type SummarySource = Pick<AnalysisRecord, "summary" | "structured_output">;

const ASSESSMENT_HEADINGS = new Set(["Оценка документа", "Document assessment"]);

export type DevilsAdvocateMarkdownSection = {
  title: string;
  markdown: string;
};

export type DevilsAdvocateRoleComment = {
  id: string;
  voter: string;
  vote: string | null;
  anchorText: string;
  body: string;
  commentType: string | null;
  severity: string | null;
};

export function analysisShortSummary(analysis: SummarySource): string | null {
  return analysis.summary || summaryFromOutput(analysis.structured_output);
}

export function stripAssessmentHeading(markdown: string | null): string | null {
  const value = asString(markdown);
  if (!value) {
    return null;
  }

  const trimmedStart = value.trimStart();
  const lines = trimmedStart.split(/\r?\n/);
  const firstLine = lines[0]?.trim().replace(/^#{1,6}\s+/, "").trim();
  if (!ASSESSMENT_HEADINGS.has(firstLine)) {
    return value;
  }

  return asString(lines.slice(1).join("\n").trimStart());
}

export function splitDevilsAdvocateMarkdown(markdown: string | null): DevilsAdvocateMarkdownSection[] {
  const value = asString(markdown);
  if (!value) {
    return [];
  }

  const lines = value.replace(/\r\n/g, "\n").split("\n");
  const roleStart = findHeadingLine(lines, isRoleCommentsHeading);
  const jtbdStart = findHeadingLine(lines, isActionableJtbdHeading);
  const hasRoleSection = roleStart >= 0 && (jtbdStart < 0 || roleStart < jtbdStart);

  if (!hasRoleSection && jtbdStart < 0) {
    return [{ title: "Devil's Advocate output", markdown: value.trim() }];
  }

  const sections: DevilsAdvocateMarkdownSection[] = [];
  const firstEnd = hasRoleSection ? roleStart : jtbdStart;
  pushMarkdownSection(sections, "Before Role comments", lines.slice(0, firstEnd));

  if (hasRoleSection) {
    const roleEnd = jtbdStart > roleStart ? jtbdStart : lines.length;
    pushMarkdownSection(sections, "Role comments / voter synthesis", lines.slice(roleStart, roleEnd));
  }

  if (jtbdStart >= 0) {
    pushMarkdownSection(sections, "Actionable JTBDs", lines.slice(jtbdStart));
  }

  return sections.length ? sections : [{ title: "Devil's Advocate output", markdown: value.trim() }];
}

export function devilsAdvocateRoleComments(
  output: Record<string, unknown> | null | undefined,
): DevilsAdvocateRoleComment[] {
  return asRecordArray(output?.role_comments).flatMap((roleRecord) => {
    const voter = asString(roleRecord.voter) || "Unknown";
    const vote = asString(roleRecord.vote);
    return asRecordArray(roleRecord.comments).flatMap((commentRecord, index) => {
      const anchorText = asString(commentRecord.anchor_text) || asString(commentRecord.anchor);
      const body = asString(commentRecord.body) || asString(commentRecord.comment);
      if (!anchorText || !body) {
        return [];
      }

      return [
        {
          id: `${voter}-${index}`,
          voter,
          vote,
          anchorText,
          body,
          commentType: asString(commentRecord.comment_type),
          severity: asString(commentRecord.severity),
        },
      ];
    });
  });
}

function summaryFromOutput(output: Record<string, unknown> | null | undefined): string | null {
  const narrative = asRecord(output?.narrative_summary);
  return (
    asString(output?.summary) ||
    asString(narrative?.summary) ||
    asString(narrative?.executive_summary) ||
    asString(narrative?.assessment) ||
    null
  );
}

function findHeadingLine(lines: string[], predicate: (heading: string) => boolean): number {
  return lines.findIndex((line) => predicate(normalizeMarkdownHeading(line)));
}

function normalizeMarkdownHeading(line: string): string {
  return line
    .trim()
    .replace(/^#{1,6}\s+/, "")
    .replace(/^\d+[.)]\s+/, "")
    .replace(/\*\*/g, "")
    .replace(/:$/, "")
    .trim()
    .toLowerCase();
}

function isRoleCommentsHeading(heading: string): boolean {
  return heading.startsWith("role comments") || (heading.includes("role comments") && heading.includes("voter synthesis"));
}

function isActionableJtbdHeading(heading: string): boolean {
  return heading.startsWith("actionable jtbd");
}

function pushMarkdownSection(sections: DevilsAdvocateMarkdownSection[], title: string, lines: string[]) {
  const markdown = cleanMarkdownSection(lines);
  if (markdown) {
    sections.push({ title, markdown });
  }
}

function cleanMarkdownSection(lines: string[]): string | null {
  const sectionLines = [...lines];
  while (sectionLines.length && isTrimmedBoundary(sectionLines[0])) {
    sectionLines.shift();
  }
  while (sectionLines.length && isTrimmedBoundary(sectionLines[sectionLines.length - 1])) {
    sectionLines.pop();
  }
  return asString(sectionLines.join("\n"));
}

function isTrimmedBoundary(line: string): boolean {
  const trimmed = line.trim();
  return !trimmed || /^(?:-{3,}|\*{3,}|_{3,})$/.test(trimmed);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asRecordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord).filter((record): record is Record<string, unknown> => Boolean(record)) : [];
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}
