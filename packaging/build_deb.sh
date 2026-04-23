#!/usr/bin/env bash
# Build a self-contained .deb for preview-app.
#
# The resulting package bundles a Python virtualenv with all pip
# dependencies (PyQt6, PyMuPDF, Pillow, pytesseract) under
# /opt/preview-app/venv, so the target system only needs:
#   - python3
#   - tesseract-ocr + tesseract-ocr-eng
#   - a handful of xcb/gl/fontconfig runtime libs (declared in Depends).
#
# Usage:
#   ./packaging/build_deb.sh            # -> build/preview-app_<ver>_<arch>.deb
#
# No sudo required to build. Install the resulting .deb with:
#   sudo apt install ./build/preview-app_<ver>_<arch>.deb
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${VERSION:-$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')}"
ARCH="$(dpkg --print-architecture)"
PKGNAME="preview-app"
BUILD_DIR="$ROOT/build"
STAGE="$BUILD_DIR/${PKGNAME}_${VERSION}_${ARCH}"
DEB_OUT="$BUILD_DIR/${PKGNAME}_${VERSION}_${ARCH}.deb"

for tool in python3 dpkg-deb dpkg; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "error: $tool is required to build the .deb" >&2
        exit 1
    fi
done

if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "error: Python venv module not available." >&2
    echo "install it with: sudo apt install python3-venv" >&2
    exit 1
fi

echo ">>> staging to $STAGE"
rm -rf "$STAGE" "$DEB_OUT"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/opt/preview-app"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/doc/preview-app"
mkdir -p "$STAGE/usr/share/icons/hicolor/scalable/apps"

echo ">>> copying source + resources"
cp -r "$ROOT/src" "$STAGE/opt/preview-app/"
cp -r "$ROOT/resources" "$STAGE/opt/preview-app/"

echo ">>> creating virtualenv and installing pip deps"
python3 -m venv "$STAGE/opt/preview-app/venv"
"$STAGE/opt/preview-app/venv/bin/pip" install --quiet --upgrade pip wheel
"$STAGE/opt/preview-app/venv/bin/pip" install --quiet --no-cache-dir -r "$ROOT/requirements.txt"

echo ">>> stripping build byproducts"
find "$STAGE/opt/preview-app" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/opt/preview-app" -type f -name "*.pyc" -delete 2>/dev/null || true
# Drop pip's own cache and any .dist-info RECORD entries are fine to keep.
rm -rf "$STAGE/opt/preview-app/venv/share" 2>/dev/null || true

echo ">>> writing launcher"
cat > "$STAGE/usr/bin/preview-app" << 'EOF'
#!/usr/bin/env bash
# Launcher for preview-app installed via .deb.
# The venv's python is still a symlink to the system python3; we set
# PYTHONPATH so the app code at /opt/preview-app/src is importable.
export PYTHONPATH="/opt/preview-app/src${PYTHONPATH:+:$PYTHONPATH}"
exec /opt/preview-app/venv/bin/python -m preview_app "$@"
EOF
chmod 755 "$STAGE/usr/bin/preview-app"

echo ">>> writing .desktop entry and icon"
cp "$ROOT/packaging/debian/preview-app.desktop" "$STAGE/usr/share/applications/"
cp "$ROOT/resources/icons/preview-app.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/preview-app.svg"

echo ">>> writing copyright + OFL notice"
cat > "$STAGE/usr/share/doc/preview-app/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: preview-app

Files: *
Copyright: Preview App Contributors
License: MIT

Files: opt/preview-app/resources/fonts/*.ttf
Copyright: Dancing Script, Great Vibes, Caveat - Google Fonts contributors
License: OFL-1.1
 See /opt/preview-app/resources/fonts/OFL.txt for the full license.
EOF

echo ">>> writing control"
SIZE_KB=$(du -sk "$STAGE" | cut -f1)
cat > "$STAGE/DEBIAN/control" << EOF
Package: preview-app
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Installed-Size: $SIZE_KB
Depends: python3 (>= 3.11),
 tesseract-ocr,
 tesseract-ocr-eng,
 libxcb-cursor0,
 libgl1,
 libegl1,
 libfontconfig1,
 libxkbcommon-x11-0,
 libdbus-1-3,
 libxcb-icccm4,
 libxcb-image0,
 libxcb-keysyms1,
 libxcb-randr0,
 libxcb-render-util0,
 libxcb-shape0,
 libxcb-xkb1
Maintainer: Preview App Contributors <noreply@example.com>
Description: Image and PDF viewer with OCR text selection and PDF signing
 Preview-style application for Linux. View images and PDFs, select
 text within them (OCR-backed for scanned PDFs and images), rubber-band
 copy regions as images, and sign PDFs using a library of drawn or
 typed signatures that round-trip via zip import/export.
EOF

echo ">>> writing postinst (refresh icon + desktop caches)"
cat > "$STAGE/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q >/dev/null 2>&1 || true
fi
exit 0
EOF

cat > "$STAGE/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q >/dev/null 2>&1 || true
    fi
fi
exit 0
EOF

chmod 755 "$STAGE/DEBIAN"
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"
find "$STAGE/DEBIAN" -type f ! -name 'postinst' ! -name 'postrm' -exec chmod 644 {} \;

echo ">>> building $DEB_OUT"
dpkg-deb --build --root-owner-group "$STAGE" "$DEB_OUT" >/dev/null

echo ""
echo "Built:   $DEB_OUT"
echo "Size:    $(du -h "$DEB_OUT" | cut -f1)"
echo ""
echo "Install with:"
echo "  sudo apt install $DEB_OUT"
echo ""
echo "Or (no dep resolution):"
echo "  sudo dpkg -i $DEB_OUT && sudo apt -f install"
