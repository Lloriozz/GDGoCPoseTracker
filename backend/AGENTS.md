# Repo Guidance

This backend contains a structured `knowledge/` workspace for an LLM Wiki workflow.

When the user asks to ingest new research, articles, PDFs, notes, or to lint/audit the wiki:

1. Read and follow `knowledge/schema/CODEX_WIKI.md`.
2. Never modify anything under `knowledge/raw/`.
3. Maintain `knowledge/wiki/index.md` and the files under `knowledge/logs/`.
4. Treat `knowledge/raw/` as a single inbox of mixed sources and classify each source into the appropriate wiki section during ingest.

Important system boundaries for this repo:

- The wiki is a knowledge layer only.
- Tools remain the source of truth for:
  - TDEE and macro calculations
  - ingredient calorie and macro calculations
  - workout plan rule logic
  - safety logic
- The wiki should improve:
  - Vietnamese meal ideas
  - nutrition concepts
  - fat loss / muscle gain guidance
  - fasting knowledge
  - recovery and beginner workout knowledge

If a new source conflicts with existing wiki content, preserve the conflict explicitly instead of silently overwriting it.
