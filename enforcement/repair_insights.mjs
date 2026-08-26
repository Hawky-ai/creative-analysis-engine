import fs from "fs";
import { execSync } from "child_process";
const BASE = process.env.LLM_BASE_URL.replace(/\/$/, ""), KEY = process.env.LLM_API_KEY;
const BRAND = process.argv[2];
const val = JSON.parse(fs.readFileSync(`${BRAND}/results/insights_validation.json`));
const ins = JSON.parse(fs.readFileSync(`${BRAND}/results/insights_v3.json`));
const obs = JSON.parse(fs.readFileSync(`${BRAND}/raw/canonical.json`));
const byHash = {};
for (const o of obs) (byHash[o.hash] = byHash[o.hash] || []).push(o);
const pat = JSON.parse(fs.readFileSync(`${BRAND}/results/patterns.json`));
const pmap = {};
for (const p of pat.patterns) pmap[`${p.facet}:${p.trait}`] = p;

async function repair(v) {
  const key = v.key, d = ins[key], p = pmap[key];
  if (!p) return null;
  // real evidence menu the model may quote from
  const hs = p.hashes.slice(0, 8);
  const menu = hs.map(h => `[${h.slice(0,12)}]\n` + (byHash[h] || []).slice(0, 10)
    .map(o => `  - ${o.facet}=${o.value}: "${String(o.evidence).slice(0, 110)}"`).join("\n")).join("\n");
  const prompt = `Your previous insight for pattern "${key}" FAILED validation with these errors:
${v.errors.join("\n")}

Rules you violated: proof.hash MUST be one of the 12-char ids below, and proof.quote MUST be copied VERBATIM from the evidence lines below (these are the only quotable sources). Do not invent hashes or paraphrase quotes.

Your previous (invalid) output: ${JSON.stringify(d).slice(0, 1200)}

QUOTABLE EVIDENCE:
${menu}

Return corrected JSON with the same schema: {"claim","layer_agreement","mechanism","proof":[{"hash","quote","metric"}],"action_type","action","caveats"}. Keep your analysis; fix only what validation flagged. claim must be a full sentence (>=30 chars). action_type MUST be exactly "MAKE THIS AD" or "RESTRUCTURE CAMPAIGNS". "action" must be a substantive plain-text brief (>=60 chars): for MAKE THIS AD give subject/setting/on-screen text/offer treatment/first-3-seconds; for RESTRUCTURE CAMPAIGNS name what to launch or pause, the audience/objective change, and the metric that proves it within 14 days. Never null fields. If layer_agreement is "disagree", caveats must be non-empty.`;
  const r = await fetch(BASE + "/chat/completions", {
    method: "POST", headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "gemini/gemini-2.5-flash", temperature: 0, response_format: { type: "json_object" }, messages: [{ role: "user", content: prompt }] }),
    signal: AbortSignal.timeout(120000),
  });
  const j = await r.json();
  if (!j.choices) throw new Error("api");
  return JSON.parse(j.choices[0].message.content.replace(/^```json\s*|```\s*$/g, ""));
}
for (const v of val.violations) {
  try {
    const fixed = await repair(v);
    if (fixed) { ins[v.key] = { pattern: ins[v.key].pattern, kpi: ins[v.key].kpi, ...fixed }; console.log("repaired", v.key); }
  } catch (e) { console.error("FAIL", v.key, e.message); }
}
fs.writeFileSync(`${BRAND}/results/insights_v3.json`, JSON.stringify(ins, null, 1));
