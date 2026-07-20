# Zotero Bib Skill Requirements

## Purpose

Create a Codex skill for working with a Zotero-exported BibTeX library. The skill reads a library path from `ZOTERO_BIB_FILE_PATH`, searches the library by keyword, and exports or updates selected entries in a paper bibliography file.

## Version 1 Scope

- Read the source BibTeX library from the environment variable `ZOTERO_BIB_FILE_PATH`.
- Support keyword search only.
- Do not support semantic search in v1.
- Parse BibTeX entries reliably enough to preserve full entries when exporting.
- Search all BibTeX entry text by default, including citation key and fields such as `title`, `author`, `year`, `journal`, `booktitle`, `keywords`, and `abstract`.
- Match keywords case-insensitively.
- For multiple keywords, split on whitespace and require all keywords to match.
- Show full metadata for a single entry, including author, year, title, publication, abstract, extracted file path values, DOI, URL, other parsed fields, and optional raw BibTeX.
- Show matching candidates before writing unless the user explicitly requests exporting all matches.
- Export selected matching entries into a paper `.bib` file.
- Update selected entries in a paper `.bib` file from the Zotero library.
- Support exact citation-key lookup using either `@key` or `key`.

## Source Library

- Source path must come from `ZOTERO_BIB_FILE_PATH`.
- If `ZOTERO_BIB_FILE_PATH` is unset, empty, or points to a missing file, the skill should report the problem and tell the user how to set it.
- The source file is treated as read-only.

## Target Paper Bibliography

- If the user specifies a target `.bib` file, use that file.
- If the user does not specify a target, discover `references.bib` in the current directory or one of its subdirectories.
- If no `references.bib` is found, create `./references.bib` by default.
- If multiple `references.bib` files are found, the skill should avoid guessing and ask the user which file to use.

## Export Behavior

- `export` should add entries that are not already present in the target bibliography.
- If an entry with the same citation key already exists during export, skip it and report that it was already present.
- If the user says "export all", "add all", or equivalent wording, write all matching entries without an intermediate selection step.
- Append newly exported entries to the end of the target bibliography.
- Preserve existing target bibliography entry order.

## Update Behavior

- `update` should replace target entries that have the same citation key as entries found in the Zotero library.
- If an entry requested for update is not already present in the target bibliography, report it as missing instead of adding it silently.
- Exporting new entries and updating existing entries should be separate behaviors unless the user explicitly asks for both.

## Result Display and Ranking

- Display search results as:
  `citation_key | year | author | title | venue`
- Rank entries with matches in the citation key or title first.
- Then rank by number of matched keyword occurrences across the full BibTeX entry text.
- Keep result display concise enough for a user to choose entries manually.

## File Safety

- Before modifying a target bibliography, create a backup next to it, such as `references.bib.bak`.
- Never modify the source Zotero library file.

## Script Interface

The skill should bundle a script with an interface similar to:

```bash
python scripts/zotero_bib.py search "rag evaluation"
python scripts/zotero_bib.py show smith2024
python scripts/zotero_bib.py show smith2024 --format json --bibtex
python scripts/zotero_bib.py export "rag evaluation" --target references.bib
python scripts/zotero_bib.py update smith2024 --target references.bib
```

Expected command behavior:

- `search QUERY`: search the Zotero library and print ranked candidates.
- `show KEY_OR_QUERY`: show full metadata for one entry.
- `export QUERY`: export matching entries to the target bibliography, skipping entries already present.
- `update KEY_OR_QUERY`: update matching existing entries in the target bibliography.
- `--target PATH`: override automatic `references.bib` discovery.

## User-Facing Trigger Examples

- "Search my Zotero bib for diffusion model and export to paper.bib"
- "Find entries about transformer pruning"
- "Update references.bib with @smith2024 from Zotero"
- "从 Zotero bib 里找 RAG evaluation 相关论文，导出到 refs.bib"

## Open Questions

Resolved decisions:

- Skill name: `zotero-bib`.
- Development location: current repository, under `skills/zotero-bib/`.
- Interactive selection: not included in v1. Search lists candidates; export/update uses citation keys or `--all`.
- Installation support: local use, `npx skills add`, Codex, and Claude Code.
