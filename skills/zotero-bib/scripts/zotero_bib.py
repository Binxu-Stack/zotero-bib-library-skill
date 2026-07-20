#!/usr/bin/env python3
"""Search, export, and update BibTeX entries from a Zotero library."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


SOURCE_ENV = "ZOTERO_BIB_FILE_PATH"


@dataclass(frozen=True)
class BibEntry:
    entry_type: str
    key: str
    text: str
    start: int
    end: int
    fields: dict[str, str]

    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def year(self) -> str:
        return self.fields.get("year", "")

    @property
    def author(self) -> str:
        return self.fields.get("author", "")

    @property
    def venue(self) -> str:
        for field in ("journal", "journaltitle", "booktitle", "conference", "publisher"):
            if self.fields.get(field):
                return self.fields[field]
        return ""

    @property
    def abstract(self) -> str:
        return self.fields.get("abstract", "")

    @property
    def search_text(self) -> str:
        return f"{self.key}\n{self.text}"


def fail(message: str, code: int = 1) -> None:
    sys.stdout.flush()
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_source_library() -> tuple[Path, str]:
    raw_path = os.environ.get(SOURCE_ENV, "").strip()
    if not raw_path:
        fail(f"{SOURCE_ENV} is not set. Set it to your Zotero-exported .bib file.")
    path = Path(raw_path).expanduser()
    if not path.exists():
        fail(f"{SOURCE_ENV} points to a missing file: {path}")
    if not path.is_file():
        fail(f"{SOURCE_ENV} does not point to a file: {path}")
    return path, path.read_text(encoding="utf-8")


def parse_bib_entries(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    index = 0
    while index < len(text):
        at = text.find("@", index)
        if at == -1:
            break

        type_match = re.match(r"@([A-Za-z]+)\s*([\{\(])", text[at:])
        if not type_match:
            index = at + 1
            continue

        entry_type = type_match.group(1).lower()
        opener = type_match.group(2)
        closer = "}" if opener == "{" else ")"
        body_start = at + type_match.end()
        end = find_matching_delimiter(text, body_start - 1, opener, closer)
        if end is None:
            index = at + 1
            continue

        comma = find_top_level_comma(text, body_start, end)
        if comma is None:
            index = end + 1
            continue

        key = text[body_start:comma].strip()
        if not key or any(char.isspace() for char in key):
            index = end + 1
            continue

        entry_text = text[at : end + 1].strip()
        fields = parse_fields(text[comma + 1 : end])
        entries.append(
            BibEntry(
                entry_type=entry_type,
                key=key,
                text=entry_text,
                start=at,
                end=end + 1,
                fields=fields,
            )
        )
        index = end + 1
    return entries


def find_matching_delimiter(
    text: str, opener_index: int, opener: str, closer: str
) -> int | None:
    depth = 0
    quote = False
    escaped = False
    for pos in range(opener_index, len(text)):
        char = text[pos]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quote = not quote
            continue
        if quote:
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return pos
    return None


def find_top_level_comma(text: str, start: int, end: int) -> int | None:
    brace_depth = 0
    paren_depth = 0
    quote = False
    escaped = False
    for pos in range(start, end):
        char = text[pos]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quote = not quote
            continue
        if quote:
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(0, brace_depth - 1)
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char == "," and brace_depth == 0 and paren_depth == 0:
            return pos
    return None


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pos = 0
    while pos < len(body):
        while pos < len(body) and body[pos] in " \t\r\n,":
            pos += 1
        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", body[pos:])
        if not match:
            pos += 1
            continue
        name = match.group(1).lower()
        value_start = pos + match.end()
        value_end = find_field_value_end(body, value_start)
        raw_value = body[value_start:value_end].strip()
        fields[name] = normalize_value(raw_value)
        pos = value_end + 1
    return fields


def find_field_value_end(body: str, start: int) -> int:
    brace_depth = 0
    paren_depth = 0
    quote = False
    escaped = False
    pos = start
    while pos < len(body):
        char = body[pos]
        if escaped:
            escaped = False
            pos += 1
            continue
        if char == "\\":
            escaped = True
            pos += 1
            continue
        if char == '"':
            quote = not quote
            pos += 1
            continue
        if not quote:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth = max(0, brace_depth - 1)
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth = max(0, paren_depth - 1)
            elif char == "," and brace_depth == 0 and paren_depth == 0:
                return pos
        pos += 1
    return len(body)


def normalize_value(raw_value: str) -> str:
    value = raw_value.strip()
    changed = True
    while changed and len(value) >= 2:
        changed = False
        pairs = {"{": "}", '"': '"'}
        if value[0] in pairs and value[-1] == pairs[value[0]]:
            value = value[1:-1].strip()
            changed = True
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[{}]", "", value)
    return value.strip()


def split_keywords(query: str) -> list[str]:
    return [part.lower() for part in re.findall(r"\S+", query) if part.strip()]


def key_from_query(query: str, entries_by_key: dict[str, BibEntry]) -> str | None:
    stripped = query.strip()
    if not stripped or any(char.isspace() for char in stripped):
        return None
    key = stripped[1:] if stripped.startswith("@") else stripped
    if stripped.startswith("@") or key in entries_by_key:
        return key
    return None


def search_entries(entries: list[BibEntry], query: str) -> list[tuple[BibEntry, int]]:
    entries_by_key = {entry.key: entry for entry in entries}
    exact_key = key_from_query(query, entries_by_key)
    if exact_key is not None:
        entry = entries_by_key.get(exact_key)
        return [(entry, 999999)] if entry else []

    keywords = split_keywords(query)
    if not keywords:
        return []

    results: list[tuple[BibEntry, int]] = []
    for entry in entries:
        haystack = entry.search_text.lower()
        if not all(keyword in haystack for keyword in keywords):
            continue
        title_key_text = f"{entry.key}\n{entry.title}".lower()
        title_key_hits = sum(title_key_text.count(keyword) for keyword in keywords)
        all_hits = sum(haystack.count(keyword) for keyword in keywords)
        score = title_key_hits * 1000 + all_hits
        results.append((entry, score))

    results.sort(key=lambda item: (item[1], item[0].year, item[0].key), reverse=True)
    return results


def trim(value: str, max_len: int) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."


def display_author(author: str) -> str:
    if not author:
        return ""
    parts = [part.strip() for part in re.split(r"\s+and\s+", author) if part.strip()]
    if len(parts) <= 1:
        return trim(author, 28)
    return trim(f"{parts[0]} et al.", 28)


def entry_to_record(index: int, entry: BibEntry, score: int) -> dict[str, object]:
    return {
        "index": index,
        "key": entry.key,
        "type": entry.entry_type,
        "year": entry.year,
        "author": display_author(entry.author),
        "title": entry.title,
        "venue": entry.venue,
        "score": score,
    }


def extract_filepaths(file_value: str) -> list[str]:
    if not file_value:
        return []

    paths: list[str] = []
    for item in [part.strip() for part in file_value.split(";") if part.strip()]:
        path = extract_filepath_item(item)
        if path and path not in paths:
            paths.append(path)
    return paths


def extract_filepath_item(item: str) -> str:
    parsed = urlparse(item)
    if parsed.scheme == "file":
        return unquote(parsed.path)

    parts = item.split(":")
    if len(parts) >= 3:
        if parts[0] == "":
            candidate = ":".join(parts[1:-1])
        elif looks_like_path(parts[0]):
            candidate = ":".join(parts[:-1])
        else:
            candidate = ":".join(parts[1:-1])
    elif len(parts) == 2:
        candidate = parts[0] if looks_like_path(parts[0]) else parts[1]
    else:
        candidate = item

    return unquote(candidate.strip())


def looks_like_path(value: str) -> bool:
    return (
        value.startswith("/")
        or value.startswith("~")
        or value.startswith(".")
        or bool(re.match(r"^[A-Za-z]:[\\/]", value))
    )


def detail_record(entry: BibEntry, include_bibtex: bool) -> dict[str, object]:
    record: dict[str, object] = {
        "key": entry.key,
        "type": entry.entry_type,
        "author": entry.author,
        "year": entry.year,
        "title": entry.title,
        "publication": entry.venue,
        "abstract": entry.abstract,
        "filepaths": extract_filepaths(entry.fields.get("file", "")),
        "doi": entry.fields.get("doi", ""),
        "url": entry.fields.get("url", ""),
        "fields": entry.fields,
    }
    if include_bibtex:
        record["bibtex"] = entry.text
    return record


def print_detail(entry: BibEntry, output_format: str, include_bibtex: bool) -> None:
    record = detail_record(entry, include_bibtex)
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return

    print(f"Citation key: {entry.key}")
    print(f"Type: {entry.entry_type}")
    print_wrapped("Author", entry.author)
    print_wrapped("Year", entry.year)
    print_wrapped("Title", entry.title)
    print_wrapped("Publication", entry.venue)
    print_wrapped("Abstract", entry.abstract)

    filepaths = record["filepaths"]
    if filepaths:
        print("Filepath:")
        for path in filepaths:
            print(f"  {path}")
    else:
        print_wrapped("Filepath", "")

    for label, field in (("DOI", "doi"), ("URL", "url")):
        if entry.fields.get(field):
            print_wrapped(label, entry.fields[field])

    shown = {
        "author",
        "year",
        "title",
        "journal",
        "journaltitle",
        "booktitle",
        "conference",
        "publisher",
        "abstract",
        "file",
        "doi",
        "url",
    }
    extra_fields = [(name, value) for name, value in entry.fields.items() if name not in shown]
    if extra_fields:
        print("\nFields:")
        for name, value in extra_fields:
            print_wrapped(name, value, indent="  ")

    if include_bibtex:
        print("\nBibTeX:")
        print(entry.text)


def print_wrapped(label: str, value: str, indent: str = "") -> None:
    text = value.strip() if value else ""
    prefix = f"{indent}{label}: "
    if not text:
        print(prefix)
        return
    wrapped = textwrap.fill(
        text,
        width=100,
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    )
    print(wrapped)


def print_results(results: list[tuple[BibEntry, int]], output_format: str, limit: int) -> None:
    limited = results[:limit]
    if output_format == "json":
        records = [entry_to_record(i + 1, entry, score) for i, (entry, score) in enumerate(limited)]
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return

    if not limited:
        print("No matches.")
        return

    print("index | citation_key | year | author | title | venue")
    print("----- | ------------ | ---- | ------ | ----- | -----")
    for i, (entry, score) in enumerate(limited, start=1):
        author = display_author(entry.author)
        print(
            f"{i} | {entry.key} | {trim(entry.year, 6)} | "
            f"{trim(author, 28)} | {trim(entry.title, 72)} | {trim(entry.venue, 36)}"
        )
    if len(results) > limit:
        print(f"... {len(results) - limit} more matches. Increase --limit to show more.")


def discover_target(target_arg: str | None, create_if_missing: bool) -> Path:
    if target_arg:
        return Path(target_arg).expanduser()

    cwd = Path.cwd()
    matches = sorted(path for path in cwd.rglob("references.bib") if path.is_file())
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print("Multiple references.bib files found:", file=sys.stderr)
        for path in matches:
            print(f"  {path}", file=sys.stderr)
        fail("specify the target bibliography with --target.")

    if create_if_missing:
        return cwd / "references.bib"
    fail("no references.bib found to update. Specify --target or export first.")


def make_backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name(path.name + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)
        return backup

    index = 1
    while True:
        numbered = path.with_name(f"{path.name}.bak.{index}")
        if not numbered.exists():
            shutil.copy2(path, numbered)
            return numbered
        index += 1


def read_target_entries(path: Path) -> tuple[str, list[BibEntry], dict[str, BibEntry]]:
    if not path.exists():
        return "", [], {}
    text = path.read_text(encoding="utf-8")
    entries = parse_bib_entries(text)
    by_key: dict[str, BibEntry] = {}
    for entry in entries:
        by_key.setdefault(entry.key, entry)
    return text, entries, by_key


def resolve_entries(
    entries: list[BibEntry],
    query: str | None,
    keys: list[str] | None,
    all_matches: bool,
    ambiguous_action: str,
) -> list[BibEntry]:
    entries_by_key = {entry.key: entry for entry in entries}
    if keys:
        selected: list[BibEntry] = []
        missing: list[str] = []
        for key in keys:
            normalized = key[1:] if key.startswith("@") else key
            entry = entries_by_key.get(normalized)
            if entry:
                selected.append(entry)
            else:
                missing.append(key)
        if missing:
            fail(f"citation key(s) not found in Zotero library: {', '.join(missing)}")
        return selected

    if query is None:
        fail("provide a query or one or more --key values.")

    results = search_entries(entries, query)
    if not results:
        fail(f"no Zotero entries matched: {query}")
    if all_matches or len(results) == 1:
        return [entry for entry, _score in results]

    print_results(results, "text", 20)
    fail(
        f"{ambiguous_action} would modify {len(results)} entries. "
        "Rerun with --all or explicit --key values.",
        code=2,
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_entries(target_text: str, entries: Iterable[BibEntry]) -> str:
    additions = [entry.text.strip() for entry in entries]
    if not additions:
        return target_text
    text = target_text
    if text and not text.endswith("\n"):
        text += "\n"
    if text.strip():
        text += "\n"
    text += "\n\n".join(additions).strip() + "\n"
    return text


def command_search(args: argparse.Namespace) -> int:
    _source_path, source_text = load_source_library()
    entries = parse_bib_entries(source_text)
    results = search_entries(entries, args.query)
    print_results(results, args.format, args.limit)
    return 0 if results else 1


def command_show(args: argparse.Namespace) -> int:
    _source_path, source_text = load_source_library()
    entries = parse_bib_entries(source_text)
    results = search_entries(entries, args.query)
    if not results:
        fail(f"no Zotero entries matched: {args.query}")
    if len(results) > 1 and not args.first:
        print_results(results, "text", args.limit)
        fail(
            "show needs one entry. Rerun with an exact citation key or pass --first.",
            code=2,
        )

    entry = results[0][0]
    print_detail(entry, args.format, args.bibtex)
    return 0


def command_export(args: argparse.Namespace) -> int:
    _source_path, source_text = load_source_library()
    source_entries = parse_bib_entries(source_text)
    selected = resolve_entries(source_entries, args.query, args.key, args.all, "export")

    target = discover_target(args.target, create_if_missing=True)
    target_text, _target_entries, target_by_key = read_target_entries(target)

    new_entries = [entry for entry in selected if entry.key not in target_by_key]
    skipped = [entry.key for entry in selected if entry.key in target_by_key]
    if not new_entries:
        print(f"No new entries to export to {target}.")
        if skipped:
            print(f"Already present: {', '.join(skipped)}")
        return 0

    backup = make_backup(target)
    updated_text = append_entries(target_text, new_entries)
    write_text(target, updated_text)

    print(f"Exported {len(new_entries)} entr{'y' if len(new_entries) == 1 else 'ies'} to {target}.")
    if backup:
        print(f"Backup created: {backup}")
    if skipped:
        print(f"Skipped existing keys: {', '.join(skipped)}")
    return 0


def command_update(args: argparse.Namespace) -> int:
    _source_path, source_text = load_source_library()
    source_entries = parse_bib_entries(source_text)
    selected = resolve_entries(source_entries, args.query, args.key, args.all, "update")

    target = discover_target(args.target, create_if_missing=False)
    if not target.exists():
        fail(f"target bibliography does not exist: {target}")
    target_text, _target_entries, target_by_key = read_target_entries(target)

    selected_by_key = {entry.key: entry for entry in selected}
    replace_keys = [key for key in selected_by_key if key in target_by_key]
    missing = [key for key in selected_by_key if key not in target_by_key]

    if not replace_keys:
        print(f"No existing entries to update in {target}.")
        if missing:
            print(f"Missing from target: {', '.join(missing)}")
        return 0

    replacements = []
    for key in replace_keys:
        target_entry = target_by_key[key]
        source_entry = selected_by_key[key]
        replacements.append((target_entry.start, target_entry.end, source_entry.text.strip()))
    replacements.sort(reverse=True)

    updated_text = target_text
    for start, end, replacement in replacements:
        updated_text = updated_text[:start] + replacement + updated_text[end:]

    backup = make_backup(target)
    write_text(target, updated_text)

    print(f"Updated {len(replace_keys)} entr{'y' if len(replace_keys) == 1 else 'ies'} in {target}.")
    if backup:
        print(f"Backup created: {backup}")
    if missing:
        print(f"Missing from target, not added: {', '.join(missing)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search, export, and update BibTeX entries from ZOTERO_BIB_FILE_PATH."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="search Zotero BibTeX entries")
    search.add_argument("query", help="keyword query or citation key")
    search.add_argument("--limit", type=int, default=20, help="maximum results to display")
    search.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    search.set_defaults(func=command_search)

    show = subparsers.add_parser("show", help="show full metadata for one Zotero BibTeX entry")
    show.add_argument("query", help="citation key or keyword query resolving to one entry")
    show.add_argument("--limit", type=int, default=20, help="maximum candidates to display on ambiguity")
    show.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    show.add_argument(
        "--bibtex",
        action="store_true",
        help="include the full raw BibTeX entry in the output",
    )
    show.add_argument(
        "--first",
        action="store_true",
        help="show the top-ranked match when a keyword query matches multiple entries",
    )
    show.set_defaults(func=command_show)

    export = subparsers.add_parser("export", help="export entries to a paper bibliography")
    export.add_argument("query", nargs="?", help="keyword query or citation key")
    export.add_argument("--target", help="target .bib file; defaults to discovered references.bib")
    export.add_argument("--all", action="store_true", help="export all keyword matches")
    export.add_argument(
        "--key",
        action="append",
        help="citation key to export; repeat for multiple keys",
    )
    export.set_defaults(func=command_export)

    update = subparsers.add_parser("update", help="update existing paper bibliography entries")
    update.add_argument("query", nargs="?", help="keyword query or citation key")
    update.add_argument("--target", help="target .bib file; defaults to discovered references.bib")
    update.add_argument("--all", action="store_true", help="update all keyword matches already present")
    update.add_argument(
        "--key",
        action="append",
        help="citation key to update; repeat for multiple keys",
    )
    update.set_defaults(func=command_update)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
