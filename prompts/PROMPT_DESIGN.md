# Prompt design methodology

Every extraction prompt in this library follows the same contract, earned across three
verticals (lead-gen video, retail-media banners, app-install video) and multiple rounds of
human review. **Do not write a new prompt from scratch — copy the nearest existing one and
adapt it using this checklist.** Every rule below exists because skipping it produced a
real, observed failure.

## The observation contract

One observation = one atomic fact:

```json
{"facet": "...", "value": "...", "evidence": "...", "source": "..."}
```

- **facet** = the question (fixed set per vertical). **value** = the answer (open
  vocabulary, category-style label or short concrete phrase). **evidence** = verbatim
  text / precise visual description / timing. **source** = where it was seen.
- The golden rule: *a different analyst looking at the same creative must arrive at the
  same value; the evidence is where nuance lives.*

## Non-negotiables (each traces to a real failure)

1. **CORE + OPTIONAL facet split.** A fixed backbone of facets emitted for EVERY
   creative ("unclear" allowed, silence not), plus optional facets only when genuinely
   present. *Failure it fixes: sparse schemas made creatives incomparable — one had
   `discount_magnitude`, its sibling didn't, and reviewers couldn't tell "absent" from
   "missed".*
2. **Concrete values, never bare abstractions.** "no phone number needed", not
   "privacy claim". When a facet is typed (e.g. `claim_type`), the TYPE is the value but
   the evidence must carry the concrete content — and downstream consumers must be told
   to read evidence, never the type label alone. *Failure: "benefit-only claim" alone
   told an analyst nothing.*
3. **Meaningful `source` attribution.** Headline text ≠ product-pack microtext ≠ CTA
   button ≠ spoken line ≠ burned-in subtitle. *Failure: flattening source to "visual"
   made pack-microtext ("SPF 50 PA++++", sub-line logos) rank as loudly as the actual
   headline, and sister-brand pack text got extracted as co-brands.*
4. **Literal facts get their own facet — never only prose.** Counts, prices, exact
   offer phrasings are queryable fields, not sentences buried in a description.
   *Failure: "two bottles visible" lived only inside evidence prose; nothing could
   GROUP BY it.*
5. **Semantics defined at the boundary.** `sku_count` counts DISTINCT sellable
   products, not physical objects (the same bottle shown twice for composition = 1).
   Bucket boundaries are stated inclusively ("30 to 49", "50 or higher") so an exact 50
   always lands in one bucket. *Failures: both happened.*
6. **Multi-instance facets say so explicitly.** Offers, claims, value props, CTAs: "a
   banner can genuinely carry TWO — extract each, do not stop at the most prominent".
   *Failure: a trial-pack price near the product suppressed the "Upto 50% off" bar
   below it.*
7. **Exact wording preserved where wording IS the variable.** `price_frame` keeps
   "up to 55% off" vs "flat 50% off" as different values — never normalize numbers.
8. **Platform chrome excluded, advertiser choices included.** "AD"/"Sponsored" labels
   and marketplace hashtags are not observations; a visible "AI Generated Content" tag
   IS (the advertiser chose it — and it's testable).
9. **Video: timing is mandatory evidence.** Hook (first 3s), CTAs, value props each
   note WHEN ("at 0-2s", "final 2s"). Verbatim quotes carry original language + English
   translation.
10. **Business model in the preamble.** Tell the model what the product is and who the
    ad targets — reading an ad without knowing the marketplace produced shallower
    facets. *Example: knowing the app is a two-sided paid-call marketplace surfaced
    `ad_objective_type` (user vs HOST recruitment — 8% of top spend!) and
    `address_mode` ("talk to ME" vs describing the app — a 28% CPI gap).*
11. **Open vocabulary, generic framing.** Facets fixed, values open; never hardcode the
    platform, brand list, or vertical assumptions — the same prompt structure must
    survive a brand switch. The model may invent a new value when nothing fits (it once
    correctly invented "formulation claim" for "Ayurvedic Proprietary Medicine").
12. **Objectivity constraints for people.** Casting attributes (age band, attire, hair,
    skin tone) are recorded as neutral, visible, FIXED-SCALE descriptors, because casting
    is a real creative decision the brand makes. Use a published scale where one exists
    (skin tone → Monk Skin Tone bands) and put the scale reference in EVIDENCE, never in
    the value — otherwise "medium-light" and "medium-light (MST 3-4)" split the same
    cohort in two. Never infer ethnicity, caste, religion, region-of-origin or class from
    appearance; never make attractiveness judgments; emit "unclear" when lighting or
    filtering genuinely prevents a call rather than guessing.
13. **A `FOCUS:` block makes listed attributes mandatory.** Prompts support an appended
    focus brief (see `brands/example/focus.md`) so a brand team can pin extra required
    attributes without a prompt rewrite. Agree it BEFORE the first run — a review round
    that discovers a missing attribute costs a full re-extraction.

14. **An escape-hatch facet for unknown unknowns.** Open vocabulary applies to VALUES,
    not FACETS — the model has nowhere to put a device no facet asks about, so it buries
    it in scene_description prose where nothing can group by it. Every prompt carries a
    `notable_device` optional facet ("anything prominent and deliberate that no facet above
    covers — name it"). *Failure: a split-screen endless-runner gameplay strip — a loud,
    testable retention device — was invisible to grouping for two extraction rounds; the
    model had described it in prose every time.*

## The iteration loop (never skip)

1. **Discover** the brand: inventory, spend, media mix, KPI keys, campaign-name
   structure, existing entity coverage. Do market research on the company — business
   model, monetization, review-mined user objections. The objections usually ARE the
   ad's persuasion levers.
2. **Look at real creatives first.** Download 5–6 samples spanning
   languages/categories/spend tiers; for videos, pull frames at 0.5s/2.5s/35%/60%/90%.
   Design facets from what you SEE, not from what you assume the vertical looks like.
3. **Draft** by copying the nearest prompt in this library and editing against the
   checklist above.
4. **Test on the samples you studied** — you know their ground truth, so you can grade
   the output. Check: core backbone complete, values consistent across near-identical
   creatives, evidence verbatim, nothing hallucinated, boundary semantics honored.
5. **Fix the prompt, not the output.** Every miss becomes a prompt clause with the
   failure named. Re-test the SAME samples until stable.
6. **Scale gradually**: ~100 before the full account; check facet-coverage counts and
   value distributions for drift (synonym splits like "expat"/"expatriate" are fine —
   the dictionary stage merges them).
7. **Coverage audit (cheap, automated).** Scan the extracted scene_description prose for
   recurring phrases that match NO facet value ("a mobile game is playing", "split screen",
   "reacts to a clip"). Anything that recurs is a missing facet — fix the prompt before the
   human round. The reviewer should be finding judgment errors, not schema holes.
8. **Human review round.** Put results in a compare/explorer page (see `explorers/`),
   collect reviewer findings, fold each one back into the prompt. Reviewer catches have
   found real bugs every single time.

## Cost expectations (gemini-2.5-flash via proxy, 2026 prices)

- Images: ~500 creatives ≈ $2–4, ~35 min at concurrency 6.
- Videos (native watch, 15–75s): ~100 ≈ $2, ~5 min at concurrency 10.
