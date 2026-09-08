---
name: onboard-brand
description: >-
  Interview the operator and open a new brand run in this repo.
  Use when someone invokes /onboard, asks to analyse a new brand's creatives, names a brand id
  with no run.yaml behind it, or when the session-start digest reports "RUNS none".
  Owns the intake questions, the workspace layout, discovery, and the creative inventory.
  Hands off to scout-and-prompt once the inventory exists.
user-invocable: true
---

# onboard-brand

You have been handed a brand and nothing else. Everything you need to run comes out of one
conversation with the operator. Do not infer any of it from a previous brand in this repo —
copying a previous brand's assumptions is the single most expensive mistake this flow makes.

## 1. Interview first, act second

Ask these before touching a database. Ask them in one message, numbered, and wait. Do not
start discovery on partial answers; a wrong brand id burns a paid extraction run.

1. **Brand name and warehouse brand id.** The name becomes `brands/<name>/`. The id is what
   creatives are read from.
2. **Where do the entities get written?** Usually the same brand id. Often a separate *test*
   brand id, so production stays untouched while the team reviews. If they say "replace the
   existing entities on production", make them say it explicitly and record it in the log —
   the existing rows are only recoverable from a backup you take yourself.
3. **Scope.** Whole account, a date window ("creatives launched in the last 15 days"), or one
   campaign. Also: video only, image only, or both.
4. **Spend gate.** Minimum lifetime spend for a creative to enter analysis. Zero is a fine
   answer for a small or recent scope; on a large account, gate for ~95% of spend with the
   fewest creatives.
5. **Credentials.** Which doppler project and config, or how else the env vars in
   `.env.example` arrive. Never ask them to paste a secret into the chat.
6. **The focus brief.** What decisions will the team make from this? What do they already
   track by hand? What have they argued about internally with no data to settle it? What must
   never be inferred? `brands/example/focus.md` has the full question list — this is step 2b in
   `AGENTS.md` and skipping it has already cost one full re-extraction.

Two things you decide, not them, and say so:

- **The vertical name.** Name it after the CATEGORY, never the brand — `social-calling-app-video`,
  not `eloelo-video`. A second brand in the same category must be able to reuse the prompt.
- **The scout sample size**, unless they have a preference. Default 15.

## 2. Open the workspace

```
mkdir -p brands/<name>/raw brands/<name>/results
cp brands/example/run.yaml brands/<name>/run.yaml
cp brands/example/focus.md brands/<name>/focus.md
```

Fill `run.yaml` from the interview. Everything under `brands/` is gitignored — brand data
never enters the repo. Write the focus brief into `focus.md` in the team's own words.

From here on, after finishing any step, set that step's key in `run.yaml` and append a line to
`log`. That file is the only thing that survives a lost session; an unrecorded step is a step
that gets run twice.

## 3. Discover

Read the account's shape out of the warehouse before deciding anything: date range, spend,
media mix, unique creative count, campaigns, ad accounts, how many creatives already carry
entities. `bin/cae-discover.sh` runs the standard queries; read its header for what it assumes.

Report the numbers to the operator in a few lines. If the count is far off what they expected,
stop and reconcile it — a mismatch here means the scope filter is wrong, and everything
downstream inherits the error.

Then research the brand outside the warehouse: what the product is, who pays for it, what
user reviews complain about. Objections in reviews are usually the account's main persuasion
levers and they belong in the prompt preamble.

## 4. Build the inventory

One JSONL row per **unique creative**, not per ad: `{"hash", "u", "ad_copy", "spend", ...}`.
Many ads share one creative; deduping is what keeps the LLM bill honest. Split video and image
into separate files — they run through different extractors.

Then check the arithmetic out loud: unique creatives, share of scope spend covered, how many
ads collapsed into them. Two traps that have both bitten:

- Fresh fetches can carry an empty `hash`. Key by ad_id and keep a url→ad_ids map instead.
- The account keeps being fetched while you work. One brand went 65 → 75 creatives mid-session,
  with the new ones carrying ~48% of spend. Re-check the count against the warehouse right
  before you load, not only here.

## 5. Hand off

Mark `discover` and `inventory` settled in `run.yaml`, then load the **scout-and-prompt** skill.
Do not write an extraction prompt in this skill, and never reuse another brand's prompt because
the categories look similar — that is exactly the failure scout-and-prompt exists to prevent.
