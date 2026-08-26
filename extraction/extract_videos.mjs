// Video entity extraction. Sends the video natively (file URI) to a multimodal model
// via the Bifrost GenAI endpoint — the model watches the whole video incl. audio.
// Usage: node extraction/extract_videos.mjs <input.jsonl> <output.json> <prompt.txt> [skip.json]
//   input.jsonl rows: {"hash": "...", "u": "<video url>", "ad_copy": "<json string or {}>", ...passthrough}
// Progress is checkpointed to <output>.progress.jsonl — rerunning the same command RESUMES
// from where it stopped (survives crashes/stalls). Model + endpoint from config.yaml.
import fs from "fs";
import { CONFIG, env } from "./config.mjs";

const [,, INPUT, OUTPUT, PROMPTFILE, SKIPFILE] = process.argv;
if (!INPUT || !OUTPUT || !PROMPTFILE) {
  console.error("usage: node extraction/extract_videos.mjs <input.jsonl> <output.json> <prompt.txt> [skip.json]");
  process.exit(1);
}
const GBASE = env(CONFIG.bifrost.genai_base_url_env).replace(/\/$/, "");
const GKEY = env(CONFIG.bifrost.api_key_env);
const MODEL = CONFIG.extraction.video_model;
const CONCURRENCY = CONFIG.extraction.video_concurrency;
const TIMEOUT_MS = CONFIG.extraction.video_timeout_ms;
const PROMPT = fs.readFileSync(PROMPTFILE, "utf8");
const PROGRESS = OUTPUT + ".progress.jsonl";
const usage = { calls: 0, prompt_tokens: 0, completion_tokens: 0, errors: 0 };

function adCopyText(raw) {
  try {
    const c = JSON.parse(raw || "{}");
    const parts = [];
    if (c.primary_text) parts.push("PRIMARY TEXT: " + c.primary_text);
    if (c.headline) parts.push("HEADLINE: " + c.headline);
    if (c.description) parts.push("DESCRIPTION: " + c.description);
    if (c.cta) parts.push("CTA BUTTON: " + c.cta);
    return parts.join("\n").slice(0, 4000) || "(no ad copy available)";
  } catch { return "(no ad copy available)"; }
}

async function callLLM(item) {
  const payload = {
    contents: [{ role: "user", parts: [
      { text: PROMPT + "\n\nAD COPY:\n" + adCopyText(item.ad_copy) },
      { fileData: { mimeType: "video/mp4", fileUri: item.u } },
    ]}],
    generationConfig: { temperature: 0, maxOutputTokens: 65536, responseMimeType: "application/json" },
  };
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(GBASE + "/models/" + MODEL + ":generateContent", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-bf-vk": GKEY },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      const j = await r.json();
      usage.calls++;
      const um = j.usageMetadata;
      if (um) { usage.prompt_tokens += um.promptTokenCount || 0; usage.completion_tokens += um.candidatesTokenCount || 0; }
      const txt = j.candidates?.[0]?.content?.parts?.map(p => p.text).join("");
      if (!txt) throw new Error("empty: " + JSON.stringify(j).slice(0, 200));
      const parsed = JSON.parse(txt.replace(/^```json\s*|```\s*$/g, ""));
      if (!Array.isArray(parsed.observations)) throw new Error("no observations array");
      return parsed.observations;
    } catch (e) {
      if (attempt === 2) { usage.errors++; return { error: String(e.message).slice(0, 200) }; }
      await new Promise(res => setTimeout(res, 3000 * (attempt + 1)));
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
const done = new Map();
if (fs.existsSync(PROGRESS)) {
  for (const line of fs.readFileSync(PROGRESS, "utf8").trim().split("\n").filter(Boolean)) {
    const r = JSON.parse(line);
    done.set(r.hash, r);
  }
  console.log("resuming:", done.size, "already done");
}
const rows = fs.readFileSync(INPUT, "utf8").trim().split("\n").map(JSON.parse)
  .filter(r => !skip.has(r.hash) && !done.has(r.hash));
console.log("extracting", rows.length, "creatives ->", OUTPUT);
const t0 = Date.now();
const fresh = await mapLimit(rows, CONCURRENCY, async (item, idx) => {
  const obs = await callLLM(item);
  const rec = { hash: item.hash, spend: item.spend, n_ads: item.n_ads, url: item.u, obs };
  fs.appendFileSync(PROGRESS, JSON.stringify(rec) + "\n");
  process.stdout.write((idx % 20 === 19) ? (idx + 1) + " " : ".");
  return rec;
});
const results = [...done.values(), ...fresh];
fs.writeFileSync(OUTPUT, JSON.stringify(results, null, 1));
console.log("\ndone", Math.round((Date.now() - t0) / 1000) + "s");
console.log("usage:", JSON.stringify(usage));
