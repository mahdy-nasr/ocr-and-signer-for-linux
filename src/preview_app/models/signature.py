from __future__ import annotations

import fcntl
import json
import os
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


SignatureType = Literal["drawn", "typed"]


@dataclass
class Signature:
    id: str
    name: str
    created_at: datetime
    type: SignatureType
    file: str
    is_default: bool = False
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "type": self.type,
            "file": self.file,
            "is_default": self.is_default,
            "meta": self.meta,
        }

    @classmethod
    def from_json(cls, d: dict) -> "Signature":
        return cls(
            id=d["id"],
            name=d["name"],
            created_at=datetime.fromisoformat(d["created_at"]),
            type=d["type"],
            file=d["file"],
            is_default=bool(d.get("is_default", False)),
            meta=d.get("meta", {}) or {},
        )


class SignatureStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.base_dir / "signatures.json"
        self._items: list[Signature] = []
        self.load()

    def load(self) -> list[Signature]:
        if not self.json_path.exists():
            self._items = []
            return self._items
        try:
            with self.json_path.open("r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError):
            self._items = []
            return self._items
        raw_items = data.get("signatures", [])
        self._items = [Signature.from_json(r) for r in raw_items]
        return self._items

    def all(self) -> list[Signature]:
        return list(self._items)

    def get(self, sig_id: str) -> Signature | None:
        for s in self._items:
            if s.id == sig_id:
                return s
        return None

    def default(self) -> Signature | None:
        for s in self._items:
            if s.is_default:
                return s
        return self._items[0] if self._items else None

    def path_for(self, sig: Signature) -> Path:
        return self.base_dir / sig.file

    def add(
        self,
        name: str,
        sig_type: SignatureType,
        png_bytes: bytes,
        is_default: bool = False,
        meta: dict | None = None,
    ) -> Signature:
        sig_id = uuid.uuid4().hex
        filename = f"sig_{sig_id}.png"
        (self.base_dir / filename).write_bytes(png_bytes)
        sig = Signature(
            id=sig_id,
            name=name,
            created_at=datetime.now(timezone.utc),
            type=sig_type,
            file=filename,
            is_default=is_default,
            meta=meta or {},
        )
        if is_default:
            for other in self._items:
                other.is_default = False
        self._items.append(sig)
        self._save_all()
        return sig

    def delete(self, sig_id: str) -> None:
        target = self.get(sig_id)
        if target is None:
            return
        try:
            (self.base_dir / target.file).unlink(missing_ok=True)
        except OSError:
            pass
        self._items = [s for s in self._items if s.id != sig_id]
        if target.is_default and self._items:
            self._items[0].is_default = True
        self._save_all()

    def rename(self, sig_id: str, new_name: str) -> None:
        sig = self.get(sig_id)
        if sig is None:
            return
        sig.name = new_name
        self._save_all()

    def set_default(self, sig_id: str) -> None:
        target = self.get(sig_id)
        if target is None:
            return
        for s in self._items:
            s.is_default = (s.id == sig_id)
        self._save_all()

    def _save_all(self) -> None:
        tmp = self.json_path.with_suffix(".json.tmp")
        payload = {
            "version": 1,
            "signatures": [s.to_json() for s in self._items],
        }
        with tmp.open("w", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp, self.json_path)

    # ---- import / export ----

    def export_zip(self, out_path: str | Path) -> Path:
        """Write a zip bundling signatures.json plus each signature's PNG."""
        target = Path(out_path)
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        payload = {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "signatures": [s.to_json() for s in self._items],
        }
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("signatures.json", json.dumps(payload, indent=2))
            for sig in self._items:
                png = self.base_dir / sig.file
                if png.exists():
                    zf.write(png, arcname=sig.file)
        return target

    def import_from(self, source: str | Path) -> int:
        """Import signatures from a zip or a directory. Returns count added.

        - zip / directory containing `signatures.json`: parse it and import
          each entry, copying the referenced PNGs.
        - directory with only loose PNGs: each PNG becomes a drawn signature
          named after its filename.

        Imported signatures always get a fresh UUID; `is_default` is never
        carried over (only the local store decides what's default).
        """
        source_path = Path(source)
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            return self._import_zip(source_path)
        if source_path.is_dir():
            return self._import_dir(source_path)
        raise ValueError(f"Unsupported import source: {source_path}")

    def _import_zip(self, zip_path: Path) -> int:
        added = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            if "signatures.json" in names:
                raw = json.loads(zf.read("signatures.json").decode("utf-8"))
                for entry in raw.get("signatures", []):
                    png_name = entry.get("file")
                    if not png_name or png_name not in names:
                        continue
                    png_bytes = zf.read(png_name)
                    self._import_one(
                        name=entry.get("name", "Imported"),
                        sig_type=entry.get("type", "drawn"),
                        png_bytes=png_bytes,
                        meta=entry.get("meta") or {},
                    )
                    added += 1
            else:
                for name in names:
                    if name.lower().endswith(".png") and not name.endswith("/"):
                        png_bytes = zf.read(name)
                        stem = Path(name).stem
                        self._import_one(
                            name=stem or "Imported",
                            sig_type="drawn",
                            png_bytes=png_bytes,
                            meta={},
                        )
                        added += 1
        if added:
            self._save_all()
        return added

    def _import_dir(self, dir_path: Path) -> int:
        added = 0
        manifest = dir_path / "signatures.json"
        if manifest.exists():
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            for entry in raw.get("signatures", []):
                png_name = entry.get("file")
                if not png_name:
                    continue
                png_path = dir_path / png_name
                if not png_path.exists():
                    continue
                self._import_one(
                    name=entry.get("name", "Imported"),
                    sig_type=entry.get("type", "drawn"),
                    png_bytes=png_path.read_bytes(),
                    meta=entry.get("meta") or {},
                )
                added += 1
        else:
            for png_path in sorted(dir_path.glob("*.png")):
                self._import_one(
                    name=png_path.stem or "Imported",
                    sig_type="drawn",
                    png_bytes=png_path.read_bytes(),
                    meta={},
                )
                added += 1
        if added:
            self._save_all()
        return added

    def _import_one(self, name: str, sig_type: str, png_bytes: bytes, meta: dict) -> Signature:
        final_name = self._unique_name(name)
        final_type: SignatureType = sig_type if sig_type in ("drawn", "typed") else "drawn"
        new_id = uuid.uuid4().hex
        filename = f"sig_{new_id}.png"
        (self.base_dir / filename).write_bytes(png_bytes)
        sig = Signature(
            id=new_id,
            name=final_name,
            created_at=datetime.now(timezone.utc),
            type=final_type,
            file=filename,
            is_default=False,
            meta=meta or {},
        )
        self._items.append(sig)
        return sig

    def _unique_name(self, base: str) -> str:
        existing = {s.name for s in self._items}
        if base not in existing:
            return base
        for i in range(2, 1000):
            candidate = f"{base} ({i})"
            if candidate not in existing:
                return candidate
        return f"{base} ({uuid.uuid4().hex[:6]})"
