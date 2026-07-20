---
name: zotero-bib
description: Search and manage entries from a Zotero-exported BibTeX library whose path is stored in ZOTERO_BIB_FILE_PATH. Use when the user asks to find papers or BibTeX terms by keyword, inspect full paper metadata such as author, year, title, publication, abstract, and file path, look up citation keys, export matching entries into a paper references.bib file, or update existing paper bibliography entries from Zotero. Supports keyword search and citation-key lookup for .bib files; semantic search is intentionally out of scope for v1.
---

# Zotero Bib

## Overview

Use this skill to search a Zotero-exported `.bib` library and copy selected entries into the bibliography for the current paper. The source library must be identified by the `ZOTERO_BIB_FILE_PATH` environment variable and must be treated as read-only.

The bundled helper is dependency-free:

```bash
python3 scripts/zotero_bib.py search "rag evaluation"
```

When the skill is installed, run the script from the installed skill directory. In conversation, prefer describing the action and let the agent locate this skill's `scripts/zotero_bib.py`.

## Workflow

1. Verify `ZOTERO_BIB_FILE_PATH` is set and points to the Zotero library. The script reports this clearly when it is missing.
2. Search first when the user asks to find references, explore candidates, or is vague about which entry to export.
3. Use `show` when the user asks for full information about one paper or citation key.
4. Export by exact citation key when the user selected entries from search results.
5. Use `--all` only when the user explicitly asks to export or update all matching entries.
6. Use `update` only for entries that should already exist in the target paper bibliography.

## Search

Search uses keyword matching only. It is case-insensitive, searches the citation key plus all entry text, splits multiple keywords on whitespace, and requires every keyword to appear.

```bash
python3 scripts/zotero_bib.py search "diffusion model"
python3 scripts/zotero_bib.py search "@smith2024"
python3 scripts/zotero_bib.py search "smith2024"
python3 scripts/zotero_bib.py search "rag evaluation" --format json
```

Display results as `index | citation_key | year | author | title | venue`. Results matching citation key or title rank first, then entries with more keyword occurrences.

## Show

Show full metadata for one entry, including author, year, title, publication, abstract, extracted file paths, DOI, URL, other parsed fields, and optionally the raw BibTeX entry.

```bash
python3 scripts/zotero_bib.py show smith2024
python3 scripts/zotero_bib.py show "@smith2024" --bibtex
python3 scripts/zotero_bib.py show "rag evaluation" --first
python3 scripts/zotero_bib.py show smith2024 --format json --bibtex
```

For keyword queries with multiple matches, `show` prints candidates and exits without guessing. Use an exact citation key, or pass `--first` only when the user explicitly wants the top-ranked match.

## Target Bibliography

Use a user-specified target when provided:

```bash
python3 scripts/zotero_bib.py export smith2024 --target paper.bib
```

If no target is specified, discover `references.bib` in the current directory or its subdirectories. If none is found, create `./references.bib` for export. If multiple `references.bib` files are found, stop and ask the user which target to use.

## Export

Export appends new entries to the target bibliography and preserves the existing target order. Existing citation keys are skipped and reported.

Safe default:

```bash
python3 scripts/zotero_bib.py export smith2024
python3 scripts/zotero_bib.py export "rag evaluation" --key smith2024 --key lee2023
```

Bulk export only when explicitly requested by the user:

```bash
python3 scripts/zotero_bib.py export "rag evaluation" --all
```

For a keyword query with multiple matches and no `--all` or `--key`, the script prints candidates and exits without modifying files.

## Update

Update replaces existing target entries with the corresponding Zotero library entries. It does not add missing entries silently.

```bash
python3 scripts/zotero_bib.py update smith2024
python3 scripts/zotero_bib.py update "rag evaluation" --key smith2024
python3 scripts/zotero_bib.py update "rag evaluation" --all
```

Before modifying an existing target bibliography, the script creates a backup next to it, using `references.bib.bak` or a numbered suffix if that backup already exists.

## Common User Requests

- "Search my Zotero bib for diffusion model and export to paper.bib"
- "Find entries about transformer pruning"
- "Show full info for @smith2024, including abstract and filepath"
- "Update references.bib with @smith2024 from Zotero"
- "从 Zotero bib 里找 RAG evaluation 相关论文，导出到 refs.bib"
