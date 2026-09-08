---
name: scout-and-prompt
description: >-
  Watch a sample of the brand's real creatives with no schema, then write, test and check the
  extraction prompt.
  Use when a run's scout, prompt, feedback or coverage_audit step is still pending, when
  someone asks to write or fix an extraction prompt, or when a review says the entities
  missed something.
  This is the part that needs judgment. extract-and-load is the mechanical part.
user-invocable: true
---

# scout-and-prompt

Everything after this is just maths on whatever the prompt asked for. If a facet is not in the
prompt, it does not exist in the warehouse, and no query later will get it back. This is why an
agent runs this repo instead of a cron job.

Read `prompts/PROMPT_DESIGN.md` before writing anything. That file is the method. This one is
the order you do it in.

## 1. Scout — watch before you write

Send `scope.scout_sample` creatives through a prompt with **no facet list, no schema, no
vocabulary**. Just ask what is in the creative and let the model describe it.

Spread the sample across languages, spend levels, media types and launch dates. A sample of
only the top spenders tells you what the winners do, not what the account does.

Then read the outputs yourself. You are looking for:

- what changes between creatives — only things that vary can ever explain performance
- what is the same in all of them — a facet that never changes is dead weight in every query
- things you would not have guessed: a gameplay strip along the bottom, a reaction inset, a
  screen recording of a chat

If the account has rejected or paused creatives, put some in the sample. They fail in exactly
the ways worth naming.

## 2. Write the prompt

Order: a short preamble saying what kind of product this is and what the viewer is being asked
to do, then the facet list, then the rules for evidence and output.

Two kinds of facet, and pick on purpose:

- **Closed** — a fixed list of allowed answers. Every creative answers on the same scale, so
  grouping by it means something. Use it when the possible answers really are limited.
- **Open** — the model answers in its own words. You find things you did not expect, but the
  answers are harder to compare. Use it when writing the list up front would be guessing.

Every observation carries `{facet, value, evidence, source}`. The evidence is the exact quote,
with a timestamp for video. That is what lets a human check an extraction in seconds instead
of just trusting it. No facet ships without it.

Always include `notable_device`: anything striking that no facet covers. It is the only way the
prompt can tell you it has gone out of date.

**The rule that already cost a full re-run:** describe the *kind* of product, never today's
specific one. Name the current hero product, ingredient or claim and every creative will
"confirm" what you wrote, while anything new gets labelled wrong. Test before shipping: *if
this brand launched a completely different product tomorrow, would this prompt label it wrong?*
If yes, rewrite. Long version is at the end of `PROMPT_DESIGN.md`.

Paste what the team said into the prompt as a `FOCUS:` block, word for word. Those are required
for every creative.

Videos also get a **separate** prompt for the beat timeline, `prompts/<vertical>-timeline.txt`.
Keep it separate. Putting the timeline in the entity prompt made both worse and cost 5x the
tokens.

## 3. Test it — the part people skip

Run the prompt on the same sample again and check the output against the creatives:

- Is every important facet answered on nearly every creative? One that is often blank is
  either badly worded or does not apply here.
- Is one idea split across lots of near-identical answers? On one brand `cta` came back with
  21 values that were really 5. Reword the prompt; do not clean up the output.
- Did the model make something up? Check the evidence quote against the creative.

**Fix the prompt, never the output.** A hand-corrected extraction is a lie that scales, and the
next batch makes the same mistake again.

Repeat until a round finds nothing. Two or three rounds is normal.

## 4. Coverage check — this one blocks

```
python3 analysis/coverage_audit.py brands/<name>/raw/scout_obs.json
```

It looks for things that keep showing up in the written descriptions but have no facet, and
exits with an error if it finds any. Each one is a missing facet: fix the prompt and re-extract
before the review, not after.

Be straight with the operator about what it does and does not do. It matches a fixed list of
words, so it catches last time's surprise, not necessarily next time's. Two habits cover the
rest: run it on every batch, not just the first, and read what keeps landing in
`notable_device`. If the same thing shows up again and again, the prompt is behind the
creatives and that thing should become a real facet.

## 5. Ship it

Prompts are code. Commit `prompts/<vertical>.txt`, `prompts/<vertical>-timeline.txt` and
`prompts/facets/<vertical>.json` (one plain-English line per facet — this is what gets
registered later, so keep it matching the prompt or the UI shows names nobody can read).

Brand data stays out of the repo. The prompt goes in it.

Set the steps in `run.yaml`, tell the operator what the prompt captures and what it does not,
then load **extract-and-load**.
