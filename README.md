# Preview App

A macOS-Preview-style viewer for Ubuntu. View images and PDFs, select text from them (OCR-powered for images and scanned PDFs), rubber-band-select regions as images, and sign PDFs with a library of drawn or typed signatures.

## Prerequisites (Ubuntu 22.04 / 24.04)

```bash
sudo apt install -y python3 python3-venv python3-pip \
  tesseract-ocr tesseract-ocr-eng \
  libgl1 libegl1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xkb1 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libfreetype6
```

If PyQt6 fails to start with `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, double-check that `libxcb-cursor0` is installed.

## Run

```bash
./run.sh                      # launches empty
./run.sh path/to/file.pdf     # opens a file directly
./run.sh path/to/image.png
```

First launch creates `~/.local/share/preview_app/signatures/` for the signature library.

## Packaging (.deb)

### Build a .deb locally

```bash
./packaging/build_deb.sh
```

Produces `build/preview-app_<version>_<arch>.deb` (~93 MB — bundles a Python
virtualenv with all pip dependencies under `/opt/preview-app/`, so the host
system only needs `python3`, `tesseract-ocr`, and the Qt runtime libs listed
under Prerequisites).

Override the version without editing `pyproject.toml`:

```bash
VERSION=0.2.0 ./packaging/build_deb.sh
```

### What the .deb installs

| Path                                              | Contents                                |
|---------------------------------------------------|-----------------------------------------|
| `/opt/preview-app/src/`                           | App source                              |
| `/opt/preview-app/resources/`                     | Cursive fonts, icon, stylesheet         |
| `/opt/preview-app/venv/`                          | Python virtualenv with pip deps         |
| `/usr/bin/preview-app`                            | Launcher shell script                   |
| `/usr/share/applications/preview-app.desktop`     | Menu entry                              |
| `/usr/share/icons/hicolor/scalable/apps/...svg`   | Scalable app icon                       |
| `/usr/share/doc/preview-app/copyright`            | Copyright + OFL font license reference  |

User data (signatures, OCR cache) lives in `~/.local/share/preview_app/` and
`~/.cache/preview_app/` — it survives uninstall/reinstall.

### Install

```bash
sudo apt install ./build/preview-app_0.1.0_amd64.deb
```

After install the app is available as the `preview-app` command and shows up
in your applications menu. Uninstall with `sudo apt remove preview-app`.

### Update an installed .deb

Same version (development iteration) — use `--reinstall`:

```bash
./packaging/build_deb.sh
sudo apt install --reinstall ./build/preview-app_0.1.0_amd64.deb
```

Bumped version — regular install picks up the upgrade:

```bash
VERSION=0.1.1 ./packaging/build_deb.sh
sudo apt install ./build/preview-app_0.1.1_amd64.deb
```

Kill any running `preview-app` process before upgrading.

### CI / GitHub Actions

Three workflows under `.github/workflows/`:

- **`ci.yml`** — runs the full test suite (`smoke_test`, `jpg_repro`,
  `sign_flow_test`, `sig_io_test`) on push to `main`, on every PR, and via
  manual dispatch. Matrix covers Python 3.11 and 3.12. Uses
  `QT_QPA_PLATFORM=offscreen` so no X server is needed.
- **`package.yml`** — builds the `.deb` on push/PR/manual dispatch across
  `ubuntu-22.04` and `ubuntu-24.04` runners, uploading each as a workflow
  artifact (retention: 14 days).
- **`release.yml`** — triggered by tag pushes matching `v*` (or manual
  dispatch with an explicit version). Flow: test → build on both runners →
  attach the `.deb`s to a GitHub Release with auto-generated release notes.

Cut a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

…or from the GitHub UI: **Actions → Release → Run workflow**, enter a
version.

The release artifacts are named per runner so users can pick the right one:

```
preview-app_0.1.0_ubuntu-22.04_amd64.deb    # built on 22.04, works on 22.04+
preview-app_0.1.0_ubuntu-24.04_amd64.deb    # built on 24.04
```

## Features

- **Image viewer** — open PNG/JPG/etc., select text within the image via OCR, copy with `Ctrl+C`.
- **PDF viewer** — text-layer selection for born-digital PDFs; OCR fallback for scanned PDFs. Per-page badge shows which mode is active.
- **Rubber-band region copy** — toggle `R`, drag a rectangle, copy the rendered region to clipboard or save as PNG.
- **Signature library** — draw with mouse or type in a cursive font, save named signatures, one marked default.
- **PDF signing** — pick a signature, place and resize on a page, Save (in-place, incremental) or Save As.

## Shortcuts

| Shortcut         | Action                      |
|------------------|-----------------------------|
| `Ctrl+O`         | Open file                   |
| `Ctrl+S`         | Save (incremental for PDFs) |
| `Ctrl+Shift+S`   | Save As                     |
| `Ctrl+W`         | Close tab                   |
| `Ctrl+C`         | Copy selected text/region   |
| `V`              | Text-select mode            |
| `R`              | Rect-select mode            |
| `Ctrl+=` / `Ctrl+-` | Zoom in / out            |
| `Ctrl+0`         | Fit width                   |

## Credits

Bundled cursive fonts are from Google Fonts, licensed under the [SIL Open Font License 1.1](resources/fonts/OFL.txt):

- Dancing Script — Pablo Impallari, Rodrigo Fuenzalida, Igino Marini
- Great Vibes — TypeSETit
- Caveat — Impallari Type
