const { expect, test } = require("@playwright/test");

const mainAnalysisResult = {
  verdict: "need_evidence",
  summary: "Needs stronger metric evidence.",
  findings: [
    {
      id: "F1",
      severity: "high",
      title: "Metric proof is incomplete",
      evidence: "The document names traction but does not provide a cohort or control-group readout.",
    },
  ],
  checks: [
    {
      name: "Incrementality evidence",
      status: "partial",
      explanation: "The defense needs an experiment or comparable holdout to support impact claims.",
    },
  ],
  key_findings: ["Metric proof is incomplete"],
};

const devilsAdvocateResult = {
  run_mode: "full_ic_voting",
  anchored_comments: [
    {
      id: "C1",
      anchor: "metrics",
      comment: "Committee will ask for incrementality evidence.",
      severity: "high",
    },
  ],
  trailer: {
    executive_summary: "Needs evidence.",
    key_risks: ["weak proof"],
    missing_evidence: ["control group"],
    next_steps: ["add experiment readout"],
  },
  ic_decision: {
    verdict: "need_evidence",
    rationale: "Missing proof.",
  },
  predicted_questions: ["What is incremental impact?"],
  consulted_wiki_pages: ["risk-patterns.md"],
  source_citations: ["wiki-ic/risk-patterns.md"],
};

test.setTimeout(120000);

test("admin creates user and user completes the MVP document analysis flow", async ({ page }) => {
  const baseUrl = process.env.E2E_BASE_URL;
  const apiBaseUrl = resolveApiBaseUrl(baseUrl);
  const adminLogin = process.env.E2E_ADMIN_LOGIN;
  const adminPassword = process.env.E2E_ADMIN_PASSWORD;
  const userLogin = `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const userPassword = "e2e-strong-password";

  await page.goto(`${baseUrl}/login`);
  await fillAndSubmitSignIn(page, adminLogin, adminPassword);
  await expect(page).toHaveURL(/\/documents/);

  await page.goto(`${baseUrl}/admin/users`);
  await page.getByLabel("Login").fill(userLogin);
  await page.getByLabel("Display name").fill("E2E User");
  await page.getByLabel("Initial password").fill(userPassword);
  await page.getByRole("button", { name: "Create user" }).click();
  await expect(page.getByText(userLogin)).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await fillAndSubmitSignIn(page, userLogin, userPassword);
  await expect(page).toHaveURL(/\/documents/);

  await page.goto(`${baseUrl}/documents/upload`);
  await expect(page.getByRole("heading", { name: /Upload/i })).toBeVisible();

  await saveDummyProviderKey(page, apiBaseUrl);

  await page.getByLabel("Title").fill("E2E Gate 2 document");
  await page.getByLabel("Manual type").selectOption("gate_2");
  await page.getByLabel("File").setInputFiles({
    name: "gate2-e2e.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      [
        "# Gate 2 investment defense",
        "",
        "This document describes MVP traction, monetization assumptions, and metrics.",
        "It intentionally needs stronger metric evidence for committee review.",
      ].join("\n"),
    ),
  });
  await page.getByRole("button", { name: "Upload document" }).click();
  await expect(page).toHaveURL(/\/documents\/[0-9a-f-]+$/);

  const documentId = page.url().split("/").pop();
  await waitForDocumentParsed(page, apiBaseUrl, documentId);
  await page.reload();
  await expect(page.getByText("completed").first()).toBeVisible();
  await expect(page.getByText("This document describes MVP traction")).toBeVisible();

  const analysis = await apiJson(page, apiBaseUrl, `/documents/${documentId}/analyses`, {
    method: "POST",
    body: {
      provider: "openai_compatible",
      model: "gpt-test",
      document_type_override: "gate_2",
      run_parameters: {
        mock_provider_result: {
          structured_text: JSON.stringify(mainAnalysisResult),
          raw_output: "raw e2e main analysis",
          input_tokens: 10,
          output_tokens: 20,
          latency_ms: 30,
        },
        predicted_comments_mock_provider_result: {
          structured_text: JSON.stringify(devilsAdvocateResult),
          raw_output: "raw e2e predicted comments",
          input_tokens: 7,
          output_tokens: 11,
          latency_ms: 25,
        },
      },
    },
  });

  await waitForCompletedAnalysis(page, apiBaseUrl, analysis.id);
  await page.goto(`${baseUrl}/analyses/${analysis.id}`);
  await expect(page.getByRole("heading", { name: "Analysis" })).toBeVisible();
  await expect(page.getByText("Needs stronger metric evidence.", { exact: true })).toBeVisible();
  await expect(page.getByText("Metric proof is incomplete").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Devil's Advocate" })).toBeVisible();
  await expect(page.getByText("What is incremental impact?", { exact: true })).toBeVisible();

  await page.getByLabel("Comment").fill("E2E feedback: result is useful for review.");
  await page.getByLabel("Use for benchmark review").check();
  await page.getByRole("button", { name: "Submit feedback" }).click();
  await expect(page.getByText("Feedback saved")).toBeVisible();

  await page.getByRole("button", { name: "Create etalon draft" }).click();
  await expect(page).toHaveURL(/\/annotation\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Annotation" })).toBeVisible();
  await expect(page.getByText("draft", { exact: true }).first()).toBeVisible();
});

function resolveApiBaseUrl(baseUrl) {
  if (process.env.E2E_API_BASE_URL) {
    return process.env.E2E_API_BASE_URL.replace(/\/$/, "");
  }
  const url = new URL(baseUrl);
  url.port = "8000";
  return url.toString().replace(/\/$/, "");
}

async function fillAndSubmitSignIn(page, login, password) {
  const loginInput = page.getByLabel("Login");
  const passwordInput = page.getByLabel("Password");
  const submit = page.getByRole("button", { name: "Sign in" });

  await expect(loginInput).toBeVisible();
  await expect(passwordInput).toBeVisible();

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await loginInput.fill("");
    await passwordInput.fill("");
    await loginInput.click();
    await loginInput.pressSequentially(login);
    await passwordInput.click();
    await passwordInput.pressSequentially(password);
    try {
      await expect(submit).toBeEnabled({ timeout: 1000 });
      await submit.click();
      return;
    } catch (error) {
      if (attempt === 2) {
        throw error;
      }
      await page.waitForTimeout(250);
    }
  }
}

async function saveDummyProviderKey(page, apiBaseUrl) {
  await apiJson(page, apiBaseUrl, "/settings/provider-keys/openai_compatible", {
    method: "PUT",
    body: {
      api_key: "sk-e2e-local-test",
      base_url: null,
      default_model: "gpt-test",
    },
  });
}

async function waitForDocumentParsed(page, apiBaseUrl, documentId) {
  return waitFor(page, "document parse completion", async () => {
    const document = await apiJson(page, apiBaseUrl, `/documents/${documentId}`);
    if (document.parse_status === "failed") {
      throw new Error(document.parse_error || "document parse failed");
    }
    return document.parse_status === "completed" ? document : null;
  });
}

async function waitForCompletedAnalysis(page, apiBaseUrl, analysisId) {
  return waitFor(page, "analysis and predicted comments completion", async () => {
    const analysis = await apiJson(page, apiBaseUrl, `/analyses/${analysisId}`);
    if (analysis.status === "failed") {
      throw new Error(analysis.error_message || "analysis failed");
    }
    if (analysis.status !== "completed") {
      return null;
    }
    if (!analysis.predicted_comment_run) {
      return null;
    }
    if (analysis.predicted_comment_run.status === "failed") {
      throw new Error(analysis.predicted_comment_run.error_message || "predicted comments failed");
    }
    return analysis.predicted_comment_run.status === "completed" ? analysis : null;
  });
}

async function waitFor(page, description, condition, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const result = await condition();
      if (result) {
        return result;
      }
    } catch (error) {
      lastError = error;
    }
    await page.waitForTimeout(750);
  }
  throw new Error(`Timed out waiting for ${description}${lastError ? `: ${lastError.message}` : ""}`);
}

async function apiJson(page, apiBaseUrl, path, options = {}) {
  const result = await page.evaluate(
    async ({ apiBaseUrl: evaluatedApiBaseUrl, path: evaluatedPath, options: evaluatedOptions }) => {
      const response = await fetch(`${evaluatedApiBaseUrl}${evaluatedPath}`, {
        method: evaluatedOptions.method || "GET",
        credentials: "include",
        headers:
          evaluatedOptions.body === undefined
            ? evaluatedOptions.headers || {}
            : { "Content-Type": "application/json", ...(evaluatedOptions.headers || {}) },
        body: evaluatedOptions.body === undefined ? undefined : JSON.stringify(evaluatedOptions.body),
      });
      const text = await response.text();
      let body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch {
        body = text;
      }
      return { ok: response.ok, status: response.status, body };
    },
    { apiBaseUrl, path, options },
  );

  if (!result.ok) {
    const detail =
      result.body && typeof result.body === "object" && "detail" in result.body ? result.body.detail : result.body;
    throw new Error(`API ${path} failed with ${result.status}: ${detail || "no response body"}`);
  }
  return result.body;
}
