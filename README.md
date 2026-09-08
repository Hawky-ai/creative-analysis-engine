# creative-analysis-engine

Turns an ad account's creatives into data you can query. A model watches every image and
video and writes down what is in them — one fact at a time, each with the exact quote or
detail it came from. After that you can group, compare and rank creatives by what they
actually contain, instead of by gut feel.

There is a second half that turns those facts into performance findings, with a check that
throws out any claim whose evidence does not hold up.

Used on seven accounts across five kinds of product: ed-tech lead-gen video, FMCG banners,
app-install video in Indian languages, haircare video, and social calling apps. On the
strongest account, creatives it picked were about 60% cheaper than launching blind, and that
held on all 6 date cutoffs it was tested against.

## Quick start

```bash
gh repo clone Hawky-ai/creative-analysis-engine
cd creative-analysis-engine && ./install.sh && claude
```

This repo is **private**, so you cannot pipe it from `raw.githubusercontent.com` — that gives a
404 to anyone without a token, which looks like the file is missing when really you just are not
logged in. `gh repo clone` uses the login the GitHub CLI already has. Run `gh auth login` first
if you have never used it here.

`install.sh` checks you have `node`, `python3`, `ffmpeg` and `curl`, and leaves you a `.env`
with the variable names in it. It does not ask you for credentials — the agent tells you what
this is and which values `.env` needs on the first session, and you fill them in yourself.
`.env` is gitignored, so it never gets committed. If you use doppler, leave `.env` alone and
just tell the agent which project and config.

It installs nothing globally and touches nothing outside the clone.

## Updating

From inside the folder:

```bash
./install.sh
```

It pulls the latest and re-checks your tools. If the clone has lost its `origin` remote —
`git pull` failing with *"'origin' does not appear to be a git repository"* — it puts the remote
back rather than leaving you to work out what broke.

Opening a coding agent inside the clone is the whole interface. Nothing to learn, no config to
fill in first: the agent reads `AGENTS.md`, prints what it can see, and if there is no run yet
it loads the `onboard-brand` skill and **asks you** — which brand, what scope, which
credentials, and what the team wants to learn from this. It does not touch a database or spend
money on a model until it has those answers.

## The guided flow

Some steps are just maths. Two of them need someone to think. That is why an agent runs this
and not a cron job.

| Skill | Owns | Nature |
|---|---|---|
| `onboard-brand` | asks what to analyse, sets up the folder, pulls the account's numbers, builds the creative list | mechanical |
| `scout-and-prompt` | watches a sample, writes the prompt, tests it, checks nothing is missing | **needs judgment** |
| `extract-and-load` | runs it on everything, checks it, writes it to ClickHouse and Mongo | mechanical |

**Watch before you write.** About 15 real creatives go through a prompt with no facet list and
no schema at all — just "describe what is in this" — picked across languages, spend levels and
dates. Reading those is what tells you which attributes are worth having. It is also what stops
you copying the last brand's setup onto this one, which is the worst mistake you can make here.

**Then test the prompt.** Run it on the same sample again, compare against the creatives, and
fix the *prompt* — never the output. Correcting output by hand is a lie that scales, and the
next batch just repeats the mistake. On one brand this turned a `cta` attribute with 21
near-identical answers into the 5 that were really there.

**Then the check that blocks.** `analysis/coverage_audit.py` looks for things that keep showing
up in the descriptions but have no attribute, and fails if it finds any. It matches a fixed list
of words, so it catches last time's surprise and not necessarily next time's — the skill says so
rather than pretending otherwise. Running it on every batch, and reading what keeps landing in
`notable_device`, covers the rest.

Each run's state is in `brands/<name>/run.yaml`, so if the session dies you pick up at the step
it stopped on instead of paying for it twice. `bin/cae-session-start.sh` prints where every
brand is.

This path covers the extraction end to end. The analysis and enforcement stages further down
are run by hand from `AGENTS.md`.

## How it works

```
creative list ──────────► a model watches each one ──────► facts, with evidence
                                                                    │
                       ┌────────────────────────────────────────────┤
                       ▼                                            ▼
              analysis (numbers, no model)                 per-creative facts
   cohorts · top vs bottom · causal · winning combos       (loaders/ → ClickHouse,
   backtest · month-by-month · cheap-but-unscaled           for whatever reads it)
                       │
                       ▼
        a model writes the findings
                       │
                       ▼
        CHECK (validate → repair → drop)   ◄── throws out unproven claims
```

**The main idea:** the questions are fixed per kind of product, the answers are open, and every
answer comes with the exact evidence for it — the quote, when it was said, and where it came
from (headline, pack text, spoken, subtitle, on-screen). That makes thousands of creatives
comparable, and lets a human check any one of them in seconds.

Videos get a **second, separate** call that breaks the video into beats from start to finish.
Keep it separate — putting it in the same prompt made both worse and cost 5x the tokens.

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
| `analysis/` | `coverage_audit.py` (the check that blocks) plus the number-crunching stages: `patterns.py`, `discriminative.py`, `engine_v3.py`, `recipes.py`, `backtest_strict_launch.py`, `trend_lifecycle.py`, `tail_hunt.py`, `matched_pairs.py`, `first3s.py`, `fatigue.py` |
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

Any OpenAI-compatible gateway works for images. Video goes through a Gemini-native endpoint,
because that is what can actually watch a video.

**The media is uploaded, not linked.** The newer Gemini models refuse a CDN URL, and they say so
with a `403 The caller does not have permission` — which looks like a login problem and is not.
So `extraction/media-inline.mjs` downloads the file, shrinks video to 480p at 2 frames a second
with ffmpeg, and sends the bytes. The model only looks at a few frames a second anyway, so
shrinking it costs nothing: on a 19MB creative, the 1.1MB version used the same tokens and gave
the same reading, down to the exact on-screen text. That is why `ffmpeg` is actually needed.

## Principles

1. **Evidence or it didn't happen.** Every answer carries the exact quote or a precise
   description of what was on screen. Every finding the model writes is checked against that
   evidence before it ships.
2. **Fixed questions, open answers.** The fixed questions make creatives comparable. The open
   answers are how you find things you did not expect.
3. **Describe the kind of product, not today's product.** Name the current hero product or its
   usual claims and every creative will "confirm" what you wrote, while anything new gets
   labelled wrong. Test before shipping: *if this brand launched something completely different
   tomorrow, would this prompt label it wrong?* This cost a full re-run before it became a rule.
4. **The backtest decides.** A pattern that does not survive being trained on old creatives and
   tested on newer ones gets reported as not surviving. This engine has publicly taken back its
   own headline result once, and that check is now built in.
5. **Prompts are code.** Versioned, reviewed, changed through a PR with the creative that broke
   them attached.
6. **The model describes, the statistics decide.** The model extracts and narrates. Numbers
   decide what is real.

## Driving it by hand

Everything the skills do can be run directly. The whole thing, step by step, is in
[`AGENTS.md`](AGENTS.md), along with every mistake already made so you do not repeat them. The
prompt checklist — every rule there came from something that actually went wrong — is in
[`prompts/PROMPT_DESIGN.md`](prompts/PROMPT_DESIGN.md).

```bash
# what shape is this account in?
doppler run -- bin/cae-discover.sh <brand_id> [date_from] [date_to]

# smoke test on a handful of creatives
doppler run -- node extraction/extract_images.mjs brands/<name>/raw/sample.jsonl \
    brands/<name>/raw/sample_obs.json prompts/retail-media-banner.txt
```

## Contributing / feedback

Open an issue with the creative (hash and media URL), what the extraction said, and what it
should have said. Prompt fixes link the issue and get re-tested on the sample before merging.
See `prompts/PROMPT_DESIGN.md`.
