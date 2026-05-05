from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class TagOperation:
    action: str
    values: tuple[str, ...] = ()

    @classmethod
    def set(cls, values: tuple[str, ...]) -> "TagOperation":
        if not values:
            raise ValueError("set operations require at least one value")
        return cls(action="set", values=values)

    @classmethod
    def clear(cls) -> "TagOperation":
        return cls(action="clear")

    @property
    def is_set(self) -> bool:
        return self.action == "set"

    @property
    def is_clear(self) -> bool:
        return self.action == "clear"


@dataclass(frozen=True)
class TagRow:
    source_line: int
    file_path: str | None
    disc_number: int | None
    track_number: int | None
    tags: Dict[str, TagOperation]


@dataclass(frozen=True)
class ProcessResult:
    row: TagRow
    resolved_path: Path
    updated_tags: Dict[str, tuple[str, ...]]
    cleared_tags: tuple[str, ...]
    dry_run: bool


@dataclass(frozen=True)
class ProcessError:
    source_line: int
    file_path: str
    message: str
