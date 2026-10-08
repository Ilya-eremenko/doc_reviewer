export type NewSummaryLanguage = "ru" | "en";

export type NewSummaryStage =
  | "Gate 1"
  | "Gate 2"
  | "Gate 3"
  | "Progress Review"
  | "Stream Review 1"
  | "Stream Review 2+"
  | "Stream Review 2+ / Progress Review"
  | "Unknown";

export type NewSummaryRequiredElement = {
  id: string;
  label: string;
  status: "есть" | "частично подтверждено" | "нет" | "present" | "partially confirmed" | "missing" | `${number}/${number}`;
  evidence?: string;
  detail?: NewSummaryRequiredDetails;
};

export type NewSummaryTractionTable = {
  metric?: "revenue" | "dtb";
  cumulative?: boolean;
  metric_label?: string;
  periods: string[];
  rows: Array<{
    label: string;
    values: string[];
    mismatch_periods?: string[];
  }>;
};

export type NewSummaryTractionSummary = NewSummaryTractionTable | { tables: NewSummaryTractionTable[] };

export type NewSummaryCriticalProblem = string | { issue: string; fact: string };

export type NewSummaryRequiredDetails =
  | {
      type: "source_links";
      availability: "provided" | "absent" | "unavailable";
      links: Array<{ label: string; url: string }>;
    }
  | {
      type: "plan_fact";
      launches: Array<{ output: string; status: "completed" | "partial" | "not_completed" | "unknown"; comment?: string }>;
      metrics: Array<{ metric: string; planned: string; actual: string }>;
    }
  | {
      type: "hypotheses_with_thresholds";
      items: Array<{ hypothesis: string; confirmation_condition: string }>;
    }
  | {
      type: "solution_validation";
      items: Array<{
        text: string;
        verdict: "confirmed" | "insufficient";
        test?: string;
        expected_result?: string;
        actual_result?: string;
      }>;
    }
  | {
      type: "metric_binding";
      input_metrics: Array<{ metric: string; binding: "confirmed" | "insufficient"; evidence: string }>;
      output_metrics: Array<{ metric: string; binding: "confirmed" | "insufficient"; evidence: string }>;
    }
  | {
      type: "next_review_plan";
      outputs_until_next_review: string[];
      metrics_until_next_review: Array<{ metric: string; current: string; next_review: string }>;
    }
  | {
      type: "stop_criteria";
      primary_criterion?: string;
      criteria: string[];
    }
  | {
      type: "criteria_list";
      criteria: string[];
    };

export type NewSummaryRequiredDetailsById = Record<string, NewSummaryRequiredDetails>;

export type NewSummaryContent = {
  schema_version: "new-summary-v1" | "new-summary-v2" | "new-summary-v3" | "new-summary-v4" | "new-summary-v5" | "new-summary-v6" | "new-summary-v7" | "new-summary-v8";
  language: NewSummaryLanguage;
  title: string;
  stage: NewSummaryStage;
  document_quality_percent?: number;
  traction_summary?: NewSummaryTractionSummary;
  context: string;
  required_elements: NewSummaryRequiredElement[];
  required_details?: NewSummaryRequiredDetailsById;
  confirmed?: string[];
  insufficiently_confirmed?: string[];
  critical_problems?: NewSummaryCriticalProblem[];
  other?: string[];
};

export type NewSummaryReport = {
  analysis_id: string;
  created_at?: string | null;
  docx_path?: string | null;
  pdf_path?: string | null;
  route?: string | null;
  ru: NewSummaryContent;
  en: NewSummaryContent;
};
