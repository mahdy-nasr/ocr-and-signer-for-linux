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
