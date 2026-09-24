#!/usr/bin/env python3
"""Merge multiple PDFs into one, then run Adobe OCR on the result.

Usage:
  python merge_and_ocr.py <file1.pdf> <file2.pdf> [...]

Behavior:
  - Files are merged in the order given (the file manager passes them sorted).
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

from pypdf import PdfReader, PdfWriter

from config import load_config, CredentialsMissingError, setup_logging
from ocr_convert import (
    _MAX_FILE_BYTES,
    _PAGE_WARN_LIMIT,
    UserCancelled,
    _build_services,
    _choose_locale,
    _confirm_warnings,
    _describe_error,
    _notify,
    _ocr_then_export,
    _preflight,
    _run_with_progress,
    _run_with_timeout,
    _show_error,
    _with_retry,
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
        _show_error("Merge & OCR failed", f"File not found: {missing[0].name}")
        return 1

    try:
        cfg = load_config()
    except CredentialsMissingError as e:
        _show_error("OCR setup needed", str(e))
        return 1

    first = files[0]
    output_docx = first.with_name(f"{first.stem}_OCR.docx")

    errors, warnings = [], []
    for pdf in files:
        pf = _preflight(pdf)
        if pf.error:
            errors.append(f"{pdf.name}:\n{pf.error}")
        warnings += [f"{pdf.name}: {w}" for w in pf.warnings]
    if errors:
        logger.error("Preflight rejected input: %s", errors)
        _show_error("Merge & OCR failed", "\n\n".join(errors))
        return 1

    tmp_fd, tmp_name = tempfile.mkstemp(prefix="pdfocr-merge-", suffix=".pdf")
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    try:
        try:
            merge_pdfs(files, tmp_path)
            merged_pages = len(PdfReader(str(tmp_path)).pages)
        except Exception as e:
            logger.exception("Merging failed")
            _show_error("Merge & OCR failed", f"The files could not be merged ({type(e).__name__}).")
            return 1

        merged_size = tmp_path.stat().st_size
        if merged_size > _MAX_FILE_BYTES:
            _show_error(
                "Merge & OCR failed",
                f"The merged PDF is {merged_size / 1024 / 1024:.0f} MB; Adobe accepts "
                f"at most {_MAX_FILE_BYTES // 1024 // 1024} MB. Merge fewer files at once.",
            )
            return 1
        if merged_pages > _PAGE_WARN_LIMIT:
            warnings.append(
                f"The merged PDF has {merged_pages} pages. Adobe's OCR is known to "
                f"reject documents beyond about {_PAGE_WARN_LIMIT} pages."
            )

        if warnings and not _confirm_warnings("The files to merge have problems", warnings):
            logger.info("Merge & OCR skipped by user after preflight warnings")
            return 0

        locale = _choose_locale(cfg.default_locale)
        if not locale:
            return 0  # User cancelled

        def _ocr():
            pdf_services = _build_services(cfg.client_id, cfg.client_secret)
            return _run_with_timeout(_with_retry, _ocr_then_export, pdf_services, tmp_path, locale)

        try:
            data = _run_with_progress(_ocr)
        except UserCancelled:
            logger.info("Merge & OCR cancelled by user")
            return 0
        except Exception as e:
            logger.exception("Merge & OCR failed")
            _show_error("Merge & OCR failed", _describe_error(e))
            return 1

        output_docx.write_bytes(data)
        _notify("Merge & OCR complete", f"Saved: {output_docx.name}")
        return 0
    finally:
        _secure_delete(tmp_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    setup_logging()
    sys.exit(main(sys.argv))
