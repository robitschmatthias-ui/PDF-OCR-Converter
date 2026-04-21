#!/usr/bin/env python3
"""Merge multiple PDFs into one, then run Adobe OCR on the result.

Usage:
  python merge_and_ocr.py <file1.pdf> <file2.pdf> [...]

Behavior:
  - Files are merged in the order given (Nemo passes them sorted).
  - The merged PDF is written to a temp file, processed by Adobe OCR,
    and then securely deleted.
  - Output DOCX is saved next to the FIRST input file with suffix "_OCR":
      <first>_OCR.docx
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from pypdf import PdfWriter

from config import load_config, CredentialsMissingError, setup_logging
from ocr_convert import (
    _build_services,
    _choose_locale,
    _notify,
    _ocr_then_export,
    _run_with_progress,
)

logger = logging.getLogger("pdf-ocr-converter.merge")


def _secure_delete(path: Path) -> None:
    """Best-effort secure delete: overwrite with zeros, then unlink."""
    try:
        if path.exists():
            size = path.stat().st_size
            with open(path, "r+b") as f:
                f.write(b"\x00" * size)
                f.flush()
                os.fsync(f.fileno())
            path.unlink()
    except Exception:
        logger.warning("Secure delete failed for %s; attempting plain unlink.", path.name)
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.exception("Failed to delete temp file %s", path.name)


def merge_pdfs(inputs: list[Path], output: Path) -> None:
    writer = PdfWriter()
    for pdf in inputs:
        writer.append(str(pdf))
    with open(output, "wb") as f:
        writer.write(f)
    writer.close()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: merge_and_ocr.py <file1.pdf> <file2.pdf> [...]", file=sys.stderr)
        return 2

    files = [Path(p).expanduser().resolve() for p in argv[1:]]
    missing = [p for p in files if not p.is_file()]
    if missing:
        _notify("Merge & OCR failed", f"File not found: {missing[0].name}")
        return 1

    try:
        cfg = load_config()
    except CredentialsMissingError as e:
        _notify("OCR setup needed", str(e))
        return 1

    first = files[0]
    output_docx = first.with_name(f"{first.stem}_OCR.docx")
    locale = _choose_locale(cfg.default_locale)
    if not locale:
        return 0  # User cancelled

    tmp_fd, tmp_name = tempfile.mkstemp(prefix="pdfocr-merge-", suffix=".pdf")
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    def _merge_and_ocr():
        merge_pdfs(files, tmp_path)
        pdf_services = _build_services(cfg.client_id, cfg.client_secret)
        return _ocr_then_export(pdf_services, tmp_path, locale)

    try:
        data = _run_with_progress(_merge_and_ocr)
        output_docx.write_bytes(data)
        _notify("Merge & OCR complete", f"Saved: {output_docx.name}")
        return 0
    except Exception as e:
        logger.exception("Merge & OCR failed")
        _notify("Merge & OCR failed", f"{type(e).__name__}")
        return 1
    finally:
        _secure_delete(tmp_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    setup_logging()
    sys.exit(main(sys.argv))
