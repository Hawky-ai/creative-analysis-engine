# Focus brief — <brand>

Filled in WITH THE BRAND TEAM before the first extraction run, and updated whenever
review feedback reveals a gap. Everything listed here is appended to the extraction
prompt as a `FOCUS:` block and treated as REQUIRED output for every creative.

Ask the team these, in this order:

1. **What decisions will you make from this?** (casting? offer testing? script/hook
   testing? budget reallocation? design briefs for the next batch?)
2. **What attributes do you already track by hand** in sheets/QA docs? Those are
   mandatory facets — if the extraction doesn't emit them, it can't replace the sheet.
3. **What have you argued about internally** with no data to settle it? Those are the
   highest-value facets.
4. **Anything you must NOT infer** (compliance, brand-safety, or sensitivity limits).

## FOCUS (appended verbatim to the prompt)

```
FOCUS: <attribute> — <why it matters / what decision it feeds>
FOCUS: <attribute> — <...>
```

## Out of scope

- <attributes the team explicitly does not want inferred>

> Note on people-attributes: casting/representation attributes (skin tone, age band,
> attire, hair) are recorded ONLY as neutral, visible, fixed-scale descriptors to inform
> casting decisions. Never infer ethnicity, caste, religion, region-of-origin or class,
> and never make attractiveness judgments. See `prompts/PROMPT_DESIGN.md` §12.
