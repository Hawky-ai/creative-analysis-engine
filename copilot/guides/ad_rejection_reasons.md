# Meta Ad Rejection Reasons — Compact Reference

Source: Meta Advertising Standards, transparency.meta.com (read 2026-09-01).
Scope of review: creative + text + targeting + landing page. Re-review can happen anytime after launch.
Two outcomes: **ad rejected** (fix and resubmit) or **asset restricted** (ad account / Page / user account / Business Account).

---

## 0. How this file is used

This is the policy dictionary for the disapproved-ad workflow in
`creative_entities_analysis` → Section 11 (Rejected ads). It is a reference, not a flow.

Read it whenever a `rejection_reason` needs to be turned into a testable statement about
what was actually in the video:

1. The stored `processed_fields.rejection_reason` names the policy. Find that policy in
   §1–§4 below and read what triggers it.
2. Read `processed_fields.rejection_message` — Meta's verbatim text. It usually narrows the
   policy to a specific element and is always hypothesis seed #1.
3. Go to §6 — **Policy → candidate creative triggers**. It maps each policy to the facets to
   group on and the `_observations` / `_timeline` fields to read for evidence.
4. Generate the hypotheses from §6 plus anything the policy text in §1–§4 suggests, then
   control-test them against approved ads that delivered, per Section 11 of the skill.

**Never** name a policy that is not in `rejection_reason`. This file explains *why the stated
policy fired*; it does not license guessing a different policy.

---

## 1. Prohibited outright — no compliant version exists

| Reason | Why it triggers |
|---|---|
| Child sexual exploitation / nudity | Any sexualization or endangerment of minors. Reported to NCMEC. |
| Coordinating harm, promoting crime | Ad organizes, promotes, or admits criminal or harmful acts. |
| Dangerous organizations & individuals | Praise/support/representation of Meta-designated entities. |
| Discriminatory practices | Discriminatory copy, OR targeting that wrongfully includes/excludes a protected group. US housing/employment/credit ads not flagged as Special Ad Category. |
| Hateful conduct | Attack based on race, ethnicity, national origin, disability, religion, caste, sexual orientation, sex, gender identity, serious disease. |
| Human exploitation | Trafficking or coordinated exploitation of people. |
| Locally illegal content | Reported by government/court/NGO/public as illegal in that market. |
| Misinformation | Claim debunked by third-party fact-checkers. Repeat = ad ban. |
| Vaccine discouragement | Discourages vaccination or advocates against vaccines. |
| Fraud & scams | Deceptive schemes to take money or personal data. |
| Adult nudity & sexual activity | Nudity, explicit poses, or merely *sexually suggestive* framing. Common false-positive on swimwear/fitness/lingerie creative. |
| Adult sexual exploitation | Non-consensual sexual acts depicted, advocated, or coordinated. |
| Sexual solicitation / explicit language | Facilitating sexual encounters, commercial sexual services, or porn; explicit language restricted. |
| Bullying & harassment | Copy that degrades or shames an individual. Heightened for under-18s. |
| Profanity | Any profanity in text, image, or video. |
| Violent & graphic content | Shocking, sensational, or excessively violent imagery. |
| Suicide / self-injury / eating disorders | Encouragement or graphic depiction, incl. memes and illustrations; mocking survivors. |
| Third-party IP infringement | Copyright/trademark misuse; counterfeit goods copying a name, logo, or distinctive product feature. |
| Meta IP misuse | Meta marks used outside Brand Resource Center rules. |
| Commercial exploitation of crises | Monetizing a crisis or controversial event. |
| Tobacco / nicotine / vapes | Sale or use of tobacco, nicotine, e-cigs, vaporizers, paraphernalia. Only WHO/FDA-approved cessation products allowed. |
| Weapons, ammo, explosives | Includes weapon modification accessories. |
| Hazardous goods, human body parts/fluids, historical artifacts | Sale prohibited. |
| Endangered species / live animal sales | No endangered-derived products; no P2P sale or trade of live animals. Donation, rehoming, adoption OK. |

---

## 2. Restricted — rejected only when a condition is missing

| Reason | Condition that was missing |
|---|---|
| Alcohol | 18+ age targeting, local law/industry code compliance, geo restriction (banned in some markets). |
| Dating services | Prior written permission + dating targeting rules. |
| Online gambling & gaming | Prior written permission + 18+ + local law. Applies to anything with monetary entry AND prize. |
| Cryptocurrency | Prior written permission. Covers trading platforms, monetization/reselling/swapping/staking tools. |
| Financial & insurance | 18+, regulator authorization/identity verification. Ad must not directly request PII or financial info. |
| Drugs & pharmaceuticals | Illicit/recreational = banned. Rx, OTC, cannabis-derived = written permission + geo targeting. |
| Addiction treatment (US) | LegitScript certification + Meta permission. |
| Health / weight / cosmetics | 18+ age targeting. (Claim rules in §3.) |
| Adult products & reproductive health | 18+ AND framing must be health/medical efficacy, not sexual pleasure or enhancement. |
| Social issue, electoral, political | Advertiser authorization + disclaimer. Stored in Ad Library 7 years. |
| Entertainment (trailers, TV, games) | Written permission + 18+. No excessive drugs/alcohol, adult content, profanity, gore. |
| Lead ads | Certain question types require prior written permission. |

**Reading a restricted rejection:** the creative may be entirely compliant. The missing item is
often a permission or an age gate on the ad set, not something in the video. Before descending
into creative traits, check whether approved ads in the same policy area differ by targeting
rather than by content — if they do, the finding is an account/setup finding, not a creative one.

---

## 3. Top 3 causes of "surprise" rejections on legitimate ads

### 3.1 Personal Attributes (most common)
**Rule:** ad must not assert or imply it knows a viewer's attribute.
**Covered:** race, ethnicity, religion, beliefs, age, sexual orientation/practices, gender identity, disability, physical or mental health, vulnerable financial status, voting status, trade union membership, criminal record, name.

**Heuristic:** 2nd person + attribute = reject. 3rd person description = approve. The word **"other"** is the strongest tell.

| Approved | Rejected |
|---|---|
| "Depression counseling" | "Depression getting you down?" |
| "New diabetes treatment available" | "Do you have diabetes?" |
| "Meet seniors" | "Meet **other** seniors" |
| "Date Christian singles!" | "Are you Christian?" |
| "Come meet transgender singles" | "Questioning your gender identity?" |
| "Our new creams fight wrinkles" | "Ready to upgrade your skin to look younger?" |
| "Services to clean up previous offenses" | "Are you a convicted felon?" |
| "T-shirts printed with your name" | "Billy Taylor, get this t-shirt with your name!" |
| "Find black singles today" | "Meet other black singles near you!" |
| you/your with no attribute | "Are you 18 years old?" / "Are you bankrupt?" |

**Allowed anyway:** broad location identity ("New Yorker"), passing gender/age reference, celebrity or fictional character names, PSAs about health topics that don't assert the viewer has the condition.

**Non-English note:** the rule is about grammatical person plus attribute, not about English words.
Second-person forms in the spoken line or the subtitle (Hindi *tum / tumhe / aap / aapko*,
Tamil *neenga / ungalukku*, Telugu *meeru / meeku*, Bengali *tumi / apni*, Kannada *neevu*)
followed by a state-of-being attribute — lonely, single, sad, unemployed, in debt — carry the
same trigger. Read `says` and `says_en` together; the English translation alone can lose the
person marker.

### 3.2 Health & Wellbeing claims
Rejected creative:
- Statements of inferiority about appearance, body parts, or hygiene
- Close-up pinching fat / isolating a body area
- Claiming results from a wearable product alone
- Skin whitening/bleaching causing permanent color change
- Clickbait: sensational/exaggerated language, or a specific outcome in a set timeframe with no disclaimer

Rejected claims: **cure / heal / eliminate** any of — Diabetes, Herpes, Thyroid, Psoriasis, Ebola, Cancer, Autism, Alzheimer's, Parkinson's, ALS, HIV. (Exhaustive list. *Treating or managing symptoms* is allowed.)

Allowed: before/after transformations for cosmetic products and procedures; weight products shown in use with impact, if time-to-result is stated.

No age gate needed: general fitness/wellbeing, general food incl. protein, non-permanent cosmetics (creams, makeup, hair, editing apps), dental/whitening, women's hygiene, lingerie/swimwear.

### 3.3 Unacceptable Business Practices
Four triggers:
1. Deceptive/exaggerated claims about product **success**
2. Deceptive/exaggerated claims about **health benefits**
3. **Famous person's image** + misleading tactic as engagement bait
4. Promising financial benefit by **misrepresenting** an entity, industry association, or news outlet

High-scrutiny verticals: investment/banking, health & weight loss, "free" product offers, products with non-existent functionality.
Side effect: may trigger mandatory advertiser verification (looks like a rejection, isn't one).

---

## 4. Non-content rejections

| Reason | Why |
|---|---|
| Relevance mismatch | Ad components not relevant to the product, or ad doesn't match what the landing page sells. |
| Disruptive video | Flashing screens or similar tactics. |
| Untagged branded content | Creator/publisher content featuring a business partner not tagged via the branded content tool. |
| Abusive targeting | Targeting used to discriminate, harass, provoke, disparage, or advertise predatorily. |
| EU DSA fields | Beneficiary/payor legal names missing, inaccurate, or stale while the ad runs. |
| Account integrity / inauthentic behavior | Asset-level restriction, not ad-level. |
| Cybersecurity / spam | Phishing, social engineering, malware or spyware links. |
| Agency account misuse | Multiple clients in one ad account, or reassigning an established account to a new client. |
| Data use violation | Meta ad data used to build/enrich user profiles, or transferred to an ad network, exchange, or data broker. |
| Discretionary | Meta may reject any ad for any reason at its sole discretion. |
| Not a rejection | Low-quality-but-compliant ads get delivery suppressed — reads as a performance problem, not a policy one. |

---

## 5. Remediation
1. Edit or rebuild → treated as a new ad, re-enters review.
2. Request another review in **Account Quality** (works for ads and for restricted assets).
3. Check whether the **asset** was restricted separately from the ad — separate decision, separate appeal.

---

## 6. Policy → candidate creative triggers

The hypothesis-generation table for Section 11 of the skill. For a given `rejection_reason`,
this says which facets to group the disapproved set on and which stored evidence to read. Each
row is a starting list, not a closed one — the policy text in §1–§4 and the verbatim
`rejection_message` can add hypotheses this table does not anticipate.

Facet names are the registered ones from `get_analysis_metadata` → entities. Evidence lives in
`_observations` (verbatim quote + English translation + timing) and `_timeline`
(`beats[].says`, `says_en`, `text`, `text_en`, `shows`, `role`). Fetch both with
`view(hashes=[...])` — never `analyze_video`.

| Policy (`rejection_reason`) | What in the creative usually trips it | Facets to group on | Evidence to read |
|---|---|---|---|
| Personal attributes | Second-person address plus a state-of-being attribute; the word "other"; a question that presumes the viewer's condition | `address_mode`, `hook`, `value_prop`, `emotional_driver`, `persona_archetype`, `cta` | `hook` and `problem` beats — `says` + `says_en` together; `text` / `text_en` overlays; every `_observations` row on `hook` and `address_mode` |
| Adult nudity & sexual activity | Suggestive framing, camera framing on the body, bedroom setting, sleepwear or revealing attire — no explicit content needed | `presenter_attire`, `setting`, `presenter_gender`, `production_style`, `scene_description` | `beats[].shows`; `_observations` on `presenter_attire` and `setting`; read the whole `scene_description` |
| Sexual solicitation / explicit language | Language that reads as facilitating an encounter — "meet", "talk to", "connect with" plus a gendered or intimacy cue | `value_prop`, `cta`, `emotional_driver`, `emotional_register`, `hook` | `cta` and `invitation` beats verbatim in source language; `_observations` on `value_prop` and `cta` |
| Dating services | Positioning that reads as matchmaking even when the product is not a dating app | `value_prop`, `persona_archetype`, `offer`, `cta` | `introduce-app` and `value-prop` beats; the app-store framing on `end_card` |
| Human exploitation | Earn-money-by-talking framing, host or creator recruitment with a per-hour or per-minute rate | `ad_objective_type`, `offer`, `price_metaphor`, `value_prop`, `hook` | `price` and `offer` beats; every `_observations` row carrying an amount |
| Unacceptable business practices | Income or outcome claims, "free" framing, exaggerated success, a famous face used as bait | `offer`, `price_metaphor`, `social_proof`, `value_prop` | `price`, `social-proof`, `value-prop` beats; `_observations` on `social_proof` |
| Health & wellbeing | Loneliness, depression or anxiety framed as the viewer's condition; a promised emotional outcome | `emotional_driver`, `emotional_register`, `value_prop`, `hook` | `problem` beats; `_observations` on `emotional_driver` — check §3.1 as well, these two co-fire |
| Profanity | A single word in the spoken line, the burned-in subtitle, or the on-screen text — often in the source language only | `language_spoken`, `subtitle_script`, `subtitle_style` | Every `says` and `text` field across all beats, in source language; the English translation will not carry it |
| Bullying & harassment | Copy that shames the viewer or a person on screen | `emotional_register`, `hook`, `address_mode` | `hook` and `problem` beats verbatim |
| Third-party IP infringement | Music track, film or show clip, a logo or a UI that is not the brand's | `app_ui_shown`, `production_style`, `end_card` | `beats[].shows`; `_observations` on `app_ui_shown` |
| Misinformation | A factual claim presented as verified | `value_prop`, `social_proof` | `value-prop` and `social-proof` beats |
| Violent & graphic content | Staged conflict, distress or self-harm imagery used as the hook | `scene_description`, `emotional_register`, `production_style` | `hook` beat `shows`; `scene_description` |
| Relevance mismatch | What the ad promises differs from what the app store listing or landing page delivers | `value_prop`, `offer`, `cta`, `end_card`, `ad_objective_type` | `invitation`, `cta`, `end-card` beats vs the `introduce-app` beat |
| Disruptive video | Rapid cuts, strobing, flashing overlays | `production_style`, `subtitle_style` | `_timeline` beat count against `duration` — many very short beats is the tell |
| Discretionary | Nothing stated | — | No hypothesis is supportable. Report the count and stop. |

**Two policies fire together more often than not.** Personal attributes + Health & wellbeing, and
Dating services + Sexual solicitation, are the common pairs. When a creative carries traits from
both rows, test both and report both — do not force a single winner.

---

*Policies change without notice. Health & Wellness last updated 2026-07-22; Unacceptable Business Practices 2026-03-20. Verify against transparency.meta.com before enforcing.*
