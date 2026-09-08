---
name: onboard-brand
description: >-
  Ask the operator what to analyse and set up a new brand run.
  Use when someone invokes /onboard-brand, asks to analyse a new brand's creatives, gives a
  brand id with no run.yaml for it, or when the session digest says "RUNS none".
  Covers the questions, the workspace, pulling the account's numbers, and building the list
  of creatives. Then hands off to scout-and-prompt.
user-invocable: true
---

# onboard-brand

You have a brand and nothing else. Ask for the rest. Do not copy answers from another brand
already in this repo — that is the most expensive mistake here.

## 1. Ask first

Ask these before touching a database. One message, numbered, then wait.

1. **Brand name and brand id.** The name becomes the folder `brands/<name>/`. The id is the
   brand whose creatives you read.
2. **Scope.** The whole account, a date range ("creatives launched in the last 15 days"), or
   one campaign. And: video only, image only, or both.
3. **Spend gate.** The lowest spend a creative needs before it is worth analysing. Zero is
   fine for a small or recent scope. On a big account, pick a number that covers about 95% of
   spend with as few creatives as possible.
4. **How are the credentials set up?** Either they are in `.env` already (`./install.sh --creds`
   puts them there), or they use doppler — in which case you need the project and config name.
   That is all you need to know. Never ask anyone to type a secret into the chat, and do not
   warn them about it either; the setup already handles it.
5. **What do they want to learn?** What will the team decide from this? What do they already
   track by hand in a sheet? What do they argue about with no data to settle it? Is there
   anything you must not guess at? `brands/example/focus.md` has the full list. Do not skip
   this — one brand had to be re-extracted from scratch because nobody asked.

Ask those five and nothing else. Do not add a list of decisions you are making, or explain the
prompt naming, or announce the scout size — none of that means anything to someone who has not
answered yet, and it makes a short set of questions look like a form.

**By default the entities go back to the same brand.** Mention it in one line so they can say
otherwise. Only if they ask for a **test brand** do you write somewhere else, and then you need
that test brand's id too. If they say "replace what is on the live brand" instead, make them say
it clearly and write it in the log — the old rows only come back from a backup you take
yourself.

Two things you decide quietly, once you have the answers, and only mention when it matters:

- **The prompt name.** After the kind of product, not the brand: `social-calling-app-video`,
  not `eloelo-video`, so the next brand selling the same kind of thing can reuse it.
- **How many creatives to watch first.** 15, unless the account is unusually mixed.

## 2. Set up the folder

```
mkdir -p brands/<name>/raw brands/<name>/results
cp brands/example/run.yaml brands/<name>/run.yaml
cp brands/example/focus.md brands/<name>/focus.md
```

Fill in `run.yaml` from the answers. Everything under `brands/` is gitignored, so brand data
never gets committed. Write what the team said into `focus.md` in their own words.

After every step, set that step in `run.yaml` and add a line to `log`. That file is all that
survives if the session dies. A step you did not record is a step someone runs twice.

## 3. Get the account's numbers

```
doppler run ... -- bin/cae-discover.sh <brand_id> [date_from] [date_to]
```

It prints the date range, spend, how many creatives, the media mix, the top campaigns, and how
much is already analysed.

Show the operator the numbers. If the creative count is far off what they expected, stop and
sort it out — it means the scope is wrong, and everything after this inherits that.

Then read up on the brand outside the warehouse: what the product is, who pays for it, what
users complain about in reviews. Those complaints are usually what the ads are arguing
against, so they belong in the prompt.

## 4. Build the list of creatives

One line of JSON per **creative**, not per ad: `{"hash", "u", "ad_copy", "spend", ...}`. Lots
of ads share one creative, and collapsing them is what keeps the model bill sane. Put videos
and images in separate files — they go through different extractors.

Then say the numbers out loud: how many creatives, what share of spend they cover, how many
ads collapsed into them. Two things that have gone wrong before:

- Some rows come back with an empty `hash`. Key those by ad_id and keep a url→ad_ids map.
- The account keeps getting fetched while you work. One brand went from 65 to 75 creatives
  mid-session, and the new ones carried about half the spend. Check the count again right
  before loading, not just here.

## 5. Hand off

Set `discover` and `inventory` in `run.yaml`, then load the **scout-and-prompt** skill. Do not
write the prompt here, and do not reuse another brand's prompt because the products look
similar. That is exactly what the next skill exists to stop.
