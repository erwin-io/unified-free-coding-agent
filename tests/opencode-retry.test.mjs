import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

// Inject a minimal implementation of the official Plugin.define contract.
// This isolates the retry policy without requiring a paid provider or OpenCode.
const source = readFileSync(new URL(
  "../.opencode/plugins/unified-free-capacity-retry/index.js", import.meta.url
), "utf8");
const moduleSource = source.replace(
  'import { Plugin } from "@opencode/plugin"',
  "const Plugin = { define: (definition) => definition }"
);
const plugin = (await import("data:text/javascript," +
  encodeURIComponent(moduleSource))).default;

async function retryPolicy() {
  let handler;
  const ctx = { session: { hook: async (name, fn) => {
    assert.equal(name, "retry");
    handler = fn;
    return { dispose: async () => {} };
  }}};
  await plugin.setup(ctx);
  assert.equal(typeof handler, "function");
  return handler;
}

test("automatic retry for a temporarily unavailable gateway", async () => {
  const retry = await retryPolicy();
  for (const [attempt, expected] of [[2, 10000], [3, 20000], [4, 40000]]) {
    const event = { error: { status: 503 }, attempt,
                    decision: { retry: false } };
    await retry(event);
    assert.deepEqual(event.decision, { retry: true, delay: expected });
  }
});

test("permanent errors are never overridden", async () => {
  const retry = await retryPolicy();
  for (const status of [400, 401, 403, 404, 422]) {
    const event = { error: { status }, attempt: 2,
                    decision: { retry: false } };
    await retry(event);
    assert.deepEqual(event.decision, { retry: false });
  }
});

test("retry remains bounded at the configured threshold", async () => {
  const retry = await retryPolicy();
  const event = { error: { status: 503 }, attempt: 5,
                  decision: { retry: true, delay: 1000 } };
  await retry(event);
  assert.deepEqual(event.decision, { retry: false });
});
