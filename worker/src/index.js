// Persian Lyric Sync AI relay: one endpoint for the desktop app, provider fallback here.
//
// POST /  (Authorization: Bearer <APP_TOKEN>)
//   body:  { "system": "...", "prompt": "...", "max_tokens": 1500 }
//   reply: { "text": "...", "provider": "workers-ai", "model": "...", "attempts": [...] }
//
// Providers are tried in PROVIDER_ORDER. Workers AI needs no key (free tier); Claude and
// Gemini are skipped until their secrets exist, so adding a key later just turns them on.

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

export default {
  async fetch(request, env) {
    if (request.method === "GET") {
      return json({ ok: true, providers: availableProviders(env) });
    }
    if (request.method !== "POST") {
      return json({ error: "method not allowed" }, 405);
    }
    if (!env.APP_TOKEN || request.headers.get("authorization") !== `Bearer ${env.APP_TOKEN}`) {
      return json({ error: "unauthorized" }, 401);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "body must be JSON" }, 400);
    }
    const system = String(body.system || "");
    const prompt = String(body.prompt || "");
    const maxTokens = Math.min(Math.max(Number(body.max_tokens) || 1500, 64), 8000);
    if (!prompt) {
      return json({ error: "prompt is required" }, 400);
    }

    const attempts = [];
    for (const provider of availableProviders(env)) {
      for (const model of modelsFor(provider, env)) {
        try {
          const text = await PROVIDERS[provider](env, model, system, prompt, maxTokens);
          if (text && text.trim()) {
            attempts.push({ provider, model, ok: true });
            return json({ text, provider, model, attempts });
          }
          attempts.push({ provider, model, ok: false, error: "empty response" });
        } catch (err) {
          attempts.push({ provider, model, ok: false, error: String(err && err.message || err).slice(0, 300) });
        }
      }
    }
    return json({ error: "all providers failed", attempts }, 502);
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function availableProviders(env) {
  const order = (env.PROVIDER_ORDER || "workers-ai,claude,gemini").split(",").map((s) => s.trim());
  return order.filter((p) => {
    if (p === "workers-ai") return Boolean(env.AI);
    if (p === "claude") return Boolean(env.ANTHROPIC_API_KEY);
    if (p === "gemini") return Boolean(env.GEMINI_API_KEY);
    return false;
  });
}

function modelsFor(provider, env) {
  if (provider === "workers-ai") {
    return (env.WORKERS_AI_MODELS || "@cf/openai/gpt-oss-120b,@cf/meta/llama-3.3-70b-instruct-fp8-fast")
      .split(",").map((s) => s.trim()).filter(Boolean);
  }
  if (provider === "claude") return [env.CLAUDE_MODEL || "claude-opus-5"];
  if (provider === "gemini") return [env.GEMINI_MODEL || "gemini-2.5-flash"];
  return [];
}

const PROVIDERS = {
  async "workers-ai"(env, model, system, prompt, maxTokens) {
    const messages = [];
    if (system) messages.push({ role: "system", content: system });
    messages.push({ role: "user", content: prompt });
    const result = await env.AI.run(model, { messages, max_tokens: maxTokens });
    return extractWorkersAiText(result);
  },

  async claude(env, model, system, prompt, maxTokens) {
    const { default: Anthropic } = await import("@anthropic-ai/sdk");
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const response = await client.beta.messages.create({
      model,
      max_tokens: maxTokens,
      // A policy decline is retried server-side on Anthropic's recommended fallback model.
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      // Short metadata writing: low effort keeps it fast and cheap.
      output_config: { effort: "low" },
      ...(system ? { system } : {}),
      messages: [{ role: "user", content: prompt }],
    });
    if (response.stop_reason === "refusal") {
      throw new Error("refused");
    }
    return response.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  },

  async gemini(env, model, system, prompt, maxTokens) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
      body: JSON.stringify({
        ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}),
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: maxTokens },
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    const data = await res.json();
    const parts = data?.candidates?.[0]?.content?.parts || [];
    return parts.map((p) => p.text || "").join("");
  },
};

// Workers AI models answer in a few shapes: {response} for classic chat models, an
// OpenAI-style {choices} or Responses-style {output} for others (e.g. gpt-oss).
export function extractWorkersAiText(result) {
  if (!result) return "";
  if (typeof result === "string") return result;
  if (typeof result.response === "string") return result.response;
  if (result.response && typeof result.response === "object") return JSON.stringify(result.response);
  const choice = result.choices?.[0];
  if (choice?.message?.content) return choice.message.content;
  if (typeof choice?.text === "string") return choice.text;
  if (typeof result.output_text === "string") return result.output_text;
  if (Array.isArray(result.output)) {
    return result.output
      .filter((item) => item.type === "message")
      .flatMap((item) => item.content || [])
      .map((c) => c.text || "")
      .join("");
  }
  return "";
}
