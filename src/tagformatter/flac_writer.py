from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping

from mutagen.flac import FLAC, FLACNoHeaderError

from .models import ProcessError, ProcessResult, TagOperation, TagRow
from .tag_mapping import TagDefinition


TRACK_NUMBER_PATTERN = re.compile(r"^\s*(\d{1,3})\b")


def resolve_audio_path(file_path_value: str, base_dir: Path | None, csv_path: Path) -> Path:
    candidate = Path(file_path_value)
    if candidate.is_absolute():
        return candidate
    if base_dir is not None:
        return (base_dir / candidate).resolve()
    return (csv_path.parent / candidate).resolve()


def discover_album_files(album_dir: Path) -> list[Path]:
    return sorted((path for path in album_dir.rglob("*.flac") if path.is_file()), key=_album_sort_key)


def _album_sort_key(path: Path) -> tuple[int, int, str]:
    track_number = extract_track_number_from_name(path.name)
    if track_number is None:
        return (1, 0, str(path).casefold())
    return (0, track_number, str(path).casefold())


def extract_track_number_from_name(filename: str) -> int | None:
    match = TRACK_NUMBER_PATTERN.match(filename)
    if match is None:
        return None
    return int(match.group(1))


def build_album_track_map(album_dir: Path, expected_track_numbers: Iterable[int]) -> dict[int, Path]:
    flac_files = discover_album_files(album_dir)
    if not flac_files:
        raise ValueError(f"No .flac files found under album directory: {album_dir}")

    numbered_files: dict[int, Path] = {}
    all_files_have_track_numbers = True
    for path in flac_files:
        track_number = extract_track_number_from_name(path.name)
        if track_number is None:
            all_files_have_track_numbers = False
            break
        if track_number in numbered_files:
            all_files_have_track_numbers = False
            break
        numbered_files[track_number] = path

    expected_numbers = sorted(set(expected_track_numbers))
    if all_files_have_track_numbers:
        return numbered_files

    contiguous_numbers = list(range(1, len(expected_numbers) + 1))
    if expected_numbers == contiguous_numbers and len(flac_files) == len(expected_numbers):
        return {track_number: path for track_number, path in zip(expected_numbers, flac_files)}

    raise ValueError(
        "Could not infer track-to-file mapping from album directory; use filenames that start with track numbers or provide file_path"
    )


def resolve_row_path(
    row: TagRow,
    csv_path: Path,
    base_dir: Path | None = None,
    album_track_map: Mapping[int, Path] | None = None,
) -> Path:
    if album_track_map is not None:
        if row.track_number is None:
            raise ValueError("Track column is required when using --album-dir")
        resolved_path = album_track_map.get(row.track_number)
        if resolved_path is None:
            raise FileNotFoundError(f"No FLAC file mapped for track {row.track_number}")
        return resolved_path

    if row.file_path is None:
        raise ValueError("file_path is required unless --album-dir is used")

    return resolve_audio_path(row.file_path, base_dir=base_dir, csv_path=csv_path)


def _apply_tags_to_path(
    resolved_path: Path,
    row: TagRow,
    definitions: Mapping[str, TagDefinition],
    dry_run: bool = False,
) -> ProcessResult:
    if resolved_path.suffix.lower() != ".flac":
        raise ValueError(f"Only .flac files are supported: {resolved_path}")
    if not resolved_path.exists():
        raise FileNotFoundError(f"FLAC file not found: {resolved_path}")

    updated_tags, cleared_tags = _build_tag_changes(row.tags, definitions)

    if dry_run:
        return ProcessResult(
            row=row,
            resolved_path=resolved_path,
            updated_tags=updated_tags,
            cleared_tags=cleared_tags,
            dry_run=True,
        )

    try:
        audio = FLAC(str(resolved_path))
    except FLACNoHeaderError as exc:
        raise ValueError(f"Invalid FLAC file: {resolved_path}") from exc

    for tag_key in cleared_tags:
        if tag_key in audio:
            del audio[tag_key]

    for tag_key, tag_values in updated_tags.items():
        audio[tag_key] = list(tag_values)
    audio.save()

    return ProcessResult(
        row=row,
        resolved_path=resolved_path,
        updated_tags=updated_tags,
        cleared_tags=cleared_tags,
        dry_run=False,
    )


def _build_tag_changes(
    operations: Mapping[str, TagOperation], definitions: Mapping[str, TagDefinition]
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    updated_tags: dict[str, tuple[str, ...]] = {}
    cleared_tag_keys: list[str] = []

    for tag_name, operation in operations.items():
        definition = definitions.get(tag_name)
        if definition is None:
            continue

        if operation.is_clear:
            cleared_tag_keys.append(definition.flac_key)
            continue

        if operation.is_set:
            updated_tags[definition.flac_key] = operation.values

    return updated_tags, tuple(cleared_tag_keys)


def apply_row_to_flac(
    row: TagRow,
    definitions: Mapping[str, TagDefinition],
    csv_path: Path,
    base_dir: Path | None = None,
    album_track_map: Mapping[int, Path] | None = None,
    dry_run: bool = False,
) -> ProcessResult:
    resolved_path = resolve_row_path(row, csv_path=csv_path, base_dir=base_dir, album_track_map=album_track_map)
    return _apply_tags_to_path(resolved_path, row=row, definitions=definitions, dry_run=dry_run)


def apply_rows(
    rows: Iterable[TagRow],
    definitions: Mapping[str, TagDefinition],
    csv_path: Path,
    base_dir: Path | None = None,
    album_dir: Path | None = None,
    dry_run: bool = False,
) -> tuple[list[ProcessResult], list[ProcessError]]:
    results: list[ProcessResult] = []
    errors: list[ProcessError] = []
    row_list = list(rows)
    album_track_map: Mapping[int, Path] | None = None

    if album_dir is not None:
        track_numbers = [row.track_number for row in row_list if row.track_number is not None]
        album_track_map = build_album_track_map(album_dir, expected_track_numbers=track_numbers)

    for row in row_list:
        try:
            results.append(
                apply_row_to_flac(
                    row=row,
                    definitions=definitions,
                    csv_path=csv_path,
                    base_dir=base_dir,
                    album_track_map=album_track_map,
                    dry_run=dry_run,
                )
            )
        except (FileNotFoundError, ValueError) as exc:
            errors.append(ProcessError(source_line=row.source_line, file_path=row.file_path or "", message=str(exc)))

    return results, errors
