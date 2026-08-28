# Operating manual for agents

You are an agent (Claude Code, or any coding agent) that has cloned this repo to run
creative entity extraction and analysis for an ad account. This file is your runbook.
Read `README.md` for what the system is; read this for how to drive it.

## Ground rules

- **Secrets**: never hardcode or print them. Every command that needs credentials is run
  through the operator's secret manager (e.g. `doppler run --project <p> --config <c> -- <cmd>`).
  `config.yaml` names the env vars; `.env.example` lists them.
- **Spend**: extraction calls a paid LLM. Announce estimated cost before a batch
  (`prompts/PROMPT_DESIGN.md` has reference numbers) and get operator confirmation for
  full-account runs. Sample/test runs (≤10 creatives) are fine without asking.
- **Data**: brand data lives under `brands/<name>/` which is gitignored. Never commit
  inventories, observations, media, or results.
- **Databases**: reads are fine. Any write to a shared table (e.g. loading entities)
  gets announced first. `extracted_entities_v2` is versioned (ReplacingMergeTree) —
  to undo a load you load the PREVIOUS state back, you never delete.

## Onboarding a new brand (the full flow)

### 0. Create the brand workspace
```
brands/<name>/
  brand.yaml          # copy from brands/example/brand.yaml, fill in
  focus.md            # copy from brands/example/focus.md — what the team wants captured (step 2b)
  raw/                # inventories, observations, canonical
  results/            # analysis outputs
```

### 1. Discover
Pull the account's shape from the warehouse (date range, spend, media mix, unique
creatives, KPI/conversion keys, campaign-name conventions, existing entity coverage).
Watch for: empty `hash` columns on fresh fetches (key by ad_id and keep a
url→ad_ids map), conversion-event variants that double-count (check overlap before
summing), objective mixes that need per-objective KPIs.

Then do outside market research on the brand itself — business model, who pays, what
user reviews complain about. Objections in reviews are usually the ad account's main
persuasion levers, and they belong in the prompt preamble.

### 2. Build the inventory
One JSONL row per unique creative: `{"hash", "u" (media url), "ad_copy" (json string),
"spend", ...metrics}`. Dedupe by media URL. Gate by spend (default ≥ the
`defaults.spend_gate` in config.yaml) — cover ~95%+ of spend with the fewest creatives.

### 2b. Agree the FOCUS BRIEF with the brand team (do not skip)
Before writing the prompt, ask what the team actually wants to learn from their
creatives — the decisions they'll make, the attributes they already track by hand, the
arguments they can't settle, and anything they must not infer. Record it in
`brands/<name>/focus.md` and append it to the prompt as a `FOCUS:` block; the prompt
treats those attributes as REQUIRED for every creative.

*Why this is its own step: a review round once flagged a missing casting attribute that
nobody had asked about upfront — an entire extraction pass had to be re-run. Eliciting
focus costs one conversation; discovering it costs a re-run.*

### 3. Design the extraction prompt
Follow `prompts/PROMPT_DESIGN.md` — the iteration loop there is mandatory, especially:
look at real samples BEFORE writing, test on knowns, fix the prompt not the output.
Store the final prompt as `prompts/<vertical>.txt` (commit it — prompts are code).

### 4. Extract
```
# images (OpenAI-schema proxy)
doppler run ... -- node extraction/extract_images.mjs brands/<name>/raw/inventory.jsonl \
    brands/<name>/raw/obs.json prompts/<vertical>.txt

# videos (Bifrost GenAI, native video watch; resumes automatically via .progress.jsonl)
doppler run ... -- node extraction/extract_videos.mjs brands/<name>/raw/videos.jsonl \
    brands/<name>/raw/obs_vid.json prompts/<vertical>.txt
```
Verify: 0 errors, average observations/creative in the prompt's stated range, facet
coverage table looks sane (core facets ≈ 100%).

### 4b. Video beat timeline (separate call — do NOT bundle with entities)
```
doppler run ... -- node extraction/extract_timeline_vid.mjs videos.jsonl tl.json prompts/<vertical>-timeline.txt
python3 analysis/timeline_analysis.py     # joins beats to Meta's video_p25/p50/p75/p100 quartiles
```
Returns `{duration, beats:[{t0,t1,role,says,says_en,text,text_en,shows}]}` — a contiguous
0→end breakdown with a fixed `role` vocabulary (hook/problem/introduce-app/value-prop/demo/
social-proof/price/objection-handling/invitation/cta/end-card). The runner validates
contiguity + t0=0 and retries on failure.

*Keep it a separate LLM call.* Bundling timeline into the entity prompt degraded both and cost
5x the prompt tokens (21.9k vs 4.6k); split, it ran 100/100 clean.
*JSON safety:* translations go in dedicated `says_en`/`text_en` fields — a parenthesised
translation inside `says` produces unescaped quotes that break the whole array.

### 5. Canonicalize
Merge obs files, lowercase/strip values, then (optional but recommended at scale) run a
dictionary pass to merge synonyms and roll values into concepts. Keep per-facet calls
with top-N value caps — one-shot dictionary calls 504 at scale.

### 6. Analyze
```
python3 analysis/patterns.py brands/<name> --kpi <conversions_field>   # cohorts + CIs + verdicts
python3 analysis/discriminative.py brands/<name>                       # top-vs-bottom tiers
python3 analysis/engine_v3.py brands/<name>                            # causal within/between campaign
python3 analysis/recipes.py brands/<name>                              # winning combinations
python3 analysis/backtest_strict_launch.py brands/<name>               # honesty gate — run it
python3 analysis/trend_lifecycle.py brands/<name>                      # month-by-month drift
python3 analysis/tail_hunt.py brands/<name>                            # cheap-in-small-tests, unscaled
```
(Some stages expect `raw/daily.jsonl`, `raw/ctx_dim.jsonl`, `raw/campaign_context.json` —
see each script's header for its input contract.)

### 7. Reasoning + enforcement (LLM writes insights, validator keeps it honest)
```
doppler run ... -- node enforcement/reasoning_v3.mjs brands/<name>
python3 enforcement/validate_insights.py brands/<name>      # proof hashes must exist; quotes verbatim-matched
doppler run ... -- node enforcement/repair_insights.mjs brands/<name>
python3 enforcement/validate_insights.py brands/<name>      # re-validate; DROP what cannot be repaired
```
Raw LLM insight generations fabricate evidence ~30–60% of the time. Never ship an
insight that failed validation.

### 8. Review + load
Build a review page for humans (thumbnails + per-creative observations with evidence —
see `explorers/`), collect feedback, fold it into the prompt (yes, this loops back to
step 3). When approved, load entities for downstream consumers:
```
doppler run ... -- python3 loaders/load_entities_ch.py brands/<name>/raw/obs.json <brand_id> \
    --aliases prompts/aliases/<vertical>.json --timeline brands/<name>/raw/tl.json
```
Writes one row per hash: scalar facets as strings, multi-value facets as arrays,
`_observations` (verbatim evidence) and `_timeline` (beats) as payload keys.

### 9. Wire the brand into Copilot (three steps, all brand-scoped — other brands untouched)
Copilot's group-by / ranking paths explode array-valued attributes (copilot PR
`creative-entities-v2`); `view` returns the full row including `_observations`/`_timeline`.
1. **Register the facets** so the agent knows they exist — Copilot reads attribute names
   from the brand's Mongo `metrics.tags` doc, nothing else:
   `MONGO_URI=... python3 loaders/set_copilot_entities.py <brand_id> prompts/facets/<vertical>.json --media video`
   Keep `prompts/facets/<vertical>.json` in sync with the prompt (one-line meaning per facet).
2. **Install the brand skill** — upload `copilot/skills/creative_entities_analysis.md` to the
   brand's vault at `skills/` (`POST /api/v1/vault/<brand_id>/upload`, `folder_path=skills`).
   Brand-authored skills are listed in the system prompt under "This brand's own skills"
   and take precedence over the shipped FLOW B for that brand only.
3. Smoke-test with 3 questions: a group-by on a multi-value facet (`value_prop`), an
   evidence question ("show me the line where the presenter says…"), and a
   within-language comparison. All three must succeed before handing over.

## Known pitfalls (all previously hit — don't rediscover them)

- Silent stalls: extraction sockets can hang forever without a timeout — both runners
  now abort per-request (config.yaml timeouts). A run with rising wall-time but flat
  CPU and no progress output is stalled; kill and rerun (videos resume).
- `'X' AS brand_id` alias in a ClickHouse INSERT...SELECT shadows the WHERE filter on
  the same column → 0 rows. Use the positional constant, no alias.
- ReplacingMergeTree counts look "wrong" pre-merge — always compare with `FINAL`.
- Progress dots are buffered when output is piped — silence ≠ stall; check CPU time.
- Percent buckets with overlapping boundaries split identical values — state bucket
  edges inclusively.
- Two offers on one banner: the louder one suppresses the other unless the prompt
  explicitly demands ALL distinct offers.
- Video retention: `video_play_actions` counts feed AUTOPLAY starts (scroll-pasts included),
  so any ratio against it looks catastrophic and means little. Compare p25→p50→p75→p100
  against each other, never against plays.
- ALWAYS run a within-language (or within-segment) cut before reporting a pooled creative
  finding. A real example: "ask lands early = ₹48 vs ₹76 CPI" pooled, but within language it
  REVERSED in 4 of 5 languages — pure Simpson's paradox from language mix. Pooled cuts across
  a multi-language account are confounded by auction price differences per language.
