# creative-analysis-engine

Turn an ad account's creatives into **queryable, evidence-backed entities** — then into
statistically honest performance patterns. A multimodal LLM watches every image and
video, writes atomic observations (`{facet, value, evidence, source}`), and a chain of
deterministic analysis stages turns those into cohort verdicts, causal effects, winning
recipes, and backtested trends. An enforcement layer validates every LLM-written insight
against the stored evidence, so nothing fabricated ships.

Proven on four real accounts across three verticals (ed-tech lead-gen video, FMCG
retail-media banners, app-install vernacular video); backtest on the strongest account
held on 6/6 launch-date cutoffs (picked creatives ≈ 60% cheaper than launching blind).

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

## Repo layout

| Path | What |
|---|---|
| `config.yaml` | Models, endpoints (as env-var names), concurrency, timeouts, analysis defaults — the only file to edit when switching gateways/models |
| `.env.example` | Every env var the engine needs; inject via your secret manager |
| `prompts/` | The extraction prompt library, one per vertical + `PROMPT_DESIGN.md` (the methodology — read before writing any new prompt) |
| `extraction/` | `extract_images.mjs` (OpenAI-schema proxy), `extract_videos.mjs` (Bifrost GenAI, native video watch, auto-resume) |
| `analysis/` | Deterministic stages: `patterns.py`, `discriminative.py`, `engine_v3.py` (causal within/between-campaign), `recipes.py`, `backtest_strict_launch.py`, `trend_lifecycle.py`, `tail_hunt.py`, `matched_pairs.py`, `first3s.py`, `fatigue.py` |
| `enforcement/` | `reasoning_v3.mjs` → `validate_insights.py` → `repair_insights.mjs`: LLM insights are checked against stored evidence (proof hashes must exist, quotes must match verbatim); unrepairable ones are dropped |
| `loaders/` | `load_entities_ch.py` — publish per-creative entities to ClickHouse for downstream consumers (e.g. a copilot's entity path) |
| `brands/` | Per-brand workspaces (gitignored — data never enters the repo). `brands/example/brand.yaml` is the template |
| `.agents/skills/` | The guided flow: `onboard-brand`, `scout-and-prompt`, `extract-and-load` (`.claude/skills` symlinks here) |
| `bin/` | `cae-session-start.sh` (session digest, wired as the SessionStart hook), `cae-discover.sh` (account shape) |
| `install.sh` | One-command install: clone, toolchain check, `.env` seed |
| `AGENTS.md` | **The runbook.** If you are an agent (Claude Code etc.) operating this repo, start there |

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/Hawky-ai/creative-analysis-engine/main/install.sh | sh
cd creative-analysis-engine && claude
```

`install.sh` clones the repo, checks the toolchain (`node`, `python3`, `ffmpeg`, `curl`) and
seeds `.env`. It installs nothing globally and touches nothing outside the clone; re-running it
updates an existing clone. Or clone by hand — it is the same thing:

```bash
git clone https://github.com/Hawky-ai/creative-analysis-engine && cd creative-analysis-engine
cp .env.example .env            # or use doppler/vault — never commit values
claude                          # the agent reads AGENTS.md and interviews you from there
```

There is nothing to install. The clone is the tool: opening it in a coding agent runs a
session digest, and with no brand run present the agent loads the `onboard-brand` skill and
asks for the brand, the scope, the credentials and the focus brief before touching anything.
Run state lives in `brands/<name>/run.yaml`, so a lost session resumes where it stopped.

To drive it by hand instead:

```bash
# edit config.yaml if your model ids / gateway differ

# smoke test on a handful of creatives:
doppler run -- node extraction/extract_images.mjs brands/<name>/raw/sample.jsonl \
    brands/<name>/raw/sample_obs.json prompts/retail-media-banner.txt
```

Full brand onboarding — discovery, prompt design, extraction, analysis, enforcement,
review, loading — is step-by-step in [`AGENTS.md`](AGENTS.md). The prompt-design
checklist (every rule earned from a real observed failure) is in
[`prompts/PROMPT_DESIGN.md`](prompts/PROMPT_DESIGN.md).

## Configuration

All model/endpoint choices live in `config.yaml`. Secrets never do — each `*_env` key
names an environment variable, injected at runtime:

```yaml
llm_proxy:                      # images + reasoning (OpenAI chat/completions schema)
  base_url_env: LLM_BASE_URL
  api_key_env: LLM_API_KEY
bifrost:                        # videos (Gemini-native generateContent, file-URI input)
  genai_base_url_env: BIFROST_GENAI_BASE_URL
  api_key_env: BIFROST_API_KEY
extraction:
  image_model: gemini/gemini-2.5-flash
  video_model: gemini-2.5-flash
  ...
```

Any OpenAI-compatible gateway works for images/reasoning; video needs a GenAI-schema
endpoint because native video watching requires file-URI input.

## Principles

1. **Evidence or it didn't happen.** Every value carries a verbatim quote or precise
   visual description; every LLM-written insight is machine-validated against that
   evidence before it ships.
2. **Fixed questions, open answers.** Comparability comes from the facet backbone;
   discovery comes from open vocabulary values.
3. **The backtest is the honesty gate.** A pattern that doesn't survive
   train-on-ended / test-on-launched-after splits is reported as such — this engine has
   publicly retracted its own headline result once, and that protocol is now built in.
4. **Prompts are code.** Versioned, reviewed, changed via PR with the failing creative
   attached. Feedback loop: reviewer finding → issue → prompt clause naming the failure
   → re-test on knowns.
5. **Analysis is deterministic.** LLMs extract and narrate; statistics decide. Bootstrap
   CIs for verdicts, causal separation for "the ad vs the campaign it sat in".

## Contributing / feedback

File an issue with: the creative (hash + media URL), what the extraction said, what it
should have said. Prompt fixes reference the issue and re-test against the sample set
before merging. See `prompts/PROMPT_DESIGN.md` §"The iteration loop".
