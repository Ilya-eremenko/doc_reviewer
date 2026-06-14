import { afterEach, describe, expect, it, vi } from "vitest";

import { getProviderDefaultModel, listProviderModels, testProviderKey } from "./provider-settings";

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("provider settings api", () => {
  it("resolves saved default model for the selected provider", () => {
    expect(
      getProviderDefaultModel(
        [
          {
            provider: "anthropic_compatible",
            base_url: null,
            default_model: "claude-test",
            available_models: ["claude-test"],
            api_key_fingerprint: "anthropic_compatible:...test",
            has_key: true,
          },
          {
            provider: "openai_compatible",
            base_url: "https://api.example.test/v1",
            default_model: "gpt-saved",
            available_models: ["gpt-saved", "gpt-other"],
            api_key_fingerprint: "openai_compatible:...test",
            has_key: true,
          },
        ],
        "openai_compatible",
      ),
    ).toBe("gpt-saved");
  });

  it("loads shared provider model options without provider secrets", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        provider_models: [
          {
            provider: "openai_compatible",
            default_model: "openai/gpt-5.5",
            available_models: ["openai/gpt-5.5", "google/gemini-3.5-flash"],
            has_key: true,
          },
        ],
      }),
    });
    global.fetch = fetchMock;

    const response = await listProviderModels();

    expect(response.provider_models[0].available_models).toEqual(["openai/gpt-5.5", "google/gemini-3.5-flash"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/settings/provider-models",
      expect.objectContaining({
        credentials: "include",
      }),
    );
  });

  it("posts provider key test request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        provider: "openai_compatible",
        status: "ok",
        message: "Provider key is configured and decryptable.",
        default_model: "gpt-test",
        base_url: null,
      }),
    });
    global.fetch = fetchMock;

    const response = await testProviderKey("openai_compatible");

    expect(response.status).toBe("ok");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/settings/provider-keys/openai_compatible/test",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });
});
