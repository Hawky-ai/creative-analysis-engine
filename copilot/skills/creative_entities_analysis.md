---
name: creative_entities_analysis
description: Creative pattern analysis on this brand's observation-contract entities (CORE/OPTIONAL facets, multi-value facets, verbatim evidence, video beat timeline). Runs two mandatory tracks on every analysis — trait patterns and video retention/beat-structure patterns — then synthesises them. Use for any "what's working in our creatives / which creative traits win / why does this creative perform" question.
when_to_use: Any question about creative attributes, winning or losing creative patterns, presenter/casting/hook/CTA/value-prop effects, hook rate, video completion or drop-off, what content works at which point in the video, beat order, or evidence for a creative claim. Takes precedence over FLOW B in analysis_flows.md for this brand.
---

# SKILL: creative_entities_analysis

This brand's creatives were analysed with a different extraction than the default one.
The attributes are NOT Hook / CTA / Visual_Style free text — they are a fixed facet
backbone with open-vocabulary values, plus verbatim evidence and a beat timeline. Read this
before running any creative pattern analysis; the shipped FLOW B steps still apply for
report format and confidence tiers, but Steps 3.5–5 are replaced by the method below.

**The shape of a run.** Split by dimension → bucket by spend and KPI → then run **two
pattern-finding tracks over the same buckets**:

* **Track A (Section 4) — traits.** Sweep the facets on the scaled winners, descend from each
  facet into its evidence to get something a designer can build, test combinations, check
  every candidate against the scaled losers, score it.
* **Track B (Section 5) — retention and structure.** Build each video's retention curve, join
  the checkpoints to the beat timeline to see what content sits where the viewer stayed or
  left, and pattern-find on hooks, content-at-position and beat order — through the same loser
  control and the same scoring.

Then run both tracks again with the losers as the study group (Section 7), and finish with one
synthesis pass (Section 8) that merges what the two tracks found into a single ranked set of
insights.

**Both tracks run on every creative analysis.** Track B is not reserved for questions that
mention hooks or retention — whenever the scope contains video, it runs. Skipping the bucketing
step, stopping at the facet level, dropping Track B, or shipping the two tracks as two
unrelated lists are the four failure modes this skill exists to prevent.

## 1. What the entities are

Attribute list with meanings: get_analysis_metadata → entities. Three kinds:

* **CORE facets** — present on EVERY creative (format, presenter_gender,
  presenter_age_band, presenter_attire, presenter_skin_tone, presenter_hair,
  setting, language_spoken, subtitle_script, hook, production_style,
  ai_content_label, ad_objective_type, address_mode, scene_description).
  A value of unclear means the analyst could not tell; none means not applicable.
  Both are real values — keep them as their own group, do not drop them.
* **OPTIONAL facets** — present only when the trait genuinely exists (persona_archetype,
  offer, price_metaphor, social_proof, device_targeting_signal, end_card,
  subtitle_style). Absence = the creative does not have it. Compare "has it" vs
  "doesn't have it" — that absence is the control group.
* **MULTI-VALUE facets** — stored as arrays (value_prop, cta, app_ui_shown,
  emotional_register, emotional_driver). One creative can carry several values;
  creative_group_by counts it in every group it belongs to, so group percentages
  can sum above 100%. Say so when you report them.

Two payload keys are NOT attributes — never pass them to creative_group_by:

* _observations — [{facet, value, evidence, source}]. Evidence is verbatim: quote +
  English translation + timing ("at 0-2s"). This is where you get proof for a claim.
* _timeline — {duration, beats:[{t0, t1, role, says, says_en, text, text_en, shows}]}.
  role ∈ hook | problem | introduce-app | value-prop | demo | social-proof | price |
  objection-handling | invitation | cta | end-card. Beats are contiguous from 0 to duration.

scene_description is prose for reading, never for grouping.

**_observations is not a citation store — it is the analysis surface.** The facet value is a
label chosen from an open vocabulary; the evidence is the actual thing that was on screen or
said. Every insight in the final report comes from the evidence layer. Section 4 is the
method for getting there.

## 2. Dimensions come BEFORE attributes (apples-to-apples gate)

Two facets are *dimensions*, not creative traits. Split on them first, analyse inside each
split, never pool across them:

* ad_objective_type — host-recruitment ads sell "earn money", user-acquisition ads
  sell "talk to people". Different audience, different funnel, different CPI. A pattern
  pooled across both is meaningless.
* language_spoken — auction prices differ per language by 2–4×. **Every pooled finding**
  **must be re-checked within language.** Real case from this account: "CTA in the first
  quarter = ₹48 CPI vs ₹76 late" pooled, but within language it REVERSED in 4 of 5
  languages. That is Simpson's paradox, not a finding. If a pattern does not hold in at
  least the two biggest languages separately, report it as "language-mix artefact".

Then the usual FLOW B dimensions (campaign objective × optimization_goal × funnel stage).

Everything from Section 3 onward runs INSIDE one dimension. Buckets, facet sweeps,
combinations and loser checks are all dimension-local. Cross-dimension comparison happens
once, at the end, in the cross-dimension block (Section 9 → 4z).

## 3. Performance buckets — build them before any pattern work

A pattern is only as good as the spend behind the creatives carrying it. Rank a facet value
by CPI across the whole dimension and a ₹4k creative with two lucky installs outranks
everything real. So bucket first, and only ever draw evidence from the scaled buckets.

**Primary metric for this account**: actions_omni_app_install (installs) and cost per
install. Use the 20-day-from-launch window when comparing creatives that launched at
different times; lifetime numbers mix fatigue into the comparison.

**Step 1 — Baseline.** query_data for the dimension with no group_by: total spend,
installs, CPI. This is the reference every bucket and every group is judged against.

**Step 2 — Aggregate to creative.** Query at level="creative" so a creative reused across
many ads is one row, not many (see Section 10 → One creative, many ads).

**Step 3 — Cut the spend axis, dynamically.** Do not hardcode rupee thresholds; brands and
dimensions differ by an order of magnitude. Within the dimension:

* Sort creatives by spend descending, take the cumulative-spend cutoff at **80% of
  dimension spend** — those creatives are **scaled**.
* Everything below it is **small scale**.
* **Hard floor regardless of the percentile:** a creative with < ₹10k spend or < 5 installs
  is small scale even if it falls inside the top 80%. On a small dimension the percentile
  alone will happily promote noise.
* If fewer than 8 creatives clear the floor, the dimension cannot support pattern analysis.
  Say so, report the baseline, and stop — do not soften the floor to produce a finding.

**Step 4 — Cut the KPI axis.** Among scaled creatives only, split on CPI against baseline:

| Bucket | Rule | Role in the analysis |
|---|---|---|
| **Scaled winners** | Scaled AND CPI ≤ baseline CPI × 0.85 | The study group in Sections 4 and 5. Where patterns are found. |
| **Scaled losers** | Scaled AND CPI ≥ baseline CPI × 1.15 | The control group in Sections 4 and 5. The study group in Section 7. |
| **Scaled middle** | Scaled, CPI within ±15% of baseline | Neither. Excluded from both prevalence counts — a trait sitting in the middle is uninformative in either direction. |
| **Small scale** | Below the spend cutoff or under the floor | **Never evidence.** May be listed as "untested" to show the team what has not had a real read yet. |

The ±15% band is the default. If the dimension is large enough that both scaled buckets
still hold ≥ 10 creatives, widen to ±25% — a cleaner separation gives sharper differentials.
State the band you used in the Context Block.

**Step 5 — Report the buckets before analysing them.** Creative count, spend, installs and
CPI per bucket, plus the cutoff values used. The marketer must be able to see which creatives
were allowed to become evidence.

**Small scale is not a third pattern set.** It has no prevalence, no differential and no
confidence. The only legitimate statement about it is "not yet tested at spend".

## 4. Track A — finding the winning trait patterns

Run this on the **scaled winners**, with the **scaled losers** as the control. Section 5 runs
the parallel structural track over the same buckets; Section 7 runs both in reverse.

### 4.1 Facet sweep — where candidates come from

One pass per facet, on the scaled-winner set:

```
query_data(creative_group_by=<facet>, metrics=[spend, installs, cpi, impressions], filters=<dimension>)
```

Loop it over every CORE facet and every multi-value facet, plus persona_archetype, offer,
price_metaphor, social_proof, device_targeting_signal, end_card and subtitle_style as
has vs has-not. That is ~20 calls per dimension; do them, do not sample. The sweep is cheap
and the facet you skip is the one that mattered.

**Group hygiene** — a facet value needs ≥ 3 winner creatives to be a candidate. Below that
it is not a group, it is a coincidence.

A facet value becomes a **candidate** when it is over-represented in the scaled winners
relative to its share of the dimension, and its complement (all other values of the same
facet) is not. Check both sides — "western-casual wins" is not a finding if
"non-western-casual" also wins because attire simply doesn't matter here.

### 4.2 Evidence descent — the step that makes it actionable

**A facet value is never an insight.** "presenter_attire = western-casual, 14 of 22 scaled
winners, ₹41 CPI vs ₹58 baseline" is a bucket label. Nobody can brief a shoot from it —
western-casual covers a hoodie in a bedroom and a blazer over a t-shirt in an office. The
facet tells you *where to look*, not *what to say*.

For every candidate from 4.1:

1. **Pull the evidence.** view(hashes=[...]) on the winner creatives carrying the value.
   Read every `_observations` row whose `facet` is the candidate facet, and the `_timeline`
   beats that the observation is timed into.
2. **Cluster the evidence into concrete specifics.** Read the verbatim strings and group them
   by what they actually describe. Under western-casual you might find: plain solid-colour
   t-shirt, no visible branding; oversized hoodie, hood down; printed graphic tee; collared
   shirt worn open. Those are four different creative directions living under one label.
3. **Re-measure each specific.** Count winner creatives per specific and compute their spend
   and CPI. A specific carried by ≥ 3 winner creatives is reportable; below that it is
   context for the facet-level finding, not a finding of its own.
4. **Write the insight as the specific.** "Presenters in plain solid-colour t-shirts with no
   visible branding — 9 winner creatives, ₹9.4L spend, ₹38 CPI vs ₹58 baseline" is a brief.
   "Western-casual performs well" is not.
5. **Keep the facet visible as the route.** Report the specific as the insight and the facet
   as its parent, so the reader can see how it was found and can check the label themselves.

Descend on every candidate, not only the strongest one. This applies to the verbal facets as
much as the visual ones: under `hook`, the specific is the actual opening line and its timing;
under `value_prop`, the actual promise as spoken; under `cta`, the exact wording and which
beat it lands in. `_observations` carries the quote, the English translation and the timing —
report the source-language line with its translation, never a paraphrase.

**Where a specific does not exist**, say so. Some facets are genuinely coarse
(`format`, `ai_content_label`), and their evidence adds nothing beyond the label. Report those
at facet level and move on rather than inventing a specific.

### 4.3 Combinations

Single facets under-describe creatives. The real finding is often a pairing — a specific
attire with a specific presenter_age_band, a specific hook with a specific address_mode.

* **Where pairs come from:** the top single-facet candidates from 4.1, and pairs where
  neither element wins alone but the co-occurrence is concentrated in the winners. The second
  kind is the more valuable one — check it explicitly, don't only pair the winners with each
  other.
* **How to pull them:** get_creative_entities(entities=[A, B], sort_metric=...) and cross-tab
  in execute. 15 facets give 105 pairs — do not enumerate them. Cap the run at ~8 pairs,
  chosen for a reason you can state.
* **Threshold:** a pair needs ≥ 3 winner creatives in the cell. Pairs are thinner than
  singles; most will fail this and that is expected.
* **Descend on pairs too.** Once a pair clears the gate, run 4.2 on both sides of it so the
  combination is reported as two concrete specifics, not two labels.
* **Triples** only when a pair is Strong and holds ≥ 5 winner creatives. Otherwise the cell
  counts collapse and every triple looks significant.

### 4.4 Loser control — the gate every candidate passes through

An insight is not what winners have. It is what winners have **and losers don't**.

For every candidate — facet value, evidence specific, or combination — compute prevalence on
both sides:

```
prevalence_winners = carriers in scaled winners / total scaled winners
prevalence_losers  = carriers in scaled losers  / total scaled losers
differential       = prevalence_winners − prevalence_losers   (in percentage points)
```

Per creatives.md → Cross-Validation. That guide expresses the same test as a top-decile vs
bottom-decile split; the scaled-winner / scaled-loser buckets from Section 3 replace the
deciles for this brand, because a decile cut on a long tail of ₹2k creatives puts untested
work on both sides of the comparison. The differential and the thresholds are unchanged:

| Differential | Verdict |
|---|---|
| ≥ +30pp | Winning pattern |
| +15 to +30pp | Indicative — report, flag as needing more creatives |
| −15 to +15pp | **Discard.** Present in both, differentiates nothing. Say it was tested and rejected. |
| ≤ −15pp | Anti-pattern. Move it to the Section 7 losing set. |

The scaled middle is excluded from both denominators. Small scale never enters either count.

The discarded candidates are worth a line each in the report. A team that keeps briefing
"UGC-style, phone-shot" needs to know it appears just as often in the losers.

**Then the within-language re-check from Section 2**, on every candidate that passes. A
pattern that survives pooled but reverses inside the two biggest languages is a
language-mix artefact, not a pattern.

### 4.5 Confidence

Every reported pattern carries a 0–100 score and the tier from creatives.md → Confidence +
Scale. The score is computed, not asserted, and the components are shown:

| Component | Weight | Full marks at |
|---|---|---|
| Differential (winners vs losers, from 4.4) | 30 | ≥ +40pp |
| Carrier count in scaled winners | 25 | ≥ 8 creatives |
| Spend covered by carriers (share of winner-bucket spend) | 20 | ≥ 40% |
| CPI gap of carriers vs dimension baseline | 15 | ≥ 30% better |
| Within-language check | 10 | Holds in both top languages |

Score linearly within each component, floor at 0. Then:

| Score | Tier |
|---|---|
| ≥ 70 | Strong |
| 40–69 | Indicative |
| < 40 | Exploratory — flag, do not recommend action |

**Hard caps that override the score:** < 3 carrier creatives → Exploratory, whatever the
arithmetic. Within-language check returns "reverses" → Exploratory and label it a
language-mix artefact. Carriers concentrated in a single campaign → cap at Indicative and say
so; that is a campaign effect wearing a creative costume.

### 4.6 Coverage expectation

The entity set is wide and the evidence layer is wider. A dimension with a healthy winner
bucket should yield **many** patterns and combinations, not three. Sweep every facet, descend
on every candidate, test the pair set, and report everything that clears the gate — ranked by
confidence, not truncated to a top-3 list. Under-reporting is the more common failure: the
facets that look boring (`setting`, `subtitle_script`, `end_card`, `device_targeting_signal`)
are where the un-obvious findings live, because nobody briefs them deliberately.

If the sweep produces fewer than about five patterns clearing Indicative on a dimension with
20+ scaled creatives, the descent in 4.2 was probably too shallow — go back into the evidence
before concluding the creatives have nothing in common.

## 5. Track B — video retention and beat-structure patterns

**Track B runs on every creative analysis.** It is not conditional on the question mentioning
hooks, retention or timing. Whenever the scope contains video creatives, Track A and Track B
both run and both appear in the report. A trait pattern without a structural read is half an
answer: Track A tells you *who is on screen and what they say*, Track B tells you *when it
happens and whether the viewer was still there*.

Same buckets from Section 3, same loser control, same confidence scoring. What changes is the
unit of analysis — not a facet value, but a **position in time** and the content occupying it.

### 5.1 The retention curve

Pull per creative, aggregated to hash at level="creative":

`impressions`, `video_play_actions`, `video_p25_watched`, `video_p50_watched`,
`video_p75_watched`, `video_p100_watched`, `video_avg_time_watched`, `video_thruplay`,
plus `_timeline.duration` from view(hashes=[...]).

Derive the checkpoints. **Normalise by video_p25_watched, never by video_play_actions** —
video_play_actions counts feed autoplay starts including scroll-pasts, so any ratio against it
looks catastrophic and means nothing:

| Checkpoint | Formula | Status |
|---|---|---|
| Hook rate | `hook_rate = video_p25_watched / impressions` | Native (per ads.md derived set) |
| Thumb stop rate | `thumb_stop_rate = video_play_actions / impressions` | Native. Scroll-stop only — never a retention denominator |
| 25% | `1.0` by definition (the normalisation base) | Native |
| 50% | `r50 = video_p50_watched / video_p25_watched` | Native |
| 70% | `r70 = r50 + (r75 − r50) × 0.8` | **Interpolated** — Meta exposes no p70 |
| 75% | `r75 = video_p75_watched / video_p25_watched` | Native |
| 95% | `r95 = r75 + (r100 − r75) × 0.8` | **Interpolated** — Meta exposes no p95 |
| 100% | `r100 = video_p100_watched / video_p25_watched` | Native |
| Completion ratio | `completion_ratio = video_avg_time_watched / duration` | Native, continuous — the cross-check on the interpolated points |
| Hold rate | `hold_rate = video_p100_watched / video_p25_watched` (= r100) | Native derived name, kept for report continuity |

**On 70% and 95%:** Meta's API exposes quartiles only — p25, p50, p75, p100. The 70% and 95%
points are derived by linear interpolation between the bracketing native quartiles and must be
labelled *interpolated* wherever they appear. They are legitimate for locating a drop-off
inside a segment; they are **never** the sole basis for a pattern. If the account later exposes
native p70 / p95 fields, use those and drop the interpolation. `completion_ratio` is the honest
continuous measure — when an interpolated point and `completion_ratio` disagree about whether a
creative finished strong, believe `completion_ratio`.

If `video_thruplay` is present, report it alongside r95 for videos under 15 seconds, where
ThruPlay is effectively a completion count.

### 5.2 Duration bands — the apples-to-apples gate for Track B

A 15-second video and a 45-second video have structurally different curves; pooling them
manufactures findings. Before any comparison, band the scoped creatives by `_timeline.duration`:

`≤ 15s` · `16–30s` · `31–45s` · `> 45s`

All curve comparisons, medians and patterns are **within band**. A band with fewer than 5
scaled creatives is reported as "n too small" and produces no patterns. State the band
distribution in the Context Block.

Within each band, compute the **median curve** across scaled creatives — median hook_rate, r50,
r70, r75, r95, r100, completion_ratio. Every creative is judged against its band median, the
way Track A judges every group against the dimension baseline.

### 5.3 The time join — turning a checkpoint into content

This is the step that makes Track B different from ordinary video reporting.

`_timeline.duration` is in seconds and `beats[].t0 / t1` are in seconds, so a percentage
checkpoint converts directly:

```
t_checkpoint = pct × duration          # 0.25, 0.50, 0.70, 0.75, 0.95, 1.00
beat_at(pct) = the beat whose [t0, t1) contains t_checkpoint
```

Beats are contiguous from 0 to duration, so every checkpoint lands in exactly one beat. For
each creative you now hold a row like:

> 32s video · hook_rate 0.41 (band median 0.29) · r50 0.74 (median 0.61) · r75 0.52 (median 0.55)
> · r100 0.38 (median 0.34) · at 50% it is in a `demo` beat · at 75% in a `price` beat · at 95%
> in a `cta` beat

Also record, per creative:

* **Segment retention** — the drop across each window: `0→25` (hook survival, = hook_rate),
  `25→50` (r50), `50→75` (r75/r50), `75→100` (r100/r75). A creative's problem is a *segment*,
  not a point.
* **The content of the losing segment** — every beat overlapping that window, with `role`,
  `says` + `says_en`, `text` + `text_en`, and `shows`.
* **Role onset positions** — for each `role` present, `t0 / duration`, i.e. where in the video
  that role first appears as a fraction. This is what makes ordering comparable across
  durations.

### 5.4 Three pattern questions

Each runs on scaled winners with scaled losers as control, inside a duration band, and each
produces patterns that go through the Section 4.4 loser control and Section 4.5 confidence
scoring unchanged.

**(a) Hook patterns — what stops the scroll.**
Take the creatives in the top quartile of `hook_rate` within the band and descend per Section
4.2 into the `hook` beat and the `hook` facet's `_observations`: the actual opening line
(`says` + `says_en`), the on-screen text at 0–2s (`text` + `text_en`), and what is visually on
screen (`shows`). Cluster into concrete opening devices — a direct question, a mid-action cold
open, a named price in the first line, a face at arm's length, a hard cut on the first
syllable. Control against the bottom quartile of `hook_rate`. Report the device *and the
verbatim line*, never "question hook" alone.

Watch for the two-way split: a high hook_rate with a collapsing `25→50` segment is a hook that
overpromises. Report that as its own pattern — it is a different brief from a weak hook.

**(b) Content-at-position patterns — what belongs where.**
For each segment (`0→25`, `25→50`, `50→75`, `75→100`), tabulate which beat `role` occupies it,
winners vs losers:

```
| Segment | Role occupying it | n winners | n losers | Median segment retention | Differential |
```

Then descend: for the roles that survive the segment well, read the beats' verbatim content and
cluster it the way Section 4.2 clusters facet evidence. The finding is not "demo works in the
middle" — it is "a demo beat showing the live chat screen with an audible other-side voice,
occupying the 25–50% window, holds 0.78 vs 0.61 band median (7 winner creatives)."

Do this in both directions. Roles that consistently sit in the *collapsing* segment of losers
are structural anti-patterns — for example a `price` beat landing before the 50% mark in a
band where winners hold price until after 75%.

**(c) Order patterns — the sequence, not the ingredients.**
Reduce each `_timeline` to its **role sequence**, e.g.
`hook → problem → introduce-app → demo → social-proof → cta → end-card`. Then look for:

* **Structure archetypes** — full sequences recurring across ≥ 3 winner creatives. Name each
  archetype and report its curve against the band median.
* **Adjacency n-grams** — role pairs and triples that recur. `hook → problem` versus
  `hook → introduce-app` as the opening move is usually the single most decisive ordering
  finding in a band.
* **Role onset position** — median `t0 / duration` per role, winners vs losers. This is where
  "CTA too late" or "price too early" becomes a number: *cta first appears at 0.62 of duration
  in winners vs 0.85 in losers (differential −0.23)*.
* **Role absence** — a role missing from winners is a finding. Winners with no `price` beat at
  all, or no `objection-handling`, is as actionable as any presence pattern.
* **Beat density** — beat count ÷ duration. Compare winners vs losers; it separates a paced
  video from a rapid-cut one without needing a facet for it.

Sequences are compared as sequences. Two creatives with the same roles in a different order are
different structures, and merging them is the main way this analysis goes wrong.

### 5.5 Retention is a proxy — close the loop on CPI

Attention is not installs. Every Track B pattern must be reported with the CPI of its carriers
against the dimension baseline, and the two disagreements are findings in their own right:

* **Held but didn't convert** — top-quartile r100, bottom-quartile CPI. Read the `75→100`
  content and the `cta` / `end-card` beats; the ask is failing, not the story.
* **Converted without holding** — bottom-quartile r100, top-quartile CPI. The install decision
  is being made early; the back half of the video is doing nothing and can be cut. Check where
  the `cta` role first appears.

A Track B pattern that improves retention while worsening CPI is reported as a retention
finding explicitly labelled *not a performance finding*. Never promote it to a recommendation.

### 5.6 Track B scope limits

* Video only. Static and carousel creatives have no `_timeline` and are Track A only — say how
  many creatives in scope were excluded for that reason.
* A creative with entities but no `_timeline` is excluded from Track B, not imputed.
* Interpolated checkpoints (r70, r95) never carry a pattern alone.
* Bands with < 5 scaled creatives produce no patterns.
* Never call analyze_video for a beat, a timing or a line — `_timeline` and `_observations`
  already hold them, and view(hashes=[...]) returns them in one cheap call (Section 6).

## 6. Evidence — every claim cites the creative

For each reported pattern: view 2 creatives that carry it (one top, one bottom if the
value appears in both) and quote the _observations evidence verbatim — the actual line
spoken, with timing. A pattern with no quotable evidence is not reported.

**Never call analyze_video to get a quote, a timing, or "what happens in the video".**
Every spoken line, its English translation, its timestamp and the beat-by-beat script are
already stored per creative (_observations, _timeline); view(hashes=[...]) returns them
in one cheap call. analyze_video re-watches the file — minutes per video, times out on
long ones, and produces a fresh, unverifiable description that may not match the stored
entities. Use it only for a creative that has NO entities row.

Casting facets (presenter_skin_tone, presenter_hair, presenter_attire,
presenter_age_band) are neutral descriptors of what is on screen. Report them as
"creatives cast with X performed …", never as judgements about people.

**Video structure** is no longer a conditional side-quest — it is Track B, and it runs every
time (Section 5). The rule that governs it stays: compare quartiles to each other
(p25→p50→p75→p100), normalise by video_p25_watched, and **never divide by video_play_actions**
— it counts feed autoplay starts including scroll-pasts, so any ratio against it looks
catastrophic and means nothing.

## 7. Finding the losing patterns

Run Sections 4 **and 5** again with the buckets swapped: **scaled losers** are the study group,
**scaled winners** are the control. Same facet sweep, same evidence descent, same
combinations, same retention curves, same time join, same three structural questions, same
differential table read in the other direction, same confidence scoring.

This is not the leftovers from the winning pass. A trait can be absent from the winners
without being common in the losers, and the losing patterns are what the team must be told to
stop briefing. Run it as a full pass.

On the Track B side the losing pass is where the structural failures name themselves: the
segment where the loser bucket's median curve falls away fastest, and the role occupying it.
Report that segment and its content before anything else in the losing block — "losers lose in
25→50, and 11 of 14 are running an `introduce-app` beat there" is the most directly fixable
finding this skill produces.

Three additions specific to the losing side:

* **Separate "loses" from "never got a chance".** A creative in the scaled-loser bucket spent
  real money and underperformed. A trait that only appears in small-scale creatives is
  untested, not losing — never report it as a losing pattern.
* **Check fatigue before blaming the trait.** If the loser carriers are old creatives that
  once performed, the pattern is fatigue, not a bad trait. Compare their 20-day-from-launch
  CPI against their lifetime CPI; if the early window was fine, say the trait is exhausted
  rather than wrong.
* **Separate a bad video from a bad segment.** A creative losing across every segment is a
  weak creative; a creative holding to 75% and collapsing after is a fixable ending. Only the
  second belongs in a "recut these" recommendation, and Track B is what tells them apart.

Report the anti-patterns from 4.4 (differential ≤ −15pp in the winning pass) alongside the
patterns found here — they are the same finding reached from two directions, and agreeing
from both sides raises confidence.

## 8. Synthesis — one grouped view across both tracks

Two tracks and a losing pass produce a long, fragmented list. The synthesis is a required
final step: one pass that collapses the fragments into a ranked set of consolidated insights
the team can actually act on. A report that ends at Section 7 is incomplete.

### 8.1 Build the pattern ledger

One row per pattern surviving from Track A (Section 4), Track B (Section 5) and the losing
pass (Section 7), across every dimension:

```
| # | Claim (the specific, not the label) | Track | Origin (facet / segment / sequence) |
  Carrier hashes | n carriers | Carrier spend | Carrier CPI vs baseline | Differential |
  Confidence score | Tier | Direction (winning / losing / anti-pattern) |
```

Carrier hashes are the join key for everything below, so record them as a set, not a count.

### 8.2 Merge by carrier overlap — the same finding described twice

Track A and Track B look at the same creatives through different lenses, so they routinely
describe one underlying thing in two vocabularies. "Presenter in a plain solid-colour tee, no
branding" and "demo beat showing the live chat screen in the 25–50% window" may be the same
eight creatives.

For every pair of patterns, compute carrier overlap:

```
overlap = |carriers(A) ∩ carriers(B)| / |carriers(A) ∪ carriers(B)|
```

| Overlap | Treatment |
|---|---|
| ≥ 0.6 | **Merge.** One consolidated insight describing the whole creative — casting, message, structure and timing together. |
| 0.3 – 0.6 | **Relate, don't merge.** Report separately, cross-referenced: "co-occurs with #7 in 5 of 9 carriers." |
| < 0.3 | Independent. Leave alone. |

**Confidence on a merge does not add up.** Two lenses on the same eight creatives is one piece
of evidence, not two. Set the merged confidence to the higher of the two component scores, and
raise it by at most 5 points only when the two components are genuinely independent
measurements (a casting trait and a retention curve are; two facets that both describe attire
are not). State which it was. Double-counting overlap is the fastest way to ship a confident
wrong answer.

### 8.3 Group the merged insights by theme

Where carrier sets do not overlap, group by what the team would change:

* **Casting & presence** — who is on screen, how they look, how they are framed
* **Message & promise** — the hook line, the value_prop, the emotional register
* **Structure & timing** — role order, onset positions, segment retention, beat density
* **Offer & proof** — offer, price_metaphor, social_proof, and where they land in the timeline
* **Production & format** — production_style, subtitle_style, end_card, ai_content_label
* **Compliance** — anything overlapping the Section 11 rejected-ad findings, including a
  winning trait that also appears in a high-confidence rejection hypothesis; that tension is
  worth surfacing before the team scales it

Every insight lands in exactly one theme. A theme with no surviving insights is reported as
"tested, nothing separated winners from losers" — that is useful and stops the team re-testing it.

### 8.4 Resolve conflicts explicitly

Two things will contradict each other and the report must say so rather than choosing quietly:

* A Track A trait that wins, carried mostly by creatives that lose structurally in Track B —
  report the tension, name the carriers on each side, and say which has the higher confidence.
* A pattern that holds in one dimension and reverses in another — this belongs in the
  cross-dimension block (Section 9 → 4z) and is usually the most actionable thing in the run.
* A pattern that survives pooled but fails the within-language check — already labelled a
  language-mix artefact in Section 4.4; it appears in the ledger as tested-and-rejected, never
  as a consolidated insight.

### 8.5 The consolidated insight card

The synthesis output. One card per merged insight, ranked by confidence score descending:

```
INSIGHT — [one line, concrete enough to brief a shoot from]
  Build this:      what to make, specifically — casting, line, structure, timing
  Avoid:           the paired anti-pattern, where one exists
  Evidence:        n carriers · spend · CPI vs baseline · differential vs scaled losers
  Structure:       role sequence and onset positions, where Track B contributed
  Quotes:          verbatim line (source language + English + timing) from 2 carriers
  Confidence:      score / 100 · tier · which components drove it
  Tracks:          A / B / both · merged from patterns #n, #m
  Holds in:        languages and dimensions where it was confirmed
```

Cap the card set at the top 10–15 by confidence. Everything else stays in the ledger table
below the cards — visible and auditable, but not competing for attention.

Close with a **Do next** block: the three highest-confidence insights expressed as production
instructions, and the two highest-confidence anti-patterns expressed as stop-doing
instructions. Nothing enters this block below Indicative.

## 9. Output

Use report_renderer with FLOW B Section 4 structure, one 4.x block per dimension
(objective type × language). Pattern table columns per Hard Rule #30. Add four columns:
Within-language check = holds / reverses / n too small; Confidence score = 0–100;
Bucket = winners / losers; Track = A / B / both.

Order inside each 4.x block:

```
4.x.0  Buckets — creative count, spend, installs, CPI per bucket + the cutoffs used,
       and the duration-band distribution for Track B
4.x.a  Track A — winning trait patterns: insight (the specific), parent facet,
       evidence quotes, differential, confidence score + tier
4.x.b  Track A — winning combinations: same shape, both sides descended to specifics
4.x.c  Track B — retention curve table: hook_rate, r50, r70*, r75, r95*, r100,
       completion_ratio per creative against the band median (* = interpolated)
4.x.d  Track B — hook patterns: the opening device plus the verbatim line
4.x.e  Track B — content-at-position patterns: segment × role table, then the
       descended content of the surviving and collapsing roles
4.x.f  Track B — order patterns: structure archetypes, adjacency n-grams, role
       onset positions (winners vs losers), role absence, beat density
4.x.g  Losing patterns and anti-patterns from both tracks (Section 7)
4.x.h  Tested and rejected — candidates that failed the loser control, one line each
4.x.i  Supporting creatives per pattern, per Hard Rule #30
4.x.j  Untested — small-scale creatives, excluded static/carousel creatives, and
       duration bands that were too small to read
```

Then, once, after all dimension blocks:

```
4z     Cross-dimension overlap and anomalies (per FLOW B)
5      Synthesis — consolidated insight cards, ranked by confidence (Section 8)
5a     The full pattern ledger table behind the cards
5b     Do next — 3 production instructions, 2 stop-doing instructions
```

Coverage note in the Context Block: how many creatives in scope have entities
(get_creative_entities count vs query_data creative count). Entities cover the
top-spend creatives, not every creative — say so. Also state the bucket cutoffs, the CPI band
used, the confidence weights, the duration bands, and how many creatives Track B excluded for
having no _timeline — so the marketer can reproduce the buckets and knows what was not read.

**Self-check before emitting.** The report is incomplete, and must be re-rendered, if any of
these is true: a dimension block carries Track A patterns but no Track B blocks while video
creatives were in scope; a Track B checkpoint is reported without saying whether it is native
or interpolated; the Synthesis section is missing; or a consolidated insight card cites a
confidence higher than its highest component pattern without stating that the merge was
independent.

## 10. Tool-level gotchas (each one has bitten a run)

* **Attribute names are exact.** creative_group_by / include_entities accept only the
  names listed in get_analysis_metadata → entities (lowercase snake_case, e.g.
  value_prop). Hook, CTA, Visual_Style, USP are NOT registered for this brand —
  if a name is rejected, use the facet from the list; do not retry with synonyms.
* **Multi-value facets arrive as lists.** In include_entities / get_creative_entities
  results, value_prop, cta, app_ui_shown, emotional_register, emotional_driver
  are Python lists. In execute, df.explode("value_prop") BEFORE any groupby —
  grouping on a list column raises unhashable type: 'list'. If a value comes back as a
  string that starts with [, json.loads it first.
* **Prevalence is per creative, not per row.** After exploding a multi-value facet, a
  creative appears in several rows. Deduplicate on hash before counting carriers, or every
  multi-value pattern will look more prevalent than it is.
* **Coverage is partial.** Entities exist for the top-spend creatives (~100), not all
  ~1,365. include_entities LEFT JOINs, so uncovered creatives return ""/None for
  every facet. Drop those rows before grouping (an empty-string group is not a pattern)
  and state covered / total creatives and covered spend / total spend in the Context
  Block. Never describe an uncovered creative's traits — you do not know them.
* **Buckets are built on covered creatives only.** An uncovered creative has no traits to
  contribute, so including it in a bucket inflates the denominator and deflates every
  prevalence. Build buckets after the coverage filter, and report both counts.
* **Date window.** Entities were extracted on lifetime top-spend creatives. Run
  creative-pattern queries over the brand's full availableDateRange unless the user
  names a window; a default recent window can exclude most covered creatives and the
  join looks empty.
* **Ranking duplicates.** If an all-attributes ranking shows the same values under two
  keys (format and Format), they are aliases of one facet — report the lowercase one
  only.
* **Zero installs.** CPI = spend / installs; guard installs == 0 (report "no installs",
  not inf), and never rank by CPI a group with < 5 installs.
* **Language groups too small.** A within-language check on a language with < 5 covered
  creatives is "n too small", not "holds" or "reverses". host-recruitment has ~8
  covered creatives — anything on it is Exploratory.
* **unclear / none are values.** Keep them as their own group; they mean "could not
  tell" / "not applicable" and are sometimes the interesting cohort (e.g. none presenter
  = no person on screen).
* **Timeline units.** _timeline.beats[].t0/t1 are seconds; duration is seconds;
  video_p25..p100 are viewer COUNTS, not percentages — normalise by video_p25 (not by
  video_play_actions) when comparing curves across creatives.
* **p70 and p95 do not exist.** Meta exposes p25 / p50 / p75 / p100 only. r70 and r95 are
  interpolated in Section 5.1 and must be labelled as such every time they appear. If a query
  for a p70 or p95 field is rejected, that is the API being correct — do not retry with a
  synonym, and do not silently substitute p75 or p100 for them.
* **Curves need the duration.** duration lives in _timeline, not in the metrics payload, so a
  Track B run needs view(hashes=[...]) for every creative in scope before any checkpoint can
  be converted to seconds. Pull it in one batched call, not per creative.
* **Beat roles are a closed set.** role ∈ hook | problem | introduce-app | value-prop | demo |
  social-proof | price | objection-handling | invitation | cta | end-card. A sequence
  containing anything else means the payload was misread — re-read it rather than inventing a
  role name.
* **Sequences are ordered.** When reducing _timeline to a role sequence, do not sort, dedupe
  or set-ify it. hook → problem → cta and hook → cta → problem are different structures, and
  collapsing them is the main way Track B produces a false finding.
* **Retention is not conversion.** A pattern that improves r100 while worsening CPI is a
  retention finding, not a performance one (Section 5.5). Never promote it to a
  recommendation.
* **One creative, many ads.** Metrics live per ad; a creative is reused across ads and
  adsets. Aggregate to hash (query at level="creative") before comparing creatives, and
  give the ad count with every creative you name.

## 11. Rejected ads (Meta ad review)

This brand's data includes ads Meta DISAPPROVED in review. They are real ads the team
made and could not run — the most direct signal of what the platform will not allow.

The stored `rejection_reason` names the policy. It does not say what in the video triggered
it, and that is the question worth answering. The method below turns each policy into a set
of candidate creative triggers and tests each one against ads that carried the same trait and
ran anyway.

**Policy reference:** `vault_cli "cat library/guides/meta/ad_rejection_reasons.md"`.
Read it before generating hypotheses. §6 of that file maps each policy to the facets to group
on and the `_observations` / `_timeline` fields to read; §1–§4 give the policy definitions.

### 11.1 Pull the rejected set

```
query_data(level="ad", include_context=true,
           filters=[{"filter_key": "ad_effective_status", "filter_value": "DISAPPROVED"}],
           limit=500)
```

Always pass limit — the default is 100 and the rejected set can be larger; the count you
report must equal the rows returned, never a count inside a truncated top-100.
ad_effective_status = DISAPPROVED is the rejected state. Most rejected ads never
delivered (zero spend / impressions) — a metrics query will not find them; the context
query will.

The processed_fields on each row carry rejection_status, rejection_reason
(the Meta policy cited, e.g. "Dating ads", "Human exploitation") and rejection_message
(Meta's verbatim text incl. what to change). The rejection reason lives in
processed_fields.rejection_reason on the DISAPPROVED rows — read it there before concluding
it is "not stored"; do not reconstruct a policy from watching the video when the stored
reason exists.

**Selection scope warning**: a Selection freezes an ad set at creation time; most
rejected ads never delivered and may not be inside it. When the user asks about
rejections while a selection is active, run the account-wide DISAPPROVED context query
above WITHOUT the selection, in the same turn — never stop to ask "how would you like
to proceed" just because the selection has zero disapproved ads. Answer with both
numbers: "your selection contains N of the account's M rejected ads; analysing all M."
Then do the comparison the user asked for using the account-wide rejected set against
the selection's (or account's) high-spend approved set. Zero rejected ads in the
selection is NOT zero rejected ads.

### 11.2 Group by reason

Count ads per rejection_reason. Report this table first — before any interpretation — with
ad name, campaign, created date and policy per ad. Everything after this point runs **inside
one policy group**; never pool hypotheses across policies, and never merge two policies
because they sound similar.

Also split each group by language_spoken and ad_objective_type where the group is large
enough. Enforcement is not uniform across languages, and host-recruitment creatives trip
different policies than user-acquisition ones.

### 11.3 Generate hypotheses per group

For each policy group, produce **2–5 candidate triggers** — never settle on one before
testing. Each hypothesis must be a checkable statement about something in the creative, tied
to a facet or an evidence pattern, not a vibe.

Seeds, in order:

1. **rejection_message verbatim.** Meta's own text usually narrows the policy to a specific
   element. That is hypothesis #1, always.
2. **§6 of ad_rejection_reasons.md** — the facets and evidence fields that policy usually
   comes from. Group the rejected set on those facets and read the evidence on the carriers.
   hook_verbal_line, value_prop, address_mode, emotional_driver and presenter_attire carry
   most of this account's triggers and are worth grouping on for every policy, whether or not
   §6 lists them for that row.
3. **The policy definition in §1–§4** — read what the rule actually prohibits and ask what in
   these specific creatives could satisfy it.
4. **What the rejected set has in common that the account's creatives generally don't** —
   sweep the rejected group with the Section 4.1 facet sweep and descend per 4.2. Concentrated
   traits that are rare elsewhere are hypotheses in their own right, even when §6 does not
   list them.
5. **Where in the video it happens** — run the Section 5.3 time join on the rejected set. A
   policy trigger usually sits in one beat, and naming it ("the second-person line lands in the
   `hook` beat at 0–2s in 8 of 9 rejected ads") turns the fix into a recut instead of a
   rebuild. Rejected ads mostly never delivered, so they have no retention curve — use the
   timeline and the beat content only, never the checkpoints.

Write each hypothesis as: *trait (concrete, from evidence) → why it satisfies the cited policy
(quoting the policy) → how many of the rejected group carry it*.

Two policies commonly fire on one creative. When traits from two rows of §6 are both present,
carry both hypotheses forward rather than forcing a single winner.

### 11.4 Control test — against ads that ran

A trait is only the trigger if ads carrying it *didn't* get through. So for each hypothesis,
find the ads that carry the same trait and **delivered impressions**:

* Pull the approved, delivering set for the same language_spoken and ad_objective_type
  (impressions > 0, not DISAPPROVED).
* Count carriers of the hypothesised trait on both sides using the same evidence-level
  definition — if the hypothesis is "second-person address plus a loneliness attribute in the
  hook", the approved side must be matched on that, not on the parent facet.
* Deduplicate to creative hash on both sides before counting.

```
prevalence_rejected = carriers in the policy group / ads in the policy group
prevalence_approved = carriers in the approved delivering set / that set's size
gap                 = prevalence_rejected − prevalence_approved
```

The reading is the whole point of the exercise:

* 9 of 10 rejected carry it, 2 of 60 approved do → **this is the trigger.**
* 9 of 10 rejected carry it, 40 of 60 approved also do → **not the trigger.** The trait is how
  the brand makes ads; something else in these ten is different. Go back to Section 11.3.

A hypothesis that fails the control test is reported as tested and rejected, not deleted. It
stops the team from rewriting a brief around a trait that was never the problem.

### 11.5 Confidence per hypothesis

Same 0–100 scale, weights adapted to this question:

| Component | Weight | Full marks at |
|---|---|---|
| Gap (rejected vs approved-delivering prevalence) | 40 | ≥ +50pp |
| Share of the policy group carrying the trait | 25 | ≥ 80% |
| Size of the policy group | 20 | ≥ 10 ads |
| Size of the approved control set | 15 | ≥ 30 ads |

Tiers as in Section 4.5 (≥70 Strong, 40–69 Indicative, <40 Exploratory).

**Hard caps:** a policy group with < 3 ads supports nothing above Exploratory, whatever the
gap. An approved control set with < 10 ads caps at Indicative — a small control cannot show
absence. A trait quoted directly from rejection_message never scores below Indicative, since
Meta named it.

### 11.6 Compile

Per policy group, in this order:

1. Ad count and the ad list (ad name, campaign, created date, policy).
2. rejection_message quoted for the group, or per ad where they differ.
3. Ranked hypotheses — trait, policy clause it satisfies, rejected vs approved prevalence,
   gap, confidence score and tier, and the `_observations` quote (source language + English +
   timing) from a rejected ad that carries it.
4. Tested and rejected hypotheses, one line each with their gap.
5. The fix implied by the surviving hypotheses, phrased as what to change in the creative and
   traceable to the policy text — e.g. for Personal attributes, rewrite the hook from second
   person to third person, with the approved-side phrasing that already ships.

Then a per-ad line: the most plausible trigger for that specific ad, with its confidence.
Where no hypothesis clears Exploratory, say the trigger is undetermined and give the policy
and the message — that is more useful than a confident guess.

**Never speculate about a policy reason that is not in rejection_reason.** Hypotheses explain
why the stated policy fired. They never propose a policy Meta did not cite.
