from pathlib import Path

import pytest

from tagformatter.csv_loader import CLEAR_TAG_MARKER, CsvFormatError, load_tag_rows, write_template_csv
from tagformatter.models import TagOperation
from tagformatter.tag_mapping import DEFAULT_TAG_MAPPINGS


def test_load_tag_rows_supports_alias_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text(
        "file_path,Disc,Track,Album,Album Artist,Artist,Genre,Year,Comment,Composer,Performer,Title,Conductor\n"
        "disc1/01.flac,2,1,Album A,Album Artist A,Artist A,Genre A,2024,Comment A,Composer A,Performer A,Title A,Conductor A\n",
        encoding="utf-8",
    )

    rows, errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)

    assert not errors
    assert len(rows) == 1
    assert rows[0].file_path == "disc1/01.flac"
    assert rows[0].disc_number == 2
    assert rows[0].track_number == 1
    assert rows[0].tags == {
        "album_title": TagOperation.set(("Album A",)),
        "album_artist": TagOperation.set(("Album Artist A",)),
        "artist_name": TagOperation.set(("Artist A",)),
        "genre": TagOperation.set(("Genre A",)),
        "date": TagOperation.set(("2024",)),
        "comment": TagOperation.set(("Comment A",)),
        "composer": TagOperation.set(("Composer A",)),
        "performer": TagOperation.set(("Performer A",)),
        "track_title": TagOperation.set(("Title A",)),
        "conductor": TagOperation.set(("Conductor A",)),
    }


def test_load_tag_rows_treats_empty_tag_values_as_noop(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text(
        "file_path,Disc,Track,Album Artist,Artist,Composer,Performer,Title,Conductor\n"
        "disc1/01.flac,2,1,,Artist A,,Performer A,,\n",
        encoding="utf-8",
    )

    rows, errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)

    assert not errors
    assert len(rows) == 1
    assert rows[0].tags == {
        "artist_name": TagOperation.set(("Artist A",)),
        "performer": TagOperation.set(("Performer A",)),
    }


def test_load_tag_rows_supports_clear_marker_and_multi_value_tags(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text(
        "file_path,Artist,Performer,Conductor\n"
        f"disc1/01.flac,{CLEAR_TAG_MARKER},Performer A; Performer B,Conductor A\n",
        encoding="utf-8",
    )

    rows, errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)

    assert not errors
    assert len(rows) == 1
    assert rows[0].tags == {
        "artist_name": TagOperation.clear(),
        "performer": TagOperation.set(("Performer A", "Performer B")),
        "conductor": TagOperation.set(("Conductor A",)),
    }


def test_load_tag_rows_supports_track_mode_without_file_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text("Disc,Track,Artist,Composer\n7,3,A,B\n", encoding="utf-8")

    rows, errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)

    assert not errors
    assert len(rows) == 1
    assert rows[0].file_path is None
    assert rows[0].disc_number == 7
    assert rows[0].track_number == 3


def test_load_tag_rows_requires_targeting_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text("Artist,Composer\nA,B\n", encoding="utf-8")

    with pytest.raises(CsvFormatError):
        load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)


def test_write_template_csv_writes_expected_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / "template.csv"

    write_template_csv(csv_path, DEFAULT_TAG_MAPPINGS)

    assert csv_path.read_text(encoding="utf-8") == (
        "disc,track,file_path,album_title,album_artist,artist_name,genre,date,comment,composer,performer,track_title,conductor\n"
    )
