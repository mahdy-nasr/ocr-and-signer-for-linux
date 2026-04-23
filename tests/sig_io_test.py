"""Round-trip + alternate-format tests for signature export/import."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw  # noqa: E402

from preview_app.models.signature import SignatureStore  # noqa: E402


def _fake_png(tmp: Path, name: str, stroke_y: int) -> bytes:
    img = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(10, stroke_y), (90, 20), (180, stroke_y - 10)], fill=(0, 0, 0, 255), width=4)
    p = tmp / name
    img.save(str(p), "PNG")
    return p.read_bytes()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sig_io_"))

    # Populate source store
    src = SignatureStore(tmp / "src")
    a = src.add("Alice",  "drawn", _fake_png(tmp, "a.png", 60), is_default=True)
    b = src.add("Bob",    "typed", _fake_png(tmp, "b.png", 50), meta={"font_family": "Caveat", "text": "Bob"})
    c = src.add("Carol",  "drawn", _fake_png(tmp, "c.png", 40))
    assert len(src.all()) == 3
    print(f"[1] src store: {len(src.all())} sigs")

    # Export to zip
    zip_path = tmp / "export.zip"
    out = src.export_zip(zip_path)
    assert out.exists()
    import zipfile
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "signatures.json" in names
    for sig in src.all():
        assert sig.file in names, f"{sig.file} missing from zip"
    print(f"[2] exported zip has {len(names)} entries")

    # Import into fresh store
    dst = SignatureStore(tmp / "dst")
    added = dst.import_from(zip_path)
    assert added == 3, f"expected 3, got {added}"
    names_after = {s.name for s in dst.all()}
    assert names_after == {"Alice", "Bob", "Carol"}, names_after
    assert all(not s.is_default for s in dst.all()), "imports should never bring is_default"
    # UUIDs must differ
    src_ids = {s.id for s in src.all()}
    dst_ids = {s.id for s in dst.all()}
    assert src_ids.isdisjoint(dst_ids), "imported sigs should have fresh UUIDs"
    print(f"[3] imported {added} into fresh store")

    # Name collision: re-import the same zip into dst
    again = dst.import_from(zip_path)
    assert again == 3
    names_all = [s.name for s in dst.all()]
    assert "Alice (2)" in names_all, names_all
    assert "Bob (2)" in names_all
    assert "Carol (2)" in names_all
    print(f"[4] conflict handling: {sorted(names_all)}")

    # Import from a directory that only has loose pngs (no signatures.json)
    loose_dir = tmp / "loose"
    loose_dir.mkdir()
    (loose_dir / "Handwritten.png").write_bytes(_fake_png(tmp, "h.png", 30))
    (loose_dir / "Scribble.png").write_bytes(_fake_png(tmp, "s.png", 20))
    dst2 = SignatureStore(tmp / "dst2")
    count = dst2.import_from(loose_dir)
    assert count == 2
    assert {s.name for s in dst2.all()} == {"Handwritten", "Scribble"}
    print(f"[5] loose png dir: imported {count}")

    # Import from an unpacked export directory (has signatures.json + pngs)
    unpacked = tmp / "unpacked"
    unpacked.mkdir()
    import zipfile
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(unpacked)
    dst3 = SignatureStore(tmp / "dst3")
    count = dst3.import_from(unpacked)
    assert count == 3
    assert {s.name for s in dst3.all()} == {"Alice", "Bob", "Carol"}
    print(f"[6] unpacked dir: imported {count}")

    print("SIGNATURE IO TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
