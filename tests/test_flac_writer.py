from pathlib import Path

from tagformatter.flac_writer import apply_rows, build_album_track_map, resolve_audio_path
from tagformatter.models import TagOperation, TagRow
from tagformatter.tag_mapping import DEFAULT_TAG_MAPPINGS


def test_resolve_audio_path_uses_base_dir(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    base_dir = tmp_path / "music"
    resolved = resolve_audio_path("disc1/01.flac", base_dir=base_dir, csv_path=csv_path)

    assert resolved == (base_dir / "disc1/01.flac").resolve()


def test_apply_rows_collects_missing_file_errors(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    row = TagRow(
        source_line=2,
        file_path="missing.flac",
        disc_number=None,
        track_number=None,
        tags={"artist_name": TagOperation.set(("Artist A",))},
    )

    results, errors = apply_rows([row], DEFAULT_TAG_MAPPINGS, csv_path=csv_path, dry_run=True)

    assert not results
    assert len(errors) == 1
    assert "FLAC file not found" in errors[0].message


def test_apply_rows_maps_album_dir_by_track_number(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    album_dir = tmp_path / "Album CD7"
    album_dir.mkdir()
    first_track = album_dir / "01 Opening.flac"
    second_track = album_dir / "02 Finale.flac"
    first_track.write_bytes(b"")
    second_track.write_bytes(b"")

    rows = [
        TagRow(source_line=2, file_path=None, disc_number=7, track_number=2, tags={"track_title": TagOperation.set(("Finale",))}),
        TagRow(source_line=3, file_path=None, disc_number=7, track_number=1, tags={"track_title": TagOperation.set(("Opening",))}),
    ]

    results, errors = apply_rows(rows, DEFAULT_TAG_MAPPINGS, csv_path=csv_path, album_dir=album_dir, dry_run=True)

    assert not errors
    assert [result.resolved_path.name for result in results] == ["02 Finale.flac", "01 Opening.flac"]


def test_apply_rows_maps_album_dir_by_embedded_disc_and_track_tags(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "tags.csv"
    album_dir = tmp_path / "Album"
    album_dir.mkdir()
    first_track = album_dir / "1-01 Opening.flac"
    second_track = album_dir / "2-01 Finale.flac"
    first_track.write_bytes(b"")
    second_track.write_bytes(b"")

    class FakeFlac(dict):
        pass

    tag_data = {
        str(first_track): FakeFlac({"DISCNUMBER": ["1"], "TRACKNUMBER": ["1"]}),
        str(second_track): FakeFlac({"DISCNUMBER": ["2"], "TRACKNUMBER": ["1"]}),
    }

    monkeypatch.setattr("tagformatter.flac_writer.FLAC", lambda path: tag_data[str(path)])

    rows = [
        TagRow(source_line=2, file_path=None, disc_number=2, track_number=1, tags={"track_title": TagOperation.set(("Finale",))}),
        TagRow(source_line=3, file_path=None, disc_number=1, track_number=1, tags={"track_title": TagOperation.set(("Opening",))}),
    ]

    results, errors = apply_rows(rows, DEFAULT_TAG_MAPPINGS, csv_path=csv_path, album_dir=album_dir, dry_run=True)

    assert not errors
    assert [result.resolved_path.name for result in results] == ["2-01 Finale.flac", "1-01 Opening.flac"]


def test_apply_rows_supports_multi_value_updates_and_clear_operations(tmp_path: Path) -> None:
    csv_path = tmp_path / "tags.csv"
    flac_path = tmp_path / "track.flac"
    flac_path.write_bytes(b"")
    row = TagRow(
        source_line=2,
        file_path="track.flac",
        disc_number=None,
        track_number=None,
        tags={
            "artist_name": TagOperation.clear(),
            "performer": TagOperation.set(("Performer A", "Performer B")),
            "track_title": TagOperation.set(("Title A",)),
        },
    )

    results, errors = apply_rows([row], DEFAULT_TAG_MAPPINGS, csv_path=csv_path, dry_run=True)

    assert not errors
    assert len(results) == 1
    assert results[0].updated_tags == {"PERFORMER": ("Performer A", "Performer B"), "TITLE": ("Title A",)}
    assert results[0].cleared_tags == ("ARTIST",)


def test_build_album_track_map_falls_back_to_sorted_order(tmp_path: Path) -> None:
    album_dir = tmp_path / "Album"
    album_dir.mkdir()
    (album_dir / "a.flac").write_bytes(b"")
    (album_dir / "b.flac").write_bytes(b"")

    rows = [
        TagRow(source_line=2, file_path=None, disc_number=None, track_number=1, tags={}),
        TagRow(source_line=3, file_path=None, disc_number=None, track_number=2, tags={}),
    ]

    track_map = build_album_track_map(album_dir, rows)

    assert track_map[(None, 1)].name == "a.flac"
    assert track_map[(None, 2)].name == "b.flac"
