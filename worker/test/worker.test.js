import assert from "node:assert/strict";
import { test } from "node:test";

import worker, { extractWorkersAiText } from "../src/index.js";

const call = (env, body, token = "secret") =>
  worker.fetch(
    new Request("https://x/", {
      method: "POST",
      headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
    env,
  );

test("rejects a wrong token", async () => {
  const res = await call({ APP_TOKEN: "secret" }, { prompt: "hi" }, "nope");
  assert.equal(res.status, 401);
});

test("falls back to the next Workers AI model and skips keyless providers", async () => {
  const seen = [];
  const env = {
    APP_TOKEN: "secret",
    WORKERS_AI_MODELS: "@cf/a,@cf/b",
    AI: {
      async run(model, input) {
        seen.push(model);
        assert.equal(input.messages[0].role, "system");
        if (model === "@cf/a") throw new Error("capacity");
        return { response: "سلام" };
      },
    },
  };
  const res = await call(env, { system: "s", prompt: "p" });
  const data = await res.json();
  assert.equal(res.status, 200);
  assert.equal(data.text, "سلام");
  assert.equal(data.model, "@cf/b");
  assert.deepEqual(seen, ["@cf/a", "@cf/b"]);
  assert.equal(data.attempts[0].ok, false);
});

test("reports every failure when nothing works", async () => {
  const env = { APP_TOKEN: "secret", AI: { run: async () => ({ response: "" }) } };
  const res = await call(env, { prompt: "p" });
  assert.equal(res.status, 502);
  assert.ok((await res.json()).attempts.length >= 1);
});

test("reads the different Workers AI response shapes", () => {
  assert.equal(extractWorkersAiText({ response: "a" }), "a");
  assert.equal(extractWorkersAiText({ choices: [{ message: { content: "b" } }] }), "b");
  assert.equal(
    extractWorkersAiText({ output: [{ type: "reasoning" }, { type: "message", content: [{ text: "c" }] }] }),
    "c",
  );
});
