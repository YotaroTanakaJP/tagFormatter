from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class TagRow:
    source_line: int
    file_path: str | None
    disc_number: int | None
    track_number: int | None
    tags: Dict[str, str]


@dataclass(frozen=True)
class ProcessResult:
    row: TagRow
    resolved_path: Path
    updated_tags: Dict[str, str]
    dry_run: bool


@dataclass(frozen=True)
class ProcessError:
    source_line: int
    file_path: str
    message: str
