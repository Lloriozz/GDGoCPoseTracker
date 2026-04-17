# Fitness LLM Wiki

This folder is a Codex-friendly knowledge workspace inspired by the LLM Wiki pattern.

## Goal

Turn raw source material such as articles, PDFs, notes, and transcripts into a structured markdown wiki that can later support the chatbot's knowledge layer.

## Folders

- `raw/` - source-of-truth documents, read-only
- `wiki/` - markdown knowledge pages maintained by Codex
- `schema/` - workflow and formatting rules
- `logs/` - ingest and lint history

## Recommended workflow

1. Drop new sources directly into `raw/`.
2. Ask Codex to ingest the new sources and update the wiki.
3. Ask Codex to lint the wiki periodically.
4. Use the wiki as a retrieval-friendly knowledge layer for the chatbot.

Codex is responsible for reading each raw source and deciding whether it belongs more to meal, nutrition, workout, recovery, fasting, or multiple wiki areas.

## Important constraint

This wiki does not replace structured tools. It should not be treated as the source of truth for deterministic calculations.
