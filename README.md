# creative-analysis-engine

Turn an ad account's creatives into **queryable, evidence-backed entities** — then into
statistically honest performance patterns. A multimodal LLM watches every image and
video, writes atomic observations (`{facet, value, evidence, source}`), and a chain of
deterministic analysis stages turns those into cohort verdicts, causal effects, winning
recipes, and backtested trends. An enforcement layer validates every LLM-written insight
against the stored evidence, so nothing fabricated ships.

Proven across seven accounts and five verticals — ed-tech lead-gen video, FMCG
retail-media banners, app-install vernacular video, haircare awareness video, and social
calling apps. The backtest on the strongest account held on 6/6 launch-date cutoffs
(picked creatives ≈ 60% cheaper than launching blind).

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/Hawky-ai/creative-analysis-engine/main/install.sh | sh
cd creative-analysis-engine && claude
```

`install.sh` clones the repo, checks the toolchain (`node`, `python3`, `ffmpeg`, `curl`) and
seeds `.env`. It installs nothing globally, touches nothing outside the clone, and re-running it
just updates an existing clone. Cloning by hand does the same job.

Launching a coding agent inside the clone is the whole interface. There is no CLI to learn and
no config to fill in first: the agent reads `AGENTS.md`, runs a session digest, and with no
brand run present it loads the `onboard-brand` skill and **interviews you** — the brand, where
the entities get written, the scope, the credentials, and what the team actually wants to learn.
Nothing touches a database or a paid model until it has those answers.

## The guided flow

The flow splits at its real seam: two of the steps are arithmetic, and two need judgment. That
is why an agent drives this repo instead of a cron job.

| Skill | Owns | Nature |
|---|---|---|
| `onboard-brand` | intake interview, workspace, discovery, creative inventory | mechanical |
| `scout-and-prompt` | scout sample, prompt design, feedback loop, coverage gate | **judgment** |
| `extract-and-load` | full extraction, verification, warehouse load, facet registration | mechanical |

**Scout before you write.** A sample of real creatives goes through a deliberately open-ended
prompt — no facet list, no schema, no vocabulary — spread across language, spend band and
launch date. Reading those outputs is what tells you which facets deserve to exist. It is also
what stops the last brand's schema being copied onto this one, which is the most expensive
mistake this flow can make.

**Then the feedback loop.** Re-run on the same sample, audit against the creatives, and fix the
*prompt* — never the output. A hand-corrected extraction is a lie that scales, and the next
batch reproduces the original error. On one brand this collapsed a `cta` facet from 21
near-identical values to the 5 that were really there.

**Then the gate.** `analysis/coverage_audit.py` flags creative devices that recur in the prose
but exist in no facet value, and exits non-zero when it finds any. Its limit is stated plainly
in the skill rather than papered over: it matches a hardcoded word list, so it reliably catches
the *last* surprise and not necessarily the next one. Running it on every incremental batch and
watching what keeps landing in `notable_device` is what closes the rest of the gap.

Run state lives in `brands/<name>/run.yaml`, so a lost session resumes at the step it stopped on
instead of repeating a paid one. `bin/cae-session-start.sh` reads it and reports where every
brand is parked.

The guided path covers entity extraction end to end. The analysis and enforcement stages below
are driven by hand from `AGENTS.md`.

## How it works

```
inventory (warehouse) ──► extraction (LLM watches media) ──► canonical observations
                                                                    │
                       ┌────────────────────────────────────────────┤
                       ▼                                            ▼
              analysis stages (deterministic)              per-creative entities
   patterns · discriminative tiers · causal engine         (loaders/ → warehouse,
   recipes · strict backtest · lifecycle · tail hunt        for downstream agents)
                       │
                       ▼
        reasoning (LLM writes insights)
                       │
                       ▼
        ENFORCEMENT (validate → repair → drop)   ◄── the honesty gate
```

**The observation contract** is the core idea: facets are fixed questions per vertical,
values are open-vocabulary answers, and every observation carries verbatim evidence
(with timing, for video) and a source (headline / pack text / spoken / subtitle /
on-screen UI). That makes extractions comparable across thousands of creatives AND
auditable by a human in seconds.

Videos get a **second, separate** call for the beat timeline — a contiguous 0→end breakdown
with a closed `role` vocabulary. Keep it separate: bundling it into the entity prompt degraded
both readings and cost 5× the prompt tokens.

## Repo layout

| Path | What |
|---|---|
| `install.sh` | One-command install: clone, toolchain check, `.env` seed |
| `AGENTS.md` | **The runbook.** If you are an agent operating this repo, start there (`CLAUDE.md` points at it) |
| `.agents/skills/` | The guided flow: `onboard-brand`, `scout-and-prompt`, `extract-and-load`. `.claude/skills` symlinks here |
| `.claude/settings.json` | Runs the session digest on SessionStart |
| `bin/` | `cae-session-start.sh` (readiness + where each run is parked), `cae-discover.sh` (account shape from the warehouse) |
| `config.yaml` | Models, endpoints (as env-var names), concurrency, timeouts, analysis defaults — the only file to edit when switching gateways/models |
| `.env.example` | Every env var the engine needs; inject via your secret manager |
| `prompts/` | The extraction prompt library, one per vertical + `PROMPT_DESIGN.md` (the methodology — read before writing any new prompt) |
| `extraction/` | `extract_images.mjs` (OpenAI-schema proxy), `extract_videos.mjs` and `extract_timeline_vid.mjs` (GenAI schema, auto-resume), `media-inline.mjs` (fetch → downscale → inline bytes) |
| `analysis/` | `coverage_audit.py` (the gate) plus the deterministic stages: `patterns.py`, `discriminative.py`, `engine_v3.py`, `recipes.py`, `backtest_strict_launch.py`, `trend_lifecycle.py`, `tail_hunt.py`, `matched_pairs.py`, `first3s.py`, `fatigue.py` |
| `enforcement/` | `reasoning_v3.mjs` → `validate_insights.py` → `repair_insights.mjs`: LLM insights are checked against stored evidence (proof hashes must exist, quotes must match verbatim); unrepairable ones are dropped |
| `loaders/` | `load_entities_ch.py` (entities → ClickHouse), `set_copilot_entities.py` (facet registry), `sync_rejected_ads.py` |
| `brands/` | Per-brand workspaces (gitignored — data never enters the repo). `brands/example/` holds the `run.yaml`, `brand.yaml` and `focus.md` templates |

## Configuration

All model/endpoint choices live in `config.yaml`. Secrets never do — each `*_env` key
names an environment variable, injected at runtime:

```yaml
llm_proxy:                      # images + reasoning (OpenAI chat/completions schema)
  base_url_env: LLM_BASE_URL
  api_key_env: LLM_API_KEY
bifrost:                        # videos (Gemini-native generateContent)
  genai_base_url_env: BIFROST_GENAI_BASE_URL
  api_key_env: BIFROST_API_KEY
extraction:
  image_model: gemini/gemini-3.8-flash
  video_model: gemini-3.8-flash
  ...
```

Any OpenAI-compatible gateway works for images and reasoning; video goes through a GenAI-schema
endpoint for native video watching.

**Media is sent as inline bytes, not as a URL.** The newer Gemini models reject an external CDN
`fileUri`, and the failure surfaces as a misleading `403 The caller does not have permission`
that looks exactly like an auth problem and is not. `extraction/media-inline.mjs` fetches the
media, downscales video to 480p/2fps with ffmpeg, and sends `inline_data`. The model samples
frames at a low rate anyway, so the transcode costs nothing in quality — verified on a 19MB
creative: 1.1MB transcoded gave the same prompt-token count and the same reading, verbatim
on-screen text included. This is why `ffmpeg` is a real dependency.

## Principles

1. **Evidence or it didn't happen.** Every value carries a verbatim quote or precise
   visual description; every LLM-written insight is machine-validated against that
   evidence before it ships.
2. **Fixed questions, open answers.** Comparability comes from the facet backbone;
   discovery comes from open vocabulary values.
3. **Describe the category, never prescribe the findings.** A prompt that names today's hero
   product or its canonical claims makes every creative "confirm" what you wrote, and silently
   mislabels anything new. The test before shipping a prompt: *if this brand relaunched with a
   completely different product tomorrow, would this prompt quietly mislabel it?* This one cost
   a full re-extraction before it became a rule.
4. **The backtest is the honesty gate.** A pattern that doesn't survive
   train-on-ended / test-on-launched-after splits is reported as such — this engine has
   publicly retracted its own headline result once, and that protocol is now built in.
5. **Prompts are code.** Versioned, reviewed, changed via PR with the failing creative
   attached. Feedback loop: reviewer finding → issue → prompt clause naming the failure
   → re-test on knowns.
6. **Analysis is deterministic.** LLMs extract and narrate; statistics decide. Bootstrap
   CIs for verdicts, causal separation for "the ad vs the campaign it sat in".

## Driving it by hand

Everything the skills do can be run directly. Full brand onboarding — discovery, prompt design,
extraction, analysis, enforcement, review, loading — is step by step in
[`AGENTS.md`](AGENTS.md), which also carries the accumulated pitfalls. The prompt-design
checklist, every rule earned from a real observed failure, is in
[`prompts/PROMPT_DESIGN.md`](prompts/PROMPT_DESIGN.md).

```bash
# what shape is this account in?
doppler run -- bin/cae-discover.sh <brand_id> [date_from] [date_to]

# smoke test on a handful of creatives
doppler run -- node extraction/extract_images.mjs brands/<name>/raw/sample.jsonl \
    brands/<name>/raw/sample_obs.json prompts/retail-media-banner.txt
```

## Contributing / feedback

File an issue with: the creative (hash + media URL), what the extraction said, what it
should have said. Prompt fixes reference the issue and re-test against the sample set
before merging. See `prompts/PROMPT_DESIGN.md` §"The iteration loop".
