import fs from "fs";
const BASE = process.env.LLM_BASE_URL.replace(/\/$/, ""), KEY = process.env.LLM_API_KEY;
const BRAND = process.argv[2];
const CONV = BRAND === "bhanzu" ? "demo_sched" : "leads";
const UNIT = BRAND === "bhanzu" ? "demo booked" : "lead";

const inv = {};
for (const l of fs.readFileSync(`${BRAND}/raw/inventory.jsonl`, "utf8").trim().split("\n")) { const r = JSON.parse(l); inv[r.hash] = r; }
const obs = JSON.parse(fs.readFileSync(`${BRAND}/raw/canonical.json`));
const v3 = JSON.parse(fs.readFileSync(`${BRAND}/results/engine_v3.json`));
const pat = JSON.parse(fs.readFileSync(`${BRAND}/results/patterns.json`));
const recipes = JSON.parse(fs.readFileSync(`${BRAND}/results/recipes.json`));
const byHash = {};
for (const o of obs) (byHash[o.hash] = byHash[o.hash] || []).push(o);

const conf = pat.patterns.filter(p => p.verdict !== "INCONCLUSIVE" && (p.level || "v") !== "c")
  .sort((a, b) => Math.abs(b.cpl/b.baseline - 1) - Math.abs(a.cpl/a.baseline - 1)).slice(0, 12);

function card(h) {
  const r = inv[h]; if (!r || !r[CONV]) return null;
  const os = (byHash[h] || []).slice(0, 14).map(o => `- ${o.facet}=${o.value} [${o.source||"?"}]: ${String(o.evidence).slice(0,100)}`).join("\n");
  let m = `spend ₹${Math.round(r.spend).toLocaleString()} | ${CONV} ${r[CONV]} | cost/${UNIT} ₹${Math.round(r.spend/r[CONV]).toLocaleString()} | ctr ${(r.clicks/Math.max(r.impressions,1)*100).toFixed(2)}%`;
  if (r.mt === "video" && r.v3s) m += ` | hook ${(r.v3s/r.impressions*100).toFixed(0)}% hold ${(r.vp50/Math.max(r.vp25,1)*100).toFixed(0)}%`;
  return `[${h.slice(0,12)} | ${r.mt}] ${m}\n${os}`;
}

async function reason(p) {
  const key = `${p.facet}:${p.trait}`;
  const win = v3.within_effects[key], btw = v3.between_effects[key];
  const layer = win ? `CREATIVE-LEVEL causal estimate (within same campaign, controls applied): x${win.multiplier} on cost — ${win.multiplier < 1 ? "genuinely helps the ad itself" : win.multiplier > 1.05 ? "hurts at ad level" : "neutral at ad level"}.`
    : btw ? `CAMPAIGN-LEVEL only: x${btw.multiplier} as a creative+audience bundle. This trait defines whole campaigns — its effect CANNOT be separated from the audience it ships with. Any recommendation must be about campaign strategy, not ad tweaks.` : "no controlled estimate available.";
  const inRecipes = recipes.recipes.filter(r => r.recipe.includes(key)).slice(0, 3)
    .map(r => `${r.recipe.join(" + ")} = ₹${r.cost} (n=${r.n})`).join("; ") || "none";
  const hs = p.hashes.filter(h => inv[h] && inv[h][CONV]).sort((a, b) => (inv[a].spend/inv[a][CONV]) - (inv[b].spend/inv[b][CONV]));
  const top = hs.slice(0, 5).map(card).filter(Boolean).join("\n\n");
  const bot = hs.slice(-5).map(card).filter(Boolean).join("\n\n");
  const prompt = `You are a senior performance marketer writing one insight for the client (${BRAND}). Cost per ${UNIT}, LOWER better, account baseline ₹${p.baseline}.

PATTERN: ${key} | cohort cost ₹${p.cpl} vs baseline ₹${p.baseline} | n=${p.n} creatives | ${Math.round(p.spend_share*100)}% of spend | CI ${JSON.stringify(p.ci90)}

TWO-LAYER EVIDENCE (this is the important part):
- Raw cohort effect (forecasting layer): x${(p.cpl/p.baseline).toFixed(2)} — how such creatives perform AS DEPLOYED, campaign choice included.
- ${layer}
- Proven combinations containing it: ${inRecipes}

BEST creatives carrying it:\n${top}\n\nWORST creatives carrying the same trait:\n${bot}

Rules:
- If the two layers AGREE, say so — the finding is robust at both ad and campaign level.
- If they DISAGREE (cohort says win but ad-level says neutral/hurt), the honest read is: campaigns built this way win, but changing an existing ad won't — say which lever (campaign strategy vs ad content) the client should pull.
- Weight evidence visual > overlay > cta > ad copy. Quote verbatim. Never restate the label as the reason.
- Diagnostic vocabulary (use when metrics fit): high CPM + high CTR = expensive audience, not bad creative; low CPM + low CTR = messaging misalignment; video high-hook + low-hold = post-hook content weak; low-hook + high-hold = hook filters to the right audience. Low CPM also means the algorithm is rewarding the creative.
- Off-platform blame firewall: high CTR + low click-to-conversion = landing page or offer-page problem, NOT the creative — say so and do not write a creative fix for it.
- Scale rule: an ad spending 4x the peer median with somewhat worse cost-per-result can still be the real winner — never crown a tiny-spend ad on rate alone.
- Action guardrails for [MAKE THIS AD]: swapping a creative resets the ad learning phase (~7 days / 50 events) — recommend duplicating the ad and swapping on the copy, never an in-place swap; never recommend pausing ads younger than 7 days (Early to Judge).
- Action: ONE brief, explicitly labeled either [MAKE THIS AD] or [RESTRUCTURE CAMPAIGNS] depending on which layer supports it.
- Brief richness: a [MAKE THIS AD] action must be shootable next week — give subject, setting, on-screen text (verbatim suggestion), offer treatment, and the first-3-seconds moment. A [RESTRUCTURE CAMPAIGNS] action must name what to launch/pause/split, the audience or objective change, and what metric proves it worked within 14 days.
Return JSON: {"claim":"...","layer_agreement":"agree|disagree|campaign-only","mechanism":"...","proof":[{"hash":"...","quote":"...","metric":"..."}],"action_type":"MAKE THIS AD|RESTRUCTURE CAMPAIGNS","action":"...","caveats":["..."]}`;
  const r = await fetch(BASE + "/chat/completions", {
    method: "POST", headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "gemini/gemini-2.5-flash", temperature: 0, response_format: { type: "json_object" }, messages: [{ role: "user", content: prompt }] }),
    signal: AbortSignal.timeout(120000),
  });
  const j = await r.json();
  if (!j.choices) throw new Error(JSON.stringify(j).slice(0, 120));
  return JSON.parse(j.choices[0].message.content.replace(/^```json\s*|```\s*$/g, ""));
}

const out = {};
for (let i = 0; i < conf.length; i += 6) {
  await Promise.all(conf.slice(i, i + 6).map(async p => {
    const k = `${p.facet}:${p.trait}`;
    try { out[k] = { pattern: {cpl: p.cpl, baseline: p.baseline, n: p.n}, ...(await reason(p)) }; console.log("ok", k, "->", out[k].layer_agreement, "/", out[k].action_type); }
    catch (e) { console.error("FAIL", k, e.message.slice(0, 80)); }
  }));
}
fs.writeFileSync(`${BRAND}/results/insights_v3.json`, JSON.stringify(out, null, 1));
console.log("done", Object.keys(out).length);
