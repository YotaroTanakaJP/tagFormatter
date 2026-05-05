from pathlib import Path

from tagformatter.cli import infer_disc_number, main, select_rows_for_album
from tagformatter.models import TagRow


def test_main_writes_template(tmp_path: Path, capsys) -> None:
    template_path = tmp_path / "template.csv"

    exit_code = main(["--write-template", str(template_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert template_path.exists()
    assert "Template written" in captured.out


def test_main_returns_error_for_missing_csv(tmp_path: Path) -> None:
    exit_code = main(["--csv", str(tmp_path / "missing.csv")])

    assert exit_code == 2


def test_infer_disc_number_from_album_path() -> None:
    album_dir = Path("/music/Collection/Example Album (CD7)/Artist")

    assert infer_disc_number(album_dir) == 7


def test_select_rows_for_album_filters_disc() -> None:
    rows = [
        TagRow(source_line=2, file_path=None, disc_number=6, track_number=1, tags={}),
        TagRow(source_line=3, file_path=None, disc_number=7, track_number=1, tags={}),
    ]

    selected_rows, errors = select_rows_for_album(rows, disc_number=7)

    assert not errors
    assert len(selected_rows) == 1
    assert selected_rows[0].disc_number == 7


def test_select_rows_for_album_keeps_multiple_discs_when_not_specified() -> None:
    rows = [
        TagRow(source_line=2, file_path=None, disc_number=1, track_number=1, tags={}),
        TagRow(source_line=3, file_path=None, disc_number=2, track_number=1, tags={}),
    ]

    selected_rows, errors = select_rows_for_album(rows, disc_number=None)

    assert not errors
    assert selected_rows == rows
