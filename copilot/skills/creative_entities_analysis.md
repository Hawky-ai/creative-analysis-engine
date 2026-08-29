---
name: creative_entities_analysis
description: Creative pattern analysis on this brand's observation-contract entities (CORE/OPTIONAL facets, multi-value facets, verbatim evidence, video beat timeline). Use for any "what's working in our creatives / which creative traits win / why does this creative perform" question.
when_to_use: Any question about creative attributes, winning or losing creative patterns, presenter/casting/hook/CTA/value-prop effects, or evidence for a creative claim. Takes precedence over FLOW B in analysis_flows.md for this brand.
---

# SKILL: creative_entities_analysis

This brand's creatives were analysed with a different extraction than the default one.
The attributes are NOT `Hook / CTA / Visual_Style` free text — they are a fixed facet
backbone with open-vocabulary values, plus verbatim evidence and a beat timeline. Read this
before running any creative pattern analysis; the shipped FLOW B steps still apply for
report format and confidence tiers, but Steps 3.5–5 are replaced by the method below.

## 1. What the entities are

Attribute list with meanings: `get_analysis_metadata` → `entities`. Three kinds:

- **CORE facets** — present on EVERY creative (`format`, `presenter_gender`,
  `presenter_age_band`, `presenter_attire`, `presenter_skin_tone`, `presenter_hair`,
  `setting`, `language_spoken`, `subtitle_script`, `hook`, `production_style`,
  `ai_content_label`, `ad_objective_type`, `address_mode`, `scene_description`).
  A value of `unclear` means the analyst could not tell; `none` means not applicable.
  Both are real values — keep them as their own group, do not drop them.
- **OPTIONAL facets** — present only when the trait genuinely exists (`persona_archetype`,
  `offer`, `price_metaphor`, `social_proof`, `device_targeting_signal`, `end_card`,
  `subtitle_style`). Absence = the creative does not have it. Compare "has it" vs
  "doesn't have it" — that absence is the control group.
- **MULTI-VALUE facets** — stored as arrays (`value_prop`, `cta`, `app_ui_shown`,
  `emotional_register`, `emotional_driver`). One creative can carry several values;
  `creative_group_by` counts it in every group it belongs to, so group percentages
  can sum above 100%. Say so when you report them.

Two payload keys are NOT attributes — never pass them to `creative_group_by`:
- `_observations` — `[{facet, value, evidence, source}]`. Evidence is verbatim: quote +
  English translation + timing ("at 0-2s"). This is where you get proof for a claim.
- `_timeline` — `{duration, beats:[{t0, t1, role, says, says_en, text, text_en, shows}]}`.
  `role` ∈ hook | problem | introduce-app | value-prop | demo | social-proof | price |
  objection-handling | invitation | cta | end-card. Beats are contiguous from 0 to duration.

`scene_description` is prose for reading, never for grouping.

## 2. Dimensions come BEFORE attributes (apples-to-apples gate)

Two facets are *dimensions*, not creative traits. Split on them first, analyse inside each
split, never pool across them:

1. `ad_objective_type` — `host-recruitment` ads sell "earn money", `user-acquisition` ads
   sell "talk to people". Different audience, different funnel, different CPI. A pattern
   pooled across both is meaningless.
2. `language_spoken` — auction prices differ per language by 2–4×. **Every pooled finding
   must be re-checked within language.** Real case from this account: "CTA in the first
   quarter = ₹48 CPI vs ₹76 late" pooled, but within language it REVERSED in 4 of 5
   languages. That is Simpson's paradox, not a finding. If a pattern does not hold in at
   least the two biggest languages separately, report it as "language-mix artefact".

Then the usual FLOW B dimensions (campaign objective × optimization_goal × funnel stage).

## 3. Dynamic grouping — the method

Primary metric for this account: `actions_omni_app_install` (installs) and cost per
install. Use the 20-day-from-launch window when comparing creatives that launched at
different times; lifetime numbers mix fatigue into the comparison.

For each dimension (objective type × language, top 2–3 languages by spend):

1. **Baseline** — `query_data` for the dimension with no group_by: total spend, installs,
   CPI. Every group is judged against this, not against other groups.
2. **One pass per facet** — loop `query_data(creative_group_by=<facet>, metrics=[spend,
   installs, cpi, impressions], filters=<dimension>)` over every CORE facet and every
   multi-value facet. Also `persona_archetype`, `offer`, `price_metaphor` (has vs has-not).
   That is ~20 calls per dimension; do them, do not sample.
3. **Group hygiene** — drop groups with < 3 creatives or < ₹10k spend before ranking.
   Report them, if at all, as Exploratory.
4. **Rank groups** by CPI vs baseline (Δ% and absolute ₹). A group is a candidate pattern
   only if it beats baseline AND its complement (all other values of the same facet) does
   not — check both.
5. **Cross-validate** per `creatives.md` → Cross-Validation: share of the value in the top
   decile vs bottom decile by CPI. Strong ≥ +30pp differential, else Indicative / discard.
6. **Combinations** — at most 3 pairs, chosen from the top single-facet winners
   (e.g. `address_mode × presenter_gender`, `hook × language_spoken`). Pull with
   `get_creative_entities(entities=[A, B], sort_metric=...)` and group in `execute`.
   15 facets give 105 pairs — do not enumerate them.
7. **Video structure** (only when the question is about hooks, retention, or CTA timing):
   for the creatives in scope, `view` them to get `_timeline`, then compare each beat's
   position (t0/duration) against `video_p25 / p50 / p75 / p100` watched counts.
   Compare quartiles to each other (p25→p50→p75→p100). **Never divide by
   `video_play_actions`** — it counts feed autoplay starts including scroll-pasts, so any
   ratio against it looks catastrophic and means nothing.

## 4. Evidence — every claim cites the creative

For each reported pattern: `view` 2 creatives that carry it (one top, one bottom if the
value appears in both) and quote the `_observations` evidence verbatim — the actual line
spoken, with timing. A pattern with no quotable evidence is not reported.

**Never call `analyze_video` to get a quote, a timing, or "what happens in the video".**
Every spoken line, its English translation, its timestamp and the beat-by-beat script are
already stored per creative (`_observations`, `_timeline`); `view(hashes=[...])` returns them
in one cheap call. `analyze_video` re-watches the file — minutes per video, times out on
long ones, and produces a fresh, unverifiable description that may not match the stored
entities. Use it only for a creative that has NO entities row.

**Do NOT call `analyze_video` to get a quote or a timing.** Every spoken line, its English
translation and its timestamp are already stored per creative in `_observations` (and the
beat-by-beat script in `_timeline`); `view(hashes=[...])` returns them in one cheap call.
`analyze_video` re-watches the file (minutes, and it times out on long videos) and produces a
fresh, unverifiable description. Reserve it for a creative that has NO entities row.

Casting facets (`presenter_skin_tone`, `presenter_hair`, `presenter_attire`,
`presenter_age_band`) are neutral descriptors of what is on screen. Report them as
"creatives cast with X performed …", never as judgements about people.

## 5. Output

Use `report_renderer` with FLOW B Section 4 structure, one 4.x block per dimension
(objective type × language). Pattern table columns per Hard Rule #30. Add one column:
`Within-language check` = holds / reverses / n too small.

Coverage note in the Context Block: how many creatives in scope have entities
(`get_creative_entities` count vs `query_data` creative count). Entities cover the
top-spend creatives, not every creative — say so.

## 6. Tool-level gotchas (each one has bitten a run)

- **Attribute names are exact.** `creative_group_by` / `include_entities` accept only the
  names listed in `get_analysis_metadata` → `entities` (lowercase snake_case, e.g.
  `value_prop`). `Hook`, `CTA`, `Visual_Style`, `USP` are NOT registered for this brand —
  if a name is rejected, use the facet from the list; do not retry with synonyms.
- **Multi-value facets arrive as lists.** In `include_entities` / `get_creative_entities`
  results, `value_prop`, `cta`, `app_ui_shown`, `emotional_register`, `emotional_driver`
  are Python lists. In `execute`, `df.explode("value_prop")` BEFORE any `groupby` —
  grouping on a list column raises `unhashable type: 'list'`. If a value comes back as a
  string that starts with `[`, `json.loads` it first.
- **Coverage is partial.** Entities exist for the top-spend creatives (~100), not all
  ~1,365. `include_entities` LEFT JOINs, so uncovered creatives return `""`/`None` for
  every facet. Drop those rows before grouping (an empty-string group is not a pattern)
  and state `covered / total` creatives and `covered spend / total spend` in the Context
  Block. Never describe an uncovered creative's traits — you do not know them.
- **Date window.** Entities were extracted on lifetime top-spend creatives. Run
  creative-pattern queries over the brand's full `availableDateRange` unless the user
  names a window; a default recent window can exclude most covered creatives and the
  join looks empty.
- **Ranking duplicates.** If an all-attributes ranking shows the same values under two
  keys (`format` and `Format`), they are aliases of one facet — report the lowercase one
  only.
- **Zero installs.** CPI = spend / installs; guard `installs == 0` (report "no installs",
  not `inf`), and never rank by CPI a group with < 5 installs.
- **Language groups too small.** A within-language check on a language with < 5 covered
  creatives is "n too small", not "holds" or "reverses". `host-recruitment` has ~8
  covered creatives — anything on it is Exploratory.
- **`unclear` / `none` are values.** Keep them as their own group; they mean "could not
  tell" / "not applicable" and are sometimes the interesting cohort (e.g. `none` presenter
  = no person on screen).
- **Timeline units.** `_timeline.beats[].t0/t1` are seconds; `duration` is seconds;
  `video_p25..p100` are viewer COUNTS, not percentages — normalise by `video_p25` (not by
  `video_play_actions`) when comparing curves across creatives.
- **One creative, many ads.** Metrics live per ad; a creative is reused across ads and
  adsets. Aggregate to `hash` (query at `level="creative"`) before comparing creatives, and
  give the ad count with every creative you name.

## 7. Rejected ads (Meta ad review)

This brand's data includes ads Meta DISAPPROVED in review. They are real ads the team
made and could not run — the most direct signal of what the platform will not allow.

- **Which ads were rejected**: `query_data(level="ad", include_context=true,
  filters={"ad_effective_status": "DISAPPROVED"}, date_range=<full availableDateRange>)`.
  `ad_effective_status = DISAPPROVED` is the rejected state. Most rejected ads never
  delivered (zero spend / impressions) — a metrics query will not find them; the context
  query will.
- **Why**: the `processed_fields` on each row carry `rejection_status`, `rejection_reason`
  (the Meta policy cited, e.g. "Dating ads", "Human exploitation") and `rejection_message`
  (Meta's verbatim text incl. what to change). Quote `rejection_reason` for every ad you
  list; quote `rejection_message` when asked why or how to fix.
- **Creative traits of rejected ads**: their creatives have entities like any other
  creative. To answer "what gets our ads rejected", group the rejected set by
  `hook_verbal_line`, `value_prop`, `address_mode`, `emotional_driver`, `presenter_attire`
  and compare against the approved set (same facets, same language). A trait that is
  common in rejected ads and rare in approved ones is the likely trigger; cite
  `_observations` evidence (the spoken line) alongside Meta's policy name.
- Report counts by policy first (n ads per `rejection_reason`), then the ad list with
  ad name, campaign, created date, policy — then traits. Never speculate about a policy
  reason that is not in `rejection_reason`.
