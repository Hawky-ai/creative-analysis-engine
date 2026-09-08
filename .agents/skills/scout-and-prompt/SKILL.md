---
name: scout-and-prompt
description: >-
  Read a sample of the brand's real creatives open-endedly, then design, test and gate the
  extraction prompt for them.
  Use when a run's scout, prompt, feedback or coverage_audit step is pending, when someone asks
  to write or fix an extraction prompt, or when a review round says the entities missed something.
  This is the judgment half of the flow; the mechanical half is extract-and-load.
user-invocable: true
---

# scout-and-prompt

Everything downstream is arithmetic on what this prompt asks for. A facet that is not in the
prompt does not exist in the warehouse, and no amount of later querying recovers it. This step
is why an agent runs this repo instead of a cron job.

Read `prompts/PROMPT_DESIGN.md` before writing a line. It is the methodology; this skill is the
order of operations.

## 1. Scout — watch before you write

Send `scope.scout_sample` creatives through a deliberately **open-ended** prompt: no facet list,
no schema, no vocabulary. Ask what is in the creative and let the model describe it freely.
Spread the sample across language, spend band, media type, and launch date — a sample drawn only
from top spenders describes the winners' formula, not the account.

Then read the outputs yourself. You are looking for:

- what varies between creatives, since only variation can ever explain performance
- what is constant, since a facet that is the same everywhere is dead weight in every query
- devices you would never have predicted — the gameplay strip, the reaction inset, the
  screen-recorded chat

Include the brand's failures in the sample if the account has rejected or paused creatives.
They differ from the winners in exactly the ways worth naming.

## 2. Design the prompt

Structure, in this order: a preamble that says what kind of product this is and what a viewer is
being asked to do, then the facet list, then the evidence and output rules.

Facets come in two kinds and you must be deliberate about which:

- **Closed** — a fixed enum. Buys comparability: every creative answers on the same scale, so a
  group-by means something. Use it where the answer space is genuinely bounded.
- **Open** — vocabulary emerges from the creatives. Buys discovery, costs comparability. Use it
  where enumerating the answers up front would be guessing.

Every observation carries `{facet, value, evidence, source}`. The evidence is a verbatim quote
with timing for video, and it is what makes an extraction auditable by a human in seconds
instead of trusted on faith. Never let a facet ship without it.

Always include the `notable_device` escape hatch: anything striking that no facet covers. It is
the only channel through which the prompt can tell you it is out of date.

**The rule that has already cost a full re-extraction:** describe the CATEGORY, never prescribe
the current product. Naming today's hero SKU, ingredient or claim makes every creative "confirm"
what you wrote and silently mislabels anything new. The test, before you ship the prompt: *if
this brand relaunched with a completely different product tomorrow, would this prompt quietly
mislabel it?* If yes, rewrite it. The long version is the last section of `PROMPT_DESIGN.md`.

Append the operator's focus brief verbatim as a `FOCUS:` block; those attributes are required
output for every creative.

Videos additionally get a **separate** beat-timeline prompt, `prompts/<vertical>-timeline.txt`.
Keep it separate. Bundling the timeline into the entity prompt degraded both readings and cost
5x the prompt tokens; split, the same run went 100/100 clean.

## 3. Feedback loop — the part people skip

Re-run the prompt on the same sample and audit the output against the creatives:

- Is every core facet answered on close to 100% of creatives? A facet that is often absent is
  either badly worded or does not apply to this account.
- Is one idea fragmenting across many near-identical values? On one brand `cta` came back with
  21 distinct values that were really 5. Tighten the wording; do not clean the output.
- Did the model invent a value it could not have seen? Check the evidence quote against the
  creative.

**Fix the prompt, never the output.** A hand-corrected extraction is a lie that scales, and the
next batch reproduces the original error.

Loop until an audit round finds nothing. Two or three rounds is normal.

## 4. Coverage audit — a gate, not a suggestion

```
python3 analysis/coverage_audit.py brands/<name>/raw/scout_obs.json
```

It flags creative devices that recur in the prose descriptions but exist in no facet value, and
exits non-zero when it finds any. Each flag is a missing facet: fix the prompt and re-extract
before the review round, not after.

Know its limit, and say so to the operator rather than implying more safety than exists: it
matches a hardcoded word list, so it reliably catches the last surprise and not necessarily the
next one. Two habits close the rest of the gap — run it on every incremental batch, not only the
first, and watch what keeps landing in `notable_device`. A value that recurs across a batch is
the schema telling you it has fallen behind the creative, and it should be promoted to a real
facet.

## 5. Ship the prompt

Prompts are code: commit `prompts/<vertical>.txt`, `prompts/<vertical>-timeline.txt` and
`prompts/facets/<vertical>.json` (one line of plain meaning per facet, used to register the
facets later — keep it in sync with the prompt or the UI shows attributes nobody can interpret).

Brand data stays out of the repo; the prompt belongs in it.

Mark the steps settled in `run.yaml`, tell the operator what the prompt captures and what it
deliberately does not, then load **extract-and-load**.
