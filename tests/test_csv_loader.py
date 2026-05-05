from pathlib import Path

import pytest

from tagformatter.csv_loader import CsvFormatError, load_tag_rows, write_template_csv
from tagformatter.tag_mapping import DEFAULT_TAG_MAPPINGS


def test_load_tag_rows_supports_alias_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    csv_path.write_text(
        "file_path,Disc,Track,Album Artist,Artist,Composer,Performer,Title,Conductor\n"
        "disc1/01.flac,2,1,Album Artist A,Artist A,Composer A,Performer A,Title A,Conductor A\n",
        encoding="utf-8",
    )

    rows, errors = load_tag_rows(csv_path, DEFAULT_TAG_MAPPINGS)

    assert not errors
    assert len(rows) == 1
    assert rows[0].file_path == "disc1/01.flac"
    assert rows[0].disc_number == 2
    assert rows[0].track_number == 1
    assert rows[0].tags == {
        "album_artist": "Album Artist A",
        "artist_name": "Artist A",
        "composer": "Composer A",
        "performer": "Performer A",
        "track_title": "Title A",
        "conductor": "Conductor A",
    }


def test_load_tag_rows_preserves_empty_tag_values(tmp_path: Path) -> None:
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
        "album_artist": "",
        "artist_name": "Artist A",
        "composer": "",
        "performer": "Performer A",
        "track_title": "",
        "conductor": "",
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

    assert csv_path.read_text(encoding="utf-8") == "disc,track,file_path,album_artist,artist_name,composer,performer,track_title,conductor\n"
