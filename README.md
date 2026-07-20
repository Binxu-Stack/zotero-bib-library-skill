# Zotero Bib Skill

Portable agent skill for searching a Zotero-exported BibTeX library and exporting or updating entries in a paper bibliography.

## Background

Zotero is often the source of truth for a research library, while papers, notes, and agent workflows usually need plain BibTeX entries. Zotero can use the Better BibTeX plugin to export a stable `.bib` file, which makes the library accessible to command-line tools and coding agents.

This skill treats the generated BibTeX file as the interface to Zotero. By reading `ZOTERO_BIB_FILE_PATH`, an agent can search the exported library, inspect candidate references, and copy or refresh selected entries in a paper's `references.bib` without directly controlling the Zotero application.

## Layout

The skill lives at:

```text
skills/zotero-bib/
```

This repository layout works with the `npx skills` CLI because it can discover skills from repositories containing `SKILL.md` files under `skills/<name>/`.

## Prerequisite

Export your Zotero library to BibTeX and set:

```bash
export ZOTERO_BIB_FILE_PATH=/absolute/path/to/zotero-library.bib
```

## Use Locally Without Installing

From this repository:

```bash
python3 skills/zotero-bib/scripts/zotero_bib.py search "rag evaluation"
python3 skills/zotero-bib/scripts/zotero_bib.py show smith2024
python3 skills/zotero-bib/scripts/zotero_bib.py export smith2024 --target references.bib
python3 skills/zotero-bib/scripts/zotero_bib.py update smith2024 --target references.bib
```

Show full metadata for one entry:

```bash
python3 skills/zotero-bib/scripts/zotero_bib.py show "@smith2024" --bibtex
python3 skills/zotero-bib/scripts/zotero_bib.py show smith2024 --format json --bibtex
```

The `show` command prints author, year, title, publication, abstract, extracted file paths, DOI, URL, other parsed fields, and optionally the full raw BibTeX entry.

For keyword queries with multiple matches, export/update stops before writing. Use exact keys or pass `--all` only when you want every match:

```bash
python3 skills/zotero-bib/scripts/zotero_bib.py export "rag evaluation" --key smith2024 --key lee2023
python3 skills/zotero-bib/scripts/zotero_bib.py export "rag evaluation" --all
```

## Install With `npx skills`

From a local clone:

```bash
npx skills add . --skill zotero-bib -a codex -y
npx skills add . --skill zotero-bib -a claude-code -y
```

Install for both agents:

```bash
npx skills add . --skill zotero-bib -a codex -a claude-code -y
```

If you are not running the command from the repository root, replace `.` with the path to your local clone.

After pushing this repo to GitHub, replace `.` with `owner/repo`:

```bash
npx skills add Binxu-Stack/zotero-bib-library-skill --skill zotero-bib -a codex -a claude-code -y
```

Add `--global` if you want the skill available outside the current project.

## Manual Install

Codex user install:

```bash
mkdir -p ~/.codex/skills
cp -R skills/zotero-bib ~/.codex/skills/
```

Claude Code user install:

```bash
mkdir -p ~/.claude/skills
cp -R skills/zotero-bib ~/.claude/skills/
```

Project-local installs are best handled by `npx skills`, which chooses the correct agent-specific project directory.

Manual project install if needed:

```bash
mkdir -p .codex/skills .claude/skills
cp -R skills/zotero-bib .codex/skills/
cp -R skills/zotero-bib .claude/skills/
```
