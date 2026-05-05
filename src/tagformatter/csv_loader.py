from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

from .models import ProcessError, TagOperation, TagRow
from .tag_mapping import TagDefinition, build_column_lookup


class CsvFormatError(ValueError):
    pass


DISC_COLUMNS = ("disc", "Disc", "disc_number", "Disc Number")
TRACK_COLUMNS = ("track", "Track", "track_number", "Track Number")
CLEAR_TAG_MARKER = "__CLEAR__"
MULTI_VALUE_SEPARATOR = ";"


def _find_header(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized_headers = {name.casefold(): name for name in fieldnames}
    for candidate in candidates:
        match = normalized_headers.get(candidate.casefold())
        if match is not None:
            return match
    return None


def _parse_optional_int(value: str | None, label: str, line_number: int) -> int | None:
    normalized_value = (value or "").strip()
    if not normalized_value:
        return None
    try:
        return int(normalized_value)
    except ValueError as exc:
        raise CsvFormatError(f"{label} must be an integer on line {line_number}") from exc


def _parse_tag_operation(value: str | None, column_name: str, line_number: int) -> TagOperation | None:
    normalized_value = (value or "").strip()
    if not normalized_value:
        return None
    if normalized_value == CLEAR_TAG_MARKER:
        return TagOperation.clear()

    values = tuple(part.strip() for part in normalized_value.split(MULTI_VALUE_SEPARATOR) if part.strip())
    if not values:
        raise CsvFormatError(f"{column_name} must include at least one value on line {line_number}")
    return TagOperation.set(values)


def load_tag_rows(csv_path: Path, definitions: Mapping[str, TagDefinition]) -> tuple[list[TagRow], list[ProcessError]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CsvFormatError("CSV header is missing")

        file_path_header = _find_header(reader.fieldnames, ("file_path",))
        disc_header = _find_header(reader.fieldnames, DISC_COLUMNS)
        track_header = _find_header(reader.fieldnames, TRACK_COLUMNS)
        if file_path_header is None and track_header is None:
            raise CsvFormatError("CSV must include file_path or Track column")

        column_lookup = build_column_lookup(definitions)
        rows: list[TagRow] = []
        errors: list[ProcessError] = []

        for line_number, raw_row in enumerate(reader, start=2):
            file_path_value = (raw_row.get(file_path_header, "") or "").strip() if file_path_header else ""
            disc_number = _parse_optional_int(raw_row.get(disc_header), "Disc", line_number) if disc_header else None
            track_number = _parse_optional_int(raw_row.get(track_header), "Track", line_number) if track_header else None

            if not file_path_value and track_number is None:
                errors.append(ProcessError(source_line=line_number, file_path="", message="file_path or Track is required"))
                continue

            tags: dict[str, TagOperation] = {}
            for column_name, value in raw_row.items():
                if column_name is None:
                    continue

                canonical_name = column_lookup.get(column_name.casefold())
                if canonical_name is None:
                    continue

                operation = _parse_tag_operation(value, column_name=column_name, line_number=line_number)
                if operation is None:
                    continue
                tags[canonical_name] = operation

            rows.append(
                TagRow(
                    source_line=line_number,
                    file_path=file_path_value or None,
                    disc_number=disc_number,
                    track_number=track_number,
                    tags=tags,
                )
            )

    return rows, errors


def write_template_csv(output_path: Path, definitions: Mapping[str, TagDefinition]) -> None:
    from .tag_mapping import export_template_headers

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(export_template_headers(definitions)))
