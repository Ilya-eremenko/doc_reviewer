import type { AnalysisRecord } from "@/lib/api/documents";

type SummarySource = Pick<AnalysisRecord, "summary" | "structured_output">;
type GateDetailsSource = Pick<AnalysisRecord, "structured_output" | "detail_run">;

const ASSESSMENT_HEADINGS = new Set(["Оценка документа", "Document assessment"]);
const NO_MATERIAL_ISSUE = "No material issue";

const GATE_LAYER_METADATA = new Map(
  [
    {
      key: "problem framing and segments",
      title: "Problem Framing and Segments",
      description: "Target segment, pain, behavior change, and Gate 1 hypothesis framing",
      layer2Title: "Problem Framing and Significance: Were the Gate 1 Hypotheses Confirmed?",
    },
    {
      key: "solution quality and logic",
      title: "Solution Quality and Logic",
      description: "Hypothesis validation, decision logic, and product friction",
      layer2Title: "Solution Quality and Logic",
    },
    {
      key: "scope of work and implementation plan",
      title: "Scope of Work and Implementation Plan",
      description: "Rollout sequencing, operational constraints, legal and compliance readiness",
      layer2Title: "Scope of Work and Implementation Plan",
    },
    {
      key: "success criteria and metrics",
      title: "Success Criteria and Metrics",
      description: "Thresholds, measured results, and decision-grade metric evidence",
      layer2Title: "Success Criteria and Metrics",
    },
    {
      key: "traction model credibility",
      title: "Traction Model Credibility",
      description: "Adoption model, subsidies, organic demand, and unit economics",
      layer2Title: "Traction Model Credibility",
    },
    {
      key: "key assumptions and risks completeness",
      title: "Key Assumptions and Risks Completeness",
      description: "Scenario failure conditions, risks, and reversal logic",
      layer2Title: "Key Assumptions and Risks Completeness",
    },
    {
      key: "consistency",
      title: "Consistency",
      description: "Internal contradiction checks across targets, resources, and conclusions",
      layer2Title: "Consistency",
    },
  ].map((item) => [item.key, item]),
);

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

export type DocumentCommentTone = "good" | "warn" | "bad" | "neutral";

export type DocumentCommentAnchor = {
  id: string;
  anchorText: string;
  commentIds: string[];
  commentCount: number;
  tone: DocumentCommentTone;
};

export type DocumentCommentSegment = {
  id: string;
  text: string;
  anchorId: string | null;
  commentCount: number;
  tone: DocumentCommentTone;
};

export type DocumentCommentAnchors = {
  anchors: DocumentCommentAnchor[];
  segments: DocumentCommentSegment[];
  unmatchedComments: DevilsAdvocateRoleComment[];
};

export type LayeredGateCheck = {
  id: string;
  title: string;
  description: string | null;
  status: string | null;
  severity: string | null;
  issue: string;
  evidence: string | null;
  layer2: LayeredGateLayer2Check[];
};

export type LayeredGateLayer2Check = {
  id: string;
  parentLayer1Id: string;
  status: string | null;
  severity: string | null;
  title: string;
  question: string;
  answer: string | null;
  issue: string;
  evidence: string | null;
};

export function analysisShortSummary(analysis: SummarySource): string | null {
  return analysis.summary || summaryFromOutput(analysis.structured_output);
}

export function analysisGateDetailsOutput(
  analysis: GateDetailsSource,
): Record<string, unknown> | null | undefined {
  if (analysis.detail_run?.status === "completed" && analysis.detail_run.structured_output) {
    return analysis.detail_run.structured_output;
  }
  return analysis.structured_output;
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

export function buildDocumentCommentAnchors(
  documentText: string | null | undefined,
  comments: DevilsAdvocateRoleComment[],
): DocumentCommentAnchors {
  const text = documentText || "";
  const groupedAnchors = new Map<string, { anchorText: string; comments: DevilsAdvocateRoleComment[] }>();
  for (const comment of comments) {
    const key = normalizeAnchorText(comment.anchorText);
    if (!key) {
      continue;
    }
    const group = groupedAnchors.get(key) || { anchorText: comment.anchorText, comments: [] };
    group.comments.push(comment);
    groupedAnchors.set(key, group);
  }

  const matchedGroups = Array.from(groupedAnchors.values())
    .map((group) => ({ ...group, match: findAnchorMatch(text, group.anchorText) }))
    .filter((group): group is { anchorText: string; comments: DevilsAdvocateRoleComment[]; match: AnchorMatch } =>
      Boolean(group.match),
    )
    .sort((left, right) => left.match.start - right.match.start);

  const anchors: DocumentCommentAnchor[] = [];
  const segments: DocumentCommentSegment[] = [];
  let cursor = 0;
  for (const group of matchedGroups) {
    if (group.match.start < cursor) {
      continue;
    }

    if (group.match.start > cursor) {
      segments.push({
        id: `text-${segments.length + 1}`,
        text: text.slice(cursor, group.match.start),
        anchorId: null,
        commentCount: 0,
        tone: "neutral",
      });
    }

    const id = `anchor-${anchors.length + 1}`;
    const tone = toneForComments(group.comments);
    anchors.push({
      id,
      anchorText: group.anchorText,
      commentIds: group.comments.map((comment) => comment.id),
      commentCount: group.comments.length,
      tone,
    });
    segments.push({
      id: `segment-${id}`,
      text: text.slice(group.match.start, group.match.end),
      anchorId: id,
      commentCount: group.comments.length,
      tone,
    });
    cursor = group.match.end;
  }

  if (cursor < text.length || !segments.length) {
    segments.push({
      id: `text-${segments.length + 1}`,
      text: text.slice(cursor),
      anchorId: null,
      commentCount: 0,
      tone: "neutral",
    });
  }

  const matchedCommentIds = new Set(anchors.flatMap((anchor) => anchor.commentIds));
  return {
    anchors,
    segments,
    unmatchedComments: comments.filter((comment) => !matchedCommentIds.has(comment.id)),
  };
}

export function buildLayeredGateChecks(output: Record<string, unknown> | null | undefined): LayeredGateCheck[] {
  const layer1Sections = parseLayer1MarkdownSections(asString(output?.layer_1_markdown));
  const layer2Sections = parseLayer2MarkdownSections(asString(output?.layer_2_markdown));
  const layer1Records = asRecordArray(output?.layer_1);
  const layer1RecordsById = new Map(
    layer1Records.map((record, index) => [asString(record.id) || `L1-${index + 1}`, record]),
  );
  const consumedLayer1Ids = new Set<string>();
  const layer1: LayeredGateCheck[] = layer1Sections.map((section, index) => {
    const structured = section.id ? layer1RecordsById.get(section.id) : null;
    const id = (structured && asString(structured.id)) || section.id || syntheticId("layer-1", section.key);
    consumedLayer1Ids.add(id);
    return layer1GroupFromSources({
      id,
      key: section.key,
      structured,
      section,
      fallbackIndex: index + 1,
    });
  });

  for (const [index, record] of layer1Records.entries()) {
    const id = asString(record.id) || `L1-${index + 1}`;
    if (consumedLayer1Ids.has(id)) {
      continue;
    }
    const issue = asString(record.issue);
    const evidence = asString(record.evidence);
    if (!issue || !evidence) {
      continue;
    }
    layer1.push(
      layer1GroupFromSources({
        id,
        key: normalizeLayerKey(asString(record.dimension) || asString(record.title) || issue),
        structured: record,
        section: null,
        fallbackIndex: index + 1,
      }),
    );
  }

  if (!layer1.length) {
    return [];
  }

  const groupsById = new Map(layer1.map((group) => [group.id, group]));
  const groupsByKey = new Map(layer1.map((group) => [normalizeLayerKey(group.title), group]));
  const groupIndexById = new Map(layer1.map((group, index) => [group.id, index]));
  const sectionByKey = new Map(layer2Sections.map((section) => [section.key, section]));
  const markdownQuestionsById = new Map<string, ParsedLayer2Question>();
  for (const section of layer2Sections) {
    for (const question of section.questions) {
      if (question.id) {
        markdownQuestionsById.set(question.id, question);
      }
    }
  }

  const consumedMarkdownQuestions = new Set<ParsedLayer2Question>();
  for (const [index, record] of asRecordArray(output?.layer_2).entries()) {
    const parentLayer1Id = asString(record.parent_layer_1_id);
    if (!parentLayer1Id) {
      continue;
    }
    const group = groupsById.get(parentLayer1Id);
    if (!group) {
      continue;
    }

    const groupIndex = groupIndexById.get(group.id) ?? -1;
    const section = sectionByKey.get(normalizeLayerKey(group.title)) || layer2Sections[groupIndex];
    const childIndex = group.layer2.length;
    const markdownQuestion =
      markdownQuestionsById.get(asString(record.id) || "") ||
      section?.questions.find((question) => question.parentLayer1Id === parentLayer1Id && !consumedMarkdownQuestions.has(question)) ||
      section?.questions[childIndex] ||
      null;
    if (markdownQuestion) {
      consumedMarkdownQuestions.add(markdownQuestion);
    }
    group.layer2.push(layer2CheckFromSources(record, index, group, markdownQuestion, section));
  }

  for (const section of layer2Sections) {
    const group = groupsByKey.get(section.key);
    if (!group) {
      continue;
    }
    for (const [index, question] of section.questions.entries()) {
      if (consumedMarkdownQuestions.has(question)) {
        continue;
      }
      consumedMarkdownQuestions.add(question);
      group.layer2.push(layer2CheckFromMarkdown(section, question, group, index));
    }
  }

  return layer1;
}

function layer1GroupFromSources({
  id,
  key,
  structured,
  section,
  fallbackIndex,
}: {
  id: string;
  key: string;
  structured: Record<string, unknown> | null | undefined;
  section: ParsedLayer1Section | null;
  fallbackIndex: number;
}): LayeredGateCheck {
  const metadata = GATE_LAYER_METADATA.get(key);
  const title = metadata?.title || section?.title || toTitleCase(asString(structured?.title) || `Layer 1 ${fallbackIndex}`);
  const issue = asString(structured?.issue) || section?.issue || NO_MATERIAL_ISSUE;
  return {
    id,
    title,
    description: metadata?.description || null,
    status: section?.status || null,
    severity: asString(structured?.severity) || section?.severity || null,
    issue,
    evidence: asString(structured?.evidence) || section?.evidence || null,
    layer2: [],
  };
}

function layer2CheckFromSources(
  record: Record<string, unknown>,
  index: number,
  group: LayeredGateCheck,
  markdownQuestion: ParsedLayer2Question | null,
  section: ParsedLayer2Section | null | undefined,
): LayeredGateLayer2Check {
  const structuredQuestion = asString(record.question) || asString(record.title) || asString(record.check);
  const markdownQuestionText = markdownQuestion?.question || markdownQuestion?.title || null;
  const question =
    markdownQuestion?.source === "field"
      ? markdownQuestionText || structuredQuestion || GATE_LAYER_METADATA.get(normalizeLayerKey(group.title))?.layer2Title || `Layer 2 check ${index + 1}`
      : structuredQuestion || markdownQuestionText || GATE_LAYER_METADATA.get(normalizeLayerKey(group.title))?.layer2Title || `Layer 2 check ${index + 1}`;
  const shorthandIssue = markdownQuestion?.source === "shorthand" ? markdownQuestion.question : null;
  const status = normalizeCheckStatus(record.status) || markdownQuestion?.status || section?.status || null;
  const issue =
    markdownQuestion?.issue ||
    asString(record.issue) ||
    asString(record.atomic_issue) ||
    asString(record.finding) ||
    markdownQuestion?.atomicIssue ||
    shorthandIssue ||
    (status === "pass" ? NO_MATERIAL_ISSUE : question);
  const evidence = asString(record.evidence) || asString(record.explanation) || markdownQuestion?.evidence;
  return {
    id: asString(record.id) || markdownQuestion?.id || `L2-${index + 1}`,
    parentLayer1Id: group.id,
    status,
    severity: asString(record.severity) || markdownQuestion?.severity || null,
    title: question,
    question,
    answer: markdownQuestion?.answer || asString(record.answer) || answerForStatus(status),
    issue,
    evidence: evidence || null,
  };
}

function layer2CheckFromMarkdown(
  section: ParsedLayer2Section,
  question: ParsedLayer2Question,
  group: LayeredGateCheck,
  index: number,
): LayeredGateLayer2Check {
  const id = question.id || syntheticId("layer-2", `${section.key}-${index + 1}`);
  const title = question.question || question.title || GATE_LAYER_METADATA.get(section.key)?.layer2Title || section.title;
  return {
    id,
    parentLayer1Id: group.id,
    status: question.status || section.status,
    severity: question.severity || null,
    title,
    question: title,
    answer: question.answer || answerForStatus(question.status || section.status),
    issue: question.atomicIssue || question.issue || (section.status === "pass" ? NO_MATERIAL_ISSUE : question.question),
    evidence: question.evidence || null,
  };
}

type ParsedLayer1Section = {
  key: string;
  title: string;
  status: string | null;
  id: string | null;
  severity: string | null;
  issue: string | null;
  evidence: string | null;
};

type ParsedLayer2Section = {
  key: string;
  title: string;
  status: string | null;
  questions: ParsedLayer2Question[];
};

type ParsedLayer2Question = {
  id: string | null;
  parentLayer1Id: string | null;
  status: string | null;
  severity: string | null;
  title: string | null;
  atomicIssue: string | null;
  question: string;
  answer: string | null;
  evidence: string | null;
  issue: string | null;
  source: "field" | "shorthand";
};

function parseLayer1MarkdownSections(markdown: string | null): ParsedLayer1Section[] {
  return splitLayerMarkdownSections(markdown, false).map((section) => {
    const fields = parseMarkdownFields(section.lines);
    const shorthand = parseLayerShorthandBullet(section.lines, "L1");
    const noMaterialIssue = findNoMaterialIssue(section.lines);
    return {
      key: section.key,
      title: section.title,
      status: section.status,
      id: fields.id || shorthand?.id || null,
      severity: fields.severity || null,
      issue: fields.issue || shorthand?.text || noMaterialIssue,
      evidence: fields.evidence || null,
    };
  });
}

function parseLayer2MarkdownSections(markdown: string | null): ParsedLayer2Section[] {
  return splitLayerMarkdownSections(markdown, true).map((section) => ({
    key: section.key,
    title: section.title,
    status: section.status,
    questions: parseLayer2Questions(section.lines),
  }));
}

function splitLayerMarkdownSections(
  markdown: string | null,
  stripAtomicPrefix: boolean,
): Array<{ key: string; title: string; status: string | null; lines: string[] }> {
  const value = asString(markdown);
  if (!value) {
    return [];
  }
  const sections: Array<{ rawTitle: string; status: string | null; lines: string[] }> = [];
  let current: { rawTitle: string; status: string | null; lines: string[] } | null = null;
  for (const line of value.replace(/\r\n/g, "\n").split("\n")) {
    const heading = line.match(/^\s*#{1,6}\s+(.+?)\s*:\s*(PASS|PARTIAL|FAIL|YES|NO)\s*$/i);
    if (heading) {
      current = { rawTitle: heading[1].trim(), status: normalizeCheckStatus(heading[2]), lines: [] };
      sections.push(current);
      continue;
    }
    if (current) {
      current.lines.push(line);
    }
  }
  return sections.map((section) => {
    const rawTitle = stripAtomicPrefix
      ? section.rawTitle.replace(/^Atomic checks\s*[-:]\s*/i, "").trim()
      : section.rawTitle;
    const key = normalizeLayerKey(rawTitle);
    return {
      key,
      title: GATE_LAYER_METADATA.get(key)?.title || toTitleCase(rawTitle),
      status: section.status,
      lines: section.lines,
    };
  });
}

function parseLayer2Questions(lines: string[]): ParsedLayer2Question[] {
  const questions: Array<{ id: string | null; question: string; source: "field" | "shorthand"; lines: string[] }> = [];
  let current: { id: string | null; question: string; source: "field" | "shorthand"; lines: string[] } | null = null;
  for (const line of lines) {
    const questionMatch = line.match(/^\s*-\s*question:\s*(.+?)\s*$/i);
    if (questionMatch) {
      current = { id: null, question: questionMatch[1].trim(), source: "field", lines: [] };
      questions.push(current);
      continue;
    }

    const shorthand = parseLayerShorthandBullet([line], "L2");
    if (shorthand) {
      current = { id: shorthand.id, question: shorthand.text, source: "shorthand", lines: [] };
      questions.push(current);
      continue;
    }
    if (current) {
      current.lines.push(line);
    }
  }

  return questions.map((item) => {
    const fields = parseMarkdownFields(item.lines);
    return {
      id: fields.id || item.id,
      parentLayer1Id: fields.parent_layer_1_id || null,
      status: normalizeCheckStatus(fields.status) || normalizeCheckStatus(fields.answer),
      severity: fields.severity || null,
      title: fields.title || null,
      atomicIssue: fields.atomic_issue || null,
      question: item.question,
      answer: fields.answer || null,
      evidence: fields.evidence || null,
      issue: fields.issue || null,
      source: item.source,
    };
  });
}

function parseLayerShorthandBullet(lines: string[], layerPrefix: "L1" | "L2"): { id: string; text: string } | null {
  for (const line of lines) {
    const match = line.match(new RegExp(`^\\s*-\\s*(${layerPrefix}[-_][A-Za-z0-9._-]+)\\s*:\\s*(.+?)\\s*$`, "i"));
    if (match) {
      return { id: match[1], text: match[2].trim() };
    }
  }
  return null;
}

function answerForStatus(value: string | null): string | null {
  if (value === "pass") {
    return "YES";
  }
  if (value === "partial") {
    return "PARTIAL";
  }
  if (value === "fail") {
    return "NO";
  }
  return null;
}

function parseMarkdownFields(lines: string[]): Record<string, string | null> {
  const fields: Record<string, string | null> = {};
  for (const line of lines) {
    const match = line.match(/^\s*(?:-\s*)?([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*?)\s*$/);
    if (match) {
      fields[match[1].toLowerCase()] = match[2].trim();
    }
  }
  return fields;
}

function findNoMaterialIssue(lines: string[]): string | null {
  return lines.some((line) => /^(\s*-\s*)?No material issue\.?\s*$/i.test(line)) ? NO_MATERIAL_ISSUE : null;
}

function normalizeLayerKey(value: string | null): string {
  return (value || "")
    .replace(/^Atomic checks\s*[-:]\s*/i, "")
    .replace(/\s*:\s*(PASS|PARTIAL|FAIL|YES|NO)\s*$/i, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function syntheticId(prefix: string, value: string): string {
  const normalized = normalizeLayerKey(value).replace(/\s+/g, "-");
  return `${prefix}-${normalized || "item"}`;
}

function toTitleCase(value: string): string {
  return value
    .trim()
    .split(/\s+/)
    .map((word) => (word.length ? `${word[0].toUpperCase()}${word.slice(1).toLowerCase()}` : word))
    .join(" ");
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

type AnchorMatch = {
  start: number;
  end: number;
};

function normalizeAnchorText(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function findAnchorMatch(documentText: string, anchorText: string): AnchorMatch | null {
  const exactStart = documentText.indexOf(anchorText);
  if (exactStart >= 0) {
    return { start: exactStart, end: exactStart + anchorText.length };
  }

  const normalizedAnchor = normalizeAnchorText(anchorText);
  if (!normalizedAnchor) {
    return null;
  }

  const lowerDocument = documentText.toLowerCase();
  const lowerAnchor = anchorText.toLowerCase();
  const caseInsensitiveStart = lowerDocument.indexOf(lowerAnchor);
  return caseInsensitiveStart >= 0 ? { start: caseInsensitiveStart, end: caseInsensitiveStart + anchorText.length } : null;
}

function toneForComments(comments: DevilsAdvocateRoleComment[]): DocumentCommentTone {
  const tones = comments.map((comment) => toneForVote(comment.vote));
  if (tones.includes("bad")) {
    return "bad";
  }
  if (tones.includes("good")) {
    return "good";
  }
  if (tones.includes("warn")) {
    return "warn";
  }
  return "neutral";
}

function toneForVote(value: string | null): DocumentCommentTone {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) {
    return "warn";
  }
  if (["reject", "rework", "fail", "no"].includes(normalized)) {
    return "bad";
  }
  if (["approve", "approved", "pass", "yes", "for", "за"].includes(normalized)) {
    return "good";
  }
  return "warn";
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

function normalizeCheckStatus(value: unknown): string | null {
  const normalized = asString(value)?.toLowerCase();
  if (!normalized) {
    return null;
  }
  if (normalized === "yes") {
    return "pass";
  }
  if (normalized === "no") {
    return "fail";
  }
  return ["pass", "partial", "fail", "not_applicable"].includes(normalized) ? normalized : null;
}
