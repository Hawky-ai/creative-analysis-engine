// Image entity extraction. One LLM call per creative; observations JSON out.
// Usage: node extraction/extract_images.mjs <input.jsonl> <output.json> <prompt.txt> [skip.json]
//   input.jsonl rows: {"hash": "...", "u": "<image url>", "ad_copy": "<json string or {}>", ...passthrough}
//   skip.json (optional): JSON array of hashes already extracted (resume/delta runs)
// Model + endpoint + concurrency come from config.yaml; secrets from env (see .env.example).
import fs from "fs";
import { inlineDataUri } from "./media-inline.mjs";
import { CONFIG, env } from "./config.mjs";

const [,, INPUT, OUTPUT, PROMPTFILE, SKIPFILE] = process.argv;
if (!INPUT || !OUTPUT || !PROMPTFILE) {
  console.error("usage: node extraction/extract_images.mjs <input.jsonl> <output.json> <prompt.txt> [skip.json]");
  process.exit(1);
}
const BASE = env(CONFIG.llm_proxy.base_url_env).replace(/\/$/, "");
const KEY = env(CONFIG.llm_proxy.api_key_env);
const MODEL = CONFIG.extraction.image_model;
const CONCURRENCY = CONFIG.extraction.image_concurrency;
const TIMEOUT_MS = CONFIG.extraction.request_timeout_ms;
const PROMPT = fs.readFileSync(PROMPTFILE, "utf8");
const usage = { calls: 0, prompt_tokens: 0, completion_tokens: 0, errors: 0 };

function adCopyText(raw) {
  try {
    const c = JSON.parse(raw || "{}");
    const parts = [];
    if (c.primary_text) parts.push("PRIMARY TEXT: " + c.primary_text);
    if (c.headline) parts.push("HEADLINE: " + c.headline);
    if (c.description) parts.push("DESCRIPTION: " + c.description);
    for (const v of (c.primary_text_variants || []).slice(0, 4)) parts.push("PRIMARY VARIANT: " + v);
    for (const v of (c.headline_variants || []).slice(0, 4)) parts.push("HEADLINE VARIANT: " + v);
    for (const v of (c.description_variants || []).slice(0, 3)) parts.push("DESC VARIANT: " + v);
    if (c.cta) parts.push("CTA BUTTON: " + c.cta);
    return parts.join("\n").slice(0, 4000) || "(no ad copy available)";
  } catch { return "(no ad copy available)"; }
}

async function callLLM(item) {
  let body = null;
  const buildBody = async () => ({
    model: MODEL, temperature: 0,
    response_format: { type: "json_object" },
    messages: [{ role: "user", content: [
      { type: "text", text: PROMPT + "\n\nAD COPY:\n" + adCopyText(item.ad_copy) },
      { type: "image_url", image_url: { url: await inlineDataUri(item.u) } },
    ]}],
  });
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      if (!body) body = await buildBody();
      const r = await fetch(BASE + "/chat/completions", {
        method: "POST",
        headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      const j = await r.json();
      usage.calls++;
      if (j.usage) { usage.prompt_tokens += j.usage.prompt_tokens || 0; usage.completion_tokens += j.usage.completion_tokens || 0; }
      const txt = j.choices?.[0]?.message?.content;
      if (!txt) throw new Error("empty: " + JSON.stringify(j).slice(0, 200));
      const parsed = JSON.parse(txt.replace(/^```json\s*|```\s*$/g, ""));
      if (!Array.isArray(parsed.observations)) throw new Error("no observations array");
      return parsed.observations;
    } catch (e) {
      if (attempt === 2) { usage.errors++; return { error: String(e.message).slice(0, 200) }; }
      await new Promise(res => setTimeout(res, 2000 * (attempt + 1)));
    }
  }
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length); let i = 0;
  await Promise.all(Array.from({ length: limit }, async () => {
    while (i < items.length) { const idx = i++; out[idx] = await fn(items[idx], idx); }
  }));
  return out;
}

const skip = new Set(SKIPFILE ? JSON.parse(fs.readFileSync(SKIPFILE, "utf8")) : []);
const rows = fs.readFileSync(INPUT, "utf8").trim().split("\n").map(JSON.parse).filter(r => !skip.has(r.hash));
console.log("extracting", rows.length, "creatives ->", OUTPUT);
const t0 = Date.now();
const results = await mapLimit(rows, CONCURRENCY, async (item, idx) => {
  const obs = await callLLM(item);
  process.stdout.write((idx % 20 === 19) ? (idx + 1) + " " : ".");
  return { hash: item.hash, spend: item.spend, n_ads: item.n_ads, url: item.u, obs };
});
fs.writeFileSync(OUTPUT, JSON.stringify(results, null, 1));
console.log("\ndone", Math.round((Date.now() - t0) / 1000) + "s");
console.log("usage:", JSON.stringify(usage));
