# Preview App

A macOS-Preview-style viewer for Ubuntu. View images and PDFs, select text from them (OCR-powered for scanned documents and screenshots), copy regions as images, and sign PDFs with a library of drawn or typed signatures.

---

## Install

### Option 1 — One-liner (recommended, always latest release)

Pick the `.deb` for your Ubuntu version and run **one command**:

**Ubuntu 24.04:**

```bash
curl -LO https://github.com/mahdy-nasr/ocr-and-signer-for-linux/releases/latest/download/preview-app_ubuntu-24.04_amd64.deb \
  && sudo apt install -y ./preview-app_ubuntu-24.04_amd64.deb
```

**Ubuntu 22.04:**

```bash
curl -LO https://github.com/mahdy-nasr/ocr-and-signer-for-linux/releases/latest/download/preview-app_ubuntu-22.04_amd64.deb \
  && sudo apt install -y ./preview-app_ubuntu-22.04_amd64.deb
```

These URLs use GitHub's `/releases/latest/download/` redirector, so they automatically resolve to whatever the current latest release is — no need to update the README per version. `apt` pulls in system libraries (`tesseract-ocr`, `libxcb-cursor0`, etc.) automatically.

### Option 2 — Pin to a specific version

For `v0.1.0` (current release):

```bash
# Ubuntu 22.04:
curl -LO https://github.com/mahdy-nasr/ocr-and-signer-for-linux/releases/download/v0.1.0/preview-app_0.1.0_ubuntu-22.04_amd64.deb \
  && sudo apt install -y ./preview-app_0.1.0_ubuntu-22.04_amd64.deb

# Ubuntu 24.04:
curl -LO https://github.com/mahdy-nasr/ocr-and-signer-for-linux/releases/download/v0.1.0/preview-app_0.1.0_ubuntu-24.04_amd64.deb \
  && sudo apt install -y ./preview-app_0.1.0_ubuntu-24.04_amd64.deb
```

### Option 3 — Download from the Releases page

Open **[Releases](https://github.com/mahdy-nasr/ocr-and-signer-for-linux/releases/latest)**, download the `.deb` matching your Ubuntu version, then:

```bash
sudo apt install ./preview-app_*.deb
```

### Launch

After install, either:

- Open **"Preview App"** from your applications menu
- Or run `preview-app` in a terminal (optionally with a file path: `preview-app ~/Documents/contract.pdf`)

### Update

```bash
# grab the latest .deb, then:
sudo apt install ./preview-app_<new-version>_*.deb
```

### Uninstall

```bash
sudo apt remove preview-app
```

Your signatures and OCR cache live in `~/.local/share/preview_app/` and `~/.cache/preview_app/` — they survive uninstall and reinstall.

---

## Features

- **Image viewer with OCR text selection** — open any PNG/JPG/BMP/TIFF/WebP, drag across text, `Ctrl+C` to copy. Tesseract runs in the background with multiple layout fallbacks so screenshots, scans, and photos of text all work.
- **PDF viewer** — text-layer selection for born-digital PDFs (instant), OCR fallback for scanned PDFs. A small badge in the bottom bar tells you which mode is active per page.
- **Rubber-band region copy** — press `R`, drag a rectangle over any part of a page, and copy it to the clipboard or save it as a PNG.
- **Signature library** — draw a signature with your mouse (smooth, anti-aliased strokes) or type one in a cursive font (Dancing Script, Great Vibes, or Caveat). Save multiple named signatures; mark one as default.
- **PDF signing** — click **Sign**, pick a signature, drag to position it, resize via the corner handle, click **Apply**, then **Save** or **Save As**. The signature is embedded as a transparent image overlay — opens correctly in Evince, Okular, Adobe Reader, macOS Preview, etc.
- **Import / export signatures** — back up or move signatures between machines as a single zip via **Tools → Export Signatures**. Import from a zip, an unpacked folder, or a folder of loose PNGs.

---

## Keyboard shortcuts

| Shortcut            | Action                           |
|---------------------|----------------------------------|
| `Ctrl+O`            | Open a file                      |
| `Ctrl+S`            | Save (incremental, for PDFs)     |
| `Ctrl+Shift+S`      | Save As                          |
| `Ctrl+W`            | Close current tab                |
| `Ctrl+C`            | Copy selected text or region     |
| `V`                 | Text-select mode                 |
| `R`                 | Rectangular region-select mode   |
| `Ctrl+=` / `Ctrl+-` | Zoom in / out                    |
| `Ctrl+0`            | Fit width                        |

When a signature placement is active, **Apply** stamps it, **Cancel** discards it, and **Save** auto-commits it as a safety net.

---

## Troubleshooting

- **App won't launch, complains about `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`**
  Install the missing xcb runtime library:
  `sudo apt install libxcb-cursor0`

- **OCR badge says "OCR — no text found"**
  The image is too low-contrast, too small, or uses a font Tesseract struggles with. Try a higher-resolution version. Debug with `PREVIEW_APP_DEBUG=1 preview-app` to see which layout modes Tesseract tried.

- **Signature doesn't appear after saving**
  Make sure you clicked **Apply** (or press Enter) on the placement — not just dragged it. Recent versions auto-apply on Save as a safety net.

- **Encrypted PDFs**
  Currently not supported; the app will refuse to open password-protected PDFs. Decrypt with `qpdf` first if needed.

---

## Build from source

This section is for developers. Most users should install the `.deb` from Releases above.

### Run from source

```bash
# one-time: install system prerequisites
sudo apt install -y python3 python3-venv python3-pip \
  tesseract-ocr tesseract-ocr-eng \
  libgl1 libegl1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xkb1 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libfreetype6

# clone, then:
./run.sh                      # launches empty
./run.sh path/to/file.pdf     # opens a file directly
./run.sh path/to/image.png
```

`run.sh` creates a `.venv/` on first launch, installs pip deps, and runs the app.

### Build a .deb locally

```bash
./packaging/build_deb.sh
```

Produces `build/preview-app_<version>_<arch>.deb` (~93 MB — bundles a Python virtualenv with all pip dependencies under `/opt/preview-app/`, so the host system only needs `python3`, `tesseract-ocr`, and the Qt runtime libs listed above).

Override the version:

```bash
VERSION=0.2.0 ./packaging/build_deb.sh
```

Test your local build:

```bash
sudo apt install ./build/preview-app_0.1.0_amd64.deb
```

Same-version reinstall (development iteration):

```bash
sudo apt install --reinstall ./build/preview-app_0.1.0_amd64.deb
```

### Run the test suite

```bash
.venv/bin/python tests/smoke_test.py
.venv/bin/python tests/jpg_repro.py
.venv/bin/python tests/sign_flow_test.py
.venv/bin/python tests/sig_io_test.py
```

All tests run headless using `QT_QPA_PLATFORM=offscreen`.

---

## CI / Releases

Three workflows under `.github/workflows/`:

| Workflow        | Triggers                        | What it does                                                          |
|-----------------|---------------------------------|-----------------------------------------------------------------------|
| `ci.yml`        | Push to main, PRs, manual       | Runs all four tests on Python 3.11 and 3.12                           |
| `package.yml`   | Push to main, PRs, manual       | Builds `.deb` for Ubuntu 22.04 and 24.04, uploads as workflow artifact |
| `release.yml`   | Tag push matching `v*`, manual  | Tests → builds both `.deb`s → publishes a GitHub Release with them    |

**Cut a release:**

```bash
git tag v0.1.0
git push origin v0.1.0
```

Or from the GitHub UI: **Actions → Release → Run workflow** and type the version.

The release page will show both `.deb`s attached as downloadable assets, with auto-generated release notes from commits since the previous tag.

---

## Project layout

```
linux-app/
├── src/preview_app/
│   ├── core/            OCR, PDF I/O, selection math, signature stamping (Qt-free)
│   ├── models/          Signature store, document refs
│   ├── ui/              PyQt6 widgets, main window, document tabs, signature dialog
│   └── util/            Geometry / image conversion helpers
├── resources/
│   ├── fonts/           Cursive TTFs (SIL OFL)
│   ├── icons/           App icon (SVG)
│   └── styles/          Qt stylesheet
├── tests/               End-to-end smoke + regression tests (headless)
├── packaging/
│   ├── build_deb.sh     Builds a self-contained .deb bundling a Python venv
│   └── debian/          .desktop entry
├── .github/workflows/   CI + .deb build + release automation
├── run.sh               Dev launcher — creates .venv, installs deps, runs the app
├── requirements.txt
└── pyproject.toml
```

---

## Credits

Bundled cursive fonts are from Google Fonts, licensed under the [SIL Open Font License 1.1](resources/fonts/OFL.txt):

- **Dancing Script** — Pablo Impallari, Rodrigo Fuenzalida, Igino Marini
- **Great Vibes** — TypeSETit
- **Caveat** — Impallari Type

Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/), [PyMuPDF](https://pymupdf.readthedocs.io/), [Pillow](https://python-pillow.org/), and [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).
