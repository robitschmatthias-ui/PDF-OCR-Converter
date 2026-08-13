"""GNOME Files (Nautilus) extension for PDF-OCR-Converter.

Adds right-click context-menu entries to PDF files:
  * "OCR to DOCX"          — convert the selected PDF(s)
  * "Merge & OCR to DOCX"  — merge 2+ selected PDFs, then OCR (multi-select)
  * "OCR Settings"         — configure Adobe PDF Services credentials

The installer copies this file to
  ~/.local/share/nautilus-python/extensions/pdf_ocr_converter.py
and substitutes __PROJECT_DIR__ with the repository location. The menu
handlers launch the venv wrapper scripts under install/fedora/, which show
the tkinter dialogs and run the Adobe OCR job.

Requires the `nautilus-python` package. Supports both nautilus-python 4.x
(GTK4 Nautilus, current Fedora) and 3.x (legacy GTK3).
"""
import glob
import os
import subprocess

import gi


def _require_nautilus():
    """Pin the Nautilus GObject-introspection binding to whatever version is
    actually installed.

    The typelib version tracks the Nautilus release (e.g. GNOME 50 ships
    ``Nautilus-4.1``, older GTK4 releases ``Nautilus-4.0``, legacy GTK3
    ``Nautilus-3.0``). Rather than hard-code one, discover the installed
    versions from the girepository directories and try them newest-first,
    falling back to a known list. This keeps the extension working across
    Nautilus upgrades without edits.
    """
    search_dirs = [d for d in os.environ.get("GI_TYPELIB_PATH", "").split(os.pathsep) if d]
    search_dirs += ["/usr/lib64/girepository-1.0", "/usr/lib/girepository-1.0"]

    discovered = set()
    for directory in search_dirs:
        for path in glob.glob(os.path.join(directory, "Nautilus-*.typelib")):
            version = os.path.basename(path)[len("Nautilus-"):-len(".typelib")]
            discovered.add(version)

    def _version_key(version):
        return [int(part) if part.isdigit() else part for part in version.split(".")]

    candidates = sorted(discovered, key=_version_key, reverse=True)
    for fallback in ("4.1", "4.0", "3.0"):
        if fallback not in candidates:
            candidates.append(fallback)

    for version in candidates:
        try:
            gi.require_version("Nautilus", version)
            return version
        except ValueError:
            continue
    raise ValueError(
        "No Nautilus GObject-introspection typelib found. "
        "Is the 'nautilus-python' package installed?"
    )


_require_nautilus()

from gi.repository import GObject, Nautilus  # noqa: E402

PROJECT_DIR = "__PROJECT_DIR__"
WRAPPER_DIR = os.path.join(PROJECT_DIR, "install", "fedora")
OCR_WRAPPER = os.path.join(WRAPPER_DIR, "ocr_convert.sh")
MERGE_WRAPPER = os.path.join(WRAPPER_DIR, "merge_and_ocr.sh")
SETTINGS_WRAPPER = os.path.join(WRAPPER_DIR, "setup_credentials.sh")


def _is_pdf(file_info):
    """True if the FileInfo looks like a local PDF."""
    if file_info.get_uri_scheme() != "file":
        return False
    try:
        if file_info.get_mime_type() == "application/pdf":
            return True
    except Exception:
        pass
    name = file_info.get_name() or ""
    return name.lower().endswith(".pdf")


def _local_paths(files):
    paths = []
    for f in files:
        location = f.get_location()
        path = location.get_path() if location is not None else None
        if path:
            paths.append(path)
    return paths


class PdfOcrMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    """Provides the PDF-OCR context-menu entries."""

    def _launch(self, wrapper, paths):
        try:
            subprocess.Popen([wrapper, *paths], cwd=PROJECT_DIR)
        except Exception:
            # Nautilus swallows extension exceptions silently; failing here
            # would only hang the menu, so degrade gracefully.
            pass

    def _menu_items(self, files):
        pdfs = [f for f in files if _is_pdf(f)]
        if not pdfs:
            return []
        paths = _local_paths(pdfs)
        if not paths:
            return []

        items = []

        ocr_item = Nautilus.MenuItem(
            name="PdfOcrConverter::ocr_to_docx",
            label="OCR to DOCX",
            tip="Convert PDF(s) to DOCX via Adobe OCR",
        )
        ocr_item.connect("activate", lambda _item: self._launch(OCR_WRAPPER, paths))
        items.append(ocr_item)

        if len(paths) >= 2:
            merge_item = Nautilus.MenuItem(
                name="PdfOcrConverter::merge_and_ocr",
                label="Merge & OCR to DOCX",
                tip="Merge selected PDFs and convert to DOCX via Adobe OCR",
            )
            merge_item.connect("activate", lambda _item: self._launch(MERGE_WRAPPER, paths))
            items.append(merge_item)

        settings_item = Nautilus.MenuItem(
            name="PdfOcrConverter::settings",
            label="OCR Settings",
            tip="Configure Adobe PDF Services credentials",
        )
        settings_item.connect("activate", lambda _item: self._launch(SETTINGS_WRAPPER, []))
        items.append(settings_item)

        return items

    # nautilus-python 4.0 signature: get_file_items(self, files)
    # nautilus-python 3.0 signature: get_file_items(self, window, files)
    # Accept both by taking the last positional argument as the file list.
    def get_file_items(self, *args):
        files = args[-1]
        return self._menu_items(files)
