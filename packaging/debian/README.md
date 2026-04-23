# Debian packaging (stub)

This directory is a scaffold for building a `.deb` package later via `dpkg-buildpackage`.
It is not wired into any CI yet. To actually build a .deb, you'll need to:

1. Copy `packaging/debian/` to the project root as `debian/`.
2. Install build deps: `sudo apt install devscripts debhelper dh-python pybuild-plugin-pyproject`.
3. Run: `dpkg-buildpackage -us -uc -b`.

The stubs here assume the app is installed as a pip-installable package under `src/preview_app/`
and that the `preview-app` console script (defined in `pyproject.toml`) becomes the launcher.
