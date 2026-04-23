from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DocKind(str, Enum):
    IMAGE = "image"
    PDF = "pdf"


@dataclass
class DocumentRef:
    path: Path
    kind: DocKind

    @classmethod
    def from_path(cls, path: str | Path) -> "DocumentRef":
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".pdf":
            return cls(path=p, kind=DocKind.PDF)
        return cls(path=p, kind=DocKind.IMAGE)
