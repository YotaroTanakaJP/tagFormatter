from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping


@dataclass(frozen=True)
class TagDefinition:
    csv_columns: tuple[str, ...]
    flac_key: str


DEFAULT_TAG_MAPPINGS: Dict[str, TagDefinition] = {
    "artist_name": TagDefinition(csv_columns=("artist_name", "Artist Name", "Artist"), flac_key="ARTIST"),
    "composer": TagDefinition(csv_columns=("composer", "Composer"), flac_key="COMPOSER"),
    "track_title": TagDefinition(csv_columns=("track_title", "Track Title", "Title"), flac_key="TITLE"),
    "conductor": TagDefinition(csv_columns=("conductor", "Conductor"), flac_key="CONDUCTOR"),
}


def canonical_csv_columns(definitions: Mapping[str, TagDefinition]) -> tuple[str, ...]:
    return tuple(definitions.keys())


def build_column_lookup(definitions: Mapping[str, TagDefinition]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical_name, definition in definitions.items():
        for column_name in definition.csv_columns:
            lookup[column_name.casefold()] = canonical_name
    return lookup


def export_template_headers(definitions: Mapping[str, TagDefinition]) -> Iterable[str]:
    return ("disc", "track", "file_path", *canonical_csv_columns(definitions))
