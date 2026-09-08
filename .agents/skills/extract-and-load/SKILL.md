---
name: extract-and-load
description: >-
  Run the full extraction over a brand's creatives, verify it, and publish the entities to the
  warehouse and the brand's facet registry.
  Use when a run's extract, timeline, verify, load_ch, register_facets or smoke step is pending,
  or when someone asks to re-run or re-load a brand that already has an approved prompt.
  Owns the spend confirmation, the load safety rules, and the post-load proof.
user-invocable: true
---

# extract-and-load

The mechanical half. It still has three places where being careless costs real money or real
data, and they are all called out below.

## 1. Confirm the spend before the batch

Extraction calls a paid model on every creative. Before a full run, tell the operator the
creative count, the rough cost, and roughly how long it will take, and wait for a yes. Sample
runs of ten or fewer need no permission.

## 2. Extract

```
# images — OpenAI-schema proxy
doppler run ... -- node extraction/extract_images.mjs brands/<name>/raw/images.jsonl \
    brands/<name>/raw/obs_img.json prompts/<vertical>.txt

# videos — Bifrost GenAI, native video watch, resumes from .progress.jsonl
doppler run ... -- node extraction/extract_videos.mjs brands/<name>/raw/videos.jsonl \
    brands/<name>/raw/obs_vid.json prompts/<vertical>.txt

# beat timeline — separate call, videos only
doppler run ... -- node extraction/extract_timeline_vid.mjs brands/<name>/raw/videos.jsonl \
    brands/<name>/raw/tl.json prompts/<vertical>-timeline.txt
```

Run entities and timeline **sequentially** on a large-video account. When they compete for
bandwidth they hit the per-request timeout and roughly a third of items fail — and those
failures are recorded in `.progress.jsonl` as done, so a naive resume skips them forever. If a
run failed that way, strip the entries with no real output before re-running.

A run with rising wall-time, flat CPU and no new progress output is a stalled socket, not slow
work: kill it and re-run. Videos resume.

## 3. Verify on the full set, not the sample

- zero errors
- observations per creative inside the range the prompt states
- core facets at or near 100% coverage
- off-list values on closed facets: should be none
- `notable_device`: read every value. Recurring ones mean the prompt is behind the creative —
  that is a return trip to scout-and-prompt, not something to note and move past
- re-run `analysis/coverage_audit.py` on the full observation set

Re-check the creative count against the warehouse now. Accounts keep being fetched while you
work, and creatives that appeared after the inventory was built would otherwise ship
unanalysed, leaving two schemas in one table.

## 4. Load

```
doppler run ... -- python3 loaders/load_entities_ch.py brands/<name>/raw/obs_all.json <entities_brand_id> \
    --aliases prompts/aliases/<vertical>.json --timeline brands/<name>/raw/tl.json
```

Announce the write first — this is a shared table. Then the rules that matter:

- `extracted_entities_v2` is a ReplacingMergeTree keyed by hash. **Undo means loading the
  previous state back, never DELETE.** If you are replacing an existing analysis, dump the
  current rows to a backup file first; that file is the only way back.
- It only replaces the hashes you actually load. Rows for hashes you did not analyse survive
  with their old schema, leaving a mixed table. Prove otherwise afterwards with a
  `JSONHas(..., '<a new facet>')` count over every row for the brand.
- Pre-merge counts look wrong. Compare with `FINAL`.
- Never alias a constant to a column name in an `INSERT ... SELECT` — `'X' AS brand_id` shadows
  the `WHERE` on the same column and silently inserts nothing.

## 5. Register the facets

The consuming UI reads attribute names from the brand's Mongo metrics document and nothing else,
so an unregistered facet is invisible no matter how well it loaded.

```
MONGO_URI=... python3 loaders/set_copilot_entities.py <entities_brand_id> prompts/facets/<vertical>.json --media video
```

Two failure modes that both look like "the feature is broken":

- Setting the dotted path `tags.keyFields` writes an empty object. Set the whole `tags` object.
- Every facet needs its media type right — All, Video or Image — or it lands in the wrong
  section of the UI and reads as missing.

## 6. Prove it works

Run three real queries before telling anyone it is done: a group-by on a multi-value facet, an
evidence question that has to return the verbatim quote, and a within-language or
within-segment comparison. All three must succeed.

Then report plainly: creatives analysed, observations written, coverage, what the data now
answers, and anything that failed. Mark the remaining steps in `run.yaml`.
