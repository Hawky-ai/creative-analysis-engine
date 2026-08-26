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
    [--aliases prompts/aliases/<vertical>.json]
```

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
