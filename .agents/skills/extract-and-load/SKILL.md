---
name: extract-and-load
description: >-
  Run the extraction over all the brand's creatives, check it, and write the entities to
  ClickHouse and the facet list to Mongo.
  Use when a run's extract, timeline, verify, load_ch, register_facets or smoke step is still
  pending, or when someone asks to re-run or re-load a brand that already has an agreed prompt.
  Covers the cost check, the loading rules, and proving it worked afterwards.
user-invocable: true
---

# extract-and-load

The mechanical half. Three places here cost real money or real data if you rush them.

## 1. Say what it will cost first

Every creative is a paid model call. Before a full run, tell the operator how many creatives,
roughly what it costs and roughly how long, and wait for a yes. Test runs of ten or fewer do
not need permission.

## 2. Extract

```
# images
doppler run ... -- node extraction/extract_images.mjs brands/<name>/raw/images.jsonl \
    brands/<name>/raw/obs_img.json prompts/<vertical>.txt

# videos (resumes from .progress.jsonl if it dies)
doppler run ... -- node extraction/extract_videos.mjs brands/<name>/raw/videos.jsonl \
    brands/<name>/raw/obs_vid.json prompts/<vertical>.txt

# beat timeline, videos only, separate call
doppler run ... -- node extraction/extract_timeline_vid.mjs brands/<name>/raw/videos.jsonl \
    brands/<name>/raw/tl.json prompts/<vertical>-timeline.txt
```

On an account with big videos, run entities and timeline **one after the other**, not at the
same time. When they compete for bandwidth they hit the timeout and about a third of items
fail — and those failures get written into `.progress.jsonl` as done, so resuming skips them
forever. If that happened, delete the entries with no real output before re-running.

If a run's clock keeps going up but CPU is flat and nothing new prints, the connection is stuck,
not slow. Kill it and re-run. Videos resume.

## 3. Check the full set, not the sample

- no errors
- observations per creative in the range the prompt says
- the important facets answered on nearly every creative
- closed facets: no answers outside the allowed list
- `notable_device`: read all of them. If the same thing keeps appearing, the prompt is behind
  the creatives — that means going back to scout-and-prompt, not noting it and moving on
- run `analysis/coverage_audit.py` again on the full set

Check the creative count against the warehouse again now. Accounts keep getting fetched while
you work, and anything that appeared after the list was built would otherwise go unanalysed and
leave two different schemas in one table.

## 4. Load

```
doppler run ... -- .venv/bin/python3 loaders/load_entities_ch.py brands/<name>/raw/obs_all.json <target_brand_id> \
    --aliases prompts/aliases/<vertical>.json --timeline brands/<name>/raw/tl.json
```

`<target_brand_id>` is the same brand, unless the operator asked for a test brand.

Say you are about to write before you do — this is a shared table. Then:

- `extracted_entities_v2` keeps one row per hash and replaces it when you load again.
  **To undo, you load the old rows back. You never DELETE.** If you are replacing an existing
  analysis, dump the current rows to a file first. That file is the only way back.
- It only replaces the hashes you actually load. Hashes you did not analyse keep their old
  rows, so the table ends up half old and half new. Check afterwards with a
  `JSONHas(..., '<a new facet>')` count over all the brand's rows.
- Counts look wrong until ClickHouse merges. Compare with `FINAL`.
- Never write `'X' AS brand_id` in an `INSERT ... SELECT`. The alias hides the `WHERE` on the
  same column and you insert nothing.

## 5. Register the facets

The UI reads the list of attributes from the brand's Mongo metrics document and nowhere else.
A facet that is not registered is invisible no matter how well it loaded.

This needs `MONGO_URI` (and `MONGO_DB_NAME`, default `test`) — see `.env.example`. Through a
tunnel it points at the LOCAL end, with `replicaSet` removed and `directConnection=true` added,
because a single forwarded port cannot see a replica set. Check it before you get here: this
step lands at the very end of a run, and finding the credential missing then means the whole
extraction is already paid for.

```
MONGO_URI=... .venv/bin/python3 loaders/set_copilot_entities.py <target_brand_id> prompts/facets/<vertical>.json --media video
```

Two mistakes that both look like "the feature is broken":

- Writing to `tags.keyFields` directly puts an empty object there. Write the whole `tags`
  object instead.
- Each facet needs the right media type — All, Video or Image — or it shows up in the wrong
  part of the UI and looks missing.

## 6. Prove it works

Run three real queries before saying it is done: group by a multi-value facet, ask a question
that has to return an exact quote, and compare within one language or segment. All three have
to work.

Then report plainly: how many creatives, how many observations, coverage, what the data can now
answer, and anything that failed. Set the rest of the steps in `run.yaml`.
