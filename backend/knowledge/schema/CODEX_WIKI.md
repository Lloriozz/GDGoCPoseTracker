# Codex Fitness LLM Wiki

An LLM Wiki workflow for the fitness chatbot backend.
Inspired by Andrej Karpathy's LLM Wiki pattern, adapted for Codex and this project.

## Purpose

This wiki is a structured, interlinked knowledge base for a Vietnamese fitness and nutrition chatbot.

Codex maintains the wiki.
The human curates sources, adds new raw material, asks questions, and decides what knowledge should be included.

This wiki is meant to improve:

- Vietnamese meal ideas and substitutions
- nutrition concepts and practical advice
- fat loss and muscle gain knowledge
- fasting knowledge
- recovery knowledge
- beginner and injury-aware workout knowledge

This wiki must not replace structured tools that already exist in the backend.

## Folder structure

```text
knowledge/
  raw/
  wiki/
    index.md
    meal/
    nutrition/
    workout/
    recovery/
    fasting/
  schema/
    CODEX_WIKI.md
  logs/
    ingest-log.md
    lint-report.md
```

### Raw folder rule

Everything under `knowledge/raw/` is immutable source material.
Codex may read those files, summarize them, compare them, and cite them, but must never edit, rename, or delete them.
`knowledge/raw/` is a mixed inbox, not a pre-sorted taxonomy.
The human should be able to drop any relevant source into `raw/` without classifying it first.
Codex is responsible for identifying whether a source belongs to meal, nutrition, workout, recovery, fasting, or multiple areas.

## System boundaries

The wiki is a knowledge layer only.

Do not use the wiki as the source of truth for:

- TDEE calculations
- macro calculations
- ingredient calorie calculations
- deterministic workout plan logic
- safety and medical red-flag logic

Those remain tool-driven.

The wiki should support explanation, grounding, retrieval, synthesis, and knowledge accumulation.

## Ingest workflow

When the user adds a new source to `knowledge/raw/` and asks you to ingest it:

1. Read the full source document.
2. Classify the source into one or more target knowledge areas:
   - meal
   - nutrition
   - workout
   - recovery
   - fasting
3. Identify the main concepts, entities, claims, protocols, and practical takeaways.
4. Create a source summary page in `knowledge/wiki/` if the source introduces substantial new information.
5. Create new concept pages when needed.
6. Update existing concept pages when the source adds useful detail, nuance, or contradiction.
7. Add wiki-links (`[[page-name]]`) between related pages.
8. Update `knowledge/wiki/index.md`.
9. Append an entry to `knowledge/logs/ingest-log.md`.
10. If the source conflicts with existing pages, record the conflict explicitly.

A single source may update many pages. That is expected.
One source may belong to multiple sections. That is normal.

## Default ingest behavior

In this project, Codex should usually ingest autonomously without pausing for approval after every source.

Only ask the user when:

- the source domain is clearly outside the intended scope
- the source is too low-quality or too ambiguous to classify safely
- the source creates a high-impact structural decision with non-obvious tradeoffs

## Page types

Use a small set of page types:

- `index` pages for section overviews
- `concept` pages for ideas such as progressive overload or calorie deficit
- `entity` pages for specific foods, methods, protocols, or named items
- `comparison` pages for tradeoffs and alternatives
- `source-summary` pages for especially important raw sources

## Page format

Every wiki page should follow this structure:

```markdown
# Page Title

**Summary**: One to two sentences describing the page.

**Page type**: concept | entity | comparison | source-summary | index

**Sources**:
- raw/path/to/source.pdf

**Last updated**: YYYY-MM-DD

---

## Key Points

- ...
- ...

## Practical Notes

- ...
- ...

## Related Pages

- [[related-page-1]]
- [[related-page-2]]
```

## Writing style

- Write wiki content in clear Vietnamese with diacritics.
- Keep claims concise and practical.
- Prefer short sections over long essays.
- Optimize for chatbot retrieval and human scanning, not academic prose.
- Avoid filler language and motivational fluff.

## Naming rules

- Use lowercase kebab-case filenames.
- Prefer stable concept names over source-specific names.
- Keep filenames readable and durable.

Examples:

- `calorie-deficit.md`
- `meal-budget-basics.md`
- `knee-friendly-lower-body.md`
- `intermittent-fasting-basics.md`

## Citation rules

- Every factual claim should trace back to at least one raw source.
- Use inline source references like `(source: raw/file-name.pdf)` or the correct raw path if nested later.
- If multiple sources support the same claim, cite the strongest or most direct one.
- If sources disagree, note the disagreement explicitly instead of collapsing it.
- If a statement seems useful but is weakly supported, mark it as needing verification.

## Question answering behavior

When asked a knowledge question using this wiki:

1. Read `knowledge/wiki/index.md` first.
2. Navigate to the most relevant pages.
3. Synthesize an answer from the wiki before consulting raw files again.
4. Cite the relevant wiki pages in the answer when appropriate.
5. If the answer is missing from the wiki but present in raw sources, offer to ingest or update the wiki.
6. If the answer is uncertain, say so clearly.

Good answers should be folded back into the wiki when they add lasting value.

## Lint workflow

When the user asks to lint or audit the wiki:

- Check for contradictions between pages.
- Find orphan pages with weak or no inbound links.
- Identify concepts mentioned repeatedly that lack their own page.
- Flag outdated claims if newer sources disagree.
- Check whether pages follow the required format.
- Detect overlapping pages that should be merged or cross-linked more clearly.
- Note any unsupported claims or weak citations.
- Append a concise report to `knowledge/logs/lint-report.md`.

## Retrieval-oriented guidance

Because this wiki will support a chatbot:

- favor small, well-linked pages over giant catch-all pages
- keep summaries strong and explicit
- include practical notes that are useful in answers
- connect related meal, nutrition, workout, recovery, and fasting concepts
- preserve Vietnamese context when the knowledge is culturally specific

## Rules

- Never modify anything under `knowledge/raw/`.
- Always update `knowledge/wiki/index.md` after meaningful changes.
- Always append a short entry to `knowledge/logs/ingest-log.md` after ingest.
- Always classify mixed raw sources yourself instead of asking the user to pre-sort them unless the source is clearly ambiguous or out of scope.
- Do not overwrite contradictions silently.
- Do not let wiki content override deterministic tool outputs.
- If uncertain, preserve the ambiguity and mark it clearly.
