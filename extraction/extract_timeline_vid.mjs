// Video BEAT TIMELINE extraction — one focused call per video, separate from entity extraction.
// Usage: node scripts/extract_timeline_vid.mjs <input.jsonl> <output.json> <prompt.txt>
// Expects the model to return {"duration": n, "beats": [...]}. Resumes via <output>.progress.jsonl.
import fs from "fs";
const S = "/private/tmp/claude-501/-Users-apple-work-meta/e76840e7-1662-4b18-a477-b25558c46351/scratchpad/phase0";
const [,, INPUT, OUTPUT, PROMPTFILE] = process.argv;
const GBASE = process.env.BIFROST_GENAI_BASE_URL.replace(/\/$/, "");
const MODEL = "gemini-2.5-flash";
const CONCURRENCY = 10;
const PROMPT = fs.readFileSync(S + "/" + PROMPTFILE, "utf8");
const PROGRESS = S + "/" + OUTPUT + ".progress.jsonl";
const usage = { calls: 0, prompt_tokens: 0, completion_tokens: 0, errors: 0, bad_json: 0 };

function validate(tl) {
  if (!tl || !Array.isArray(tl.beats) || !tl.beats.length) return "no beats";
  const b = tl.beats;
  if (Math.abs(b[0].t0) > 0.05) return "does not start at 0";
  for (let i = 0; i < b.length - 1; i++) {
    if (typeof b[i].t1 !== "number" || typeof b[i + 1].t0 !== "number") return "non-numeric bounds";
    if (Math.abs(b[i].t1 - b[i + 1].t0) > 0.05) return `gap at beat ${i}`;
    if (b[i].t1 <= b[i].t0) return `zero/negative beat ${i}`;
  }
  return null;
}

async function callLLM(item) {
  const payload = {
    contents: [{ role: "user", parts: [
      { text: PROMPT },
      { fileData: { mimeType: "video/mp4", fileUri: item.u } },
    ]}],
    generationConfig: { temperature: 0, maxOutputTokens: 65536, responseMimeType: "application/json" },
  };
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(GBASE + "/models/" + MODEL + ":generateContent", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-bf-vk": process.env.BIFROST_API_KEY },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(240000),
      });
      const j = await r.json();
      usage.calls++;
      const um = j.usageMetadata;
      if (um) { usage.prompt_tokens += um.promptTokenCount || 0; usage.completion_tokens += um.candidatesTokenCount || 0; }
      const txt = j.candidates?.[0]?.content?.parts?.map(p => p.text).join("");
      if (!txt) throw new Error("empty: " + JSON.stringify(j).slice(0, 200));
      const parsed = JSON.parse(txt.replace(/^```json\s*|```\s*$/g, ""));
      const bad = validate(parsed);
      if (bad) { if (attempt === 2) { usage.bad_json++; return { error: bad, raw: parsed }; } throw new Error(bad); }
      return parsed;
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

const done = new Map();
if (fs.existsSync(PROGRESS)) {
  for (const line of fs.readFileSync(PROGRESS, "utf8").trim().split("\n").filter(Boolean)) {
    const r = JSON.parse(line); done.set(r.hash, r);
  }
  console.log("resuming:", done.size, "done");
}
const rows = fs.readFileSync(S + "/" + INPUT, "utf8").trim().split("\n").map(JSON.parse).filter(r => !done.has(r.hash));
console.log("timeline for", rows.length, "videos ->", OUTPUT);
const t0 = Date.now();
const fresh = await mapLimit(rows, CONCURRENCY, async (item, idx) => {
  const tl = await callLLM(item);
  const rec = { hash: item.hash, url: item.u, timeline: tl };
  fs.appendFileSync(PROGRESS, JSON.stringify(rec) + "\n");
  process.stdout.write((idx % 20 === 19) ? (idx + 1) + " " : ".");
  return rec;
});
fs.writeFileSync(S + "/" + OUTPUT, JSON.stringify([...done.values(), ...fresh], null, 1));
console.log("\ndone", Math.round((Date.now() - t0) / 1000) + "s");
console.log("usage:", JSON.stringify(usage));
