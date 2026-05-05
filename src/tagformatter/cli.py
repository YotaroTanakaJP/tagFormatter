from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .csv_loader import CsvFormatError, load_tag_rows, write_template_csv
from .flac_writer import apply_rows
from .models import ProcessError, TagRow
from .tag_mapping import DEFAULT_TAG_MAPPINGS


DISC_IN_PATH_PATTERN = re.compile(r"\bcd\s*([0-9]+)\b", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply FLAC tags from a CSV file")
    parser.add_argument("--csv", dest="csv_path", type=Path, help="Path to the CSV file")
    parser.add_argument("--base-dir", dest="base_dir", type=Path, default=None, help="Base directory for relative file_path values")
    parser.add_argument("--album-dir", dest="album_dir", type=Path, default=None, help="Album directory whose descendant .flac files should be processed")
    parser.add_argument("--disc", dest="disc_number", type=int, default=None, help="Disc number to select from the CSV when using --album-dir")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing FLAC tags")
    parser.add_argument(
        "--write-template",
        dest="template_path",
        type=Path,
        default=None,
        help="Write a template CSV to the given path and exit",
    )
    return parser


def infer_disc_number(album_dir: Path) -> int | None:
    for part in reversed(album_dir.parts):
        match = DISC_IN_PATH_PATTERN.search(part)
        if match is not None:
            return int(match.group(1))
    return None


def select_rows_for_album(rows: list[TagRow], disc_number: int | None) -> tuple[list[TagRow], list[ProcessError]]:
    if disc_number is None:
        distinct_discs = sorted({row.disc_number for row in rows if row.disc_number is not None})
        if len(distinct_discs) == 1:
            disc_number = distinct_discs[0]

    if disc_number is None:
        selected_rows = rows
    else:
        selected_rows = [row for row in rows if row.disc_number == disc_number]

    if not selected_rows:
        return [], [ProcessError(source_line=0, file_path="", message="No CSV rows matched the selected album/disc")]

    return selected_rows, []


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.template_path is not None:
        write_template_csv(args.template_path, DEFAULT_TAG_MAPPINGS)
        print(f"Template written: {args.template_path}")
        return 0

    if args.csv_path is None:
        print("argument error: --csv is required unless --write-template is used", file=sys.stderr)
        return 2

    if args.album_dir is not None and args.base_dir is not None:
        print("argument error: --album-dir and --base-dir cannot be used together", file=sys.stderr)
        return 2

    csv_path = args.csv_path.resolve()
    if not csv_path.exists():
        print(f"argument error: CSV file not found: {csv_path}", file=sys.stderr)
        return 2

    try:
        rows, csv_errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)
    except CsvFormatError as exc:
        print(f"CSV format error: {exc}", file=sys.stderr)
        return 2

    processing_rows = rows
    selection_errors: list[ProcessError] = []
    album_dir = args.album_dir.resolve() if args.album_dir is not None else None
    if album_dir is not None:
        if not album_dir.exists() or not album_dir.is_dir():
            print(f"argument error: album directory not found: {album_dir}", file=sys.stderr)
            return 2
        disc_number = args.disc_number if args.disc_number is not None else infer_disc_number(album_dir)
        processing_rows, selection_errors = select_rows_for_album(rows, disc_number)

    results, processing_errors = apply_rows(
        processing_rows,
        definitions=DEFAULT_TAG_MAPPINGS,
        csv_path=csv_path,
        base_dir=args.base_dir.resolve() if args.base_dir is not None else None,
        album_dir=album_dir,
        dry_run=args.dry_run,
    )

    for result in results:
        action = "DRY-RUN" if result.dry_run else "UPDATED"
        changes: list[str] = []
        for key, values in sorted(result.updated_tags.items()):
            changes.append(f"set {key}={' ; '.join(values)}")
        for key in sorted(result.cleared_tags):
            changes.append(f"clear {key}")
        changed = ", ".join(changes) if changes else "no tag updates"
        print(f"[{action}] line {result.row.source_line}: {result.resolved_path} -> {changed}")

    all_errors = [*csv_errors, *selection_errors, *processing_errors]
    for error in all_errors:
        print(f"[ERROR] line {error.source_line}: {error.file_path} -> {error.message}", file=sys.stderr)

    print(f"Processed: {len(results)} success, {len(all_errors)} error")
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
