#!/usr/bin/env python3
"""Convert a PDF to DOCX via Adobe PDF Services OCR.

Usage:
  python ocr_convert.py <file.pdf> [<file2.pdf> ...]

Each file is processed independently. Output: <basename>_OCR.docx next to
the input file.

Two Adobe API transactions are consumed per file:
  1) OCR on the PDF
  2) Export the OCR'd PDF to DOCX
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import load_config, CredentialsMissingError, setup_logging

logger = logging.getLogger("pdf-ocr-converter")

_TRANSIENT_RETRIES = 2
_TRANSIENT_RETRY_DELAY = 5  # seconds

# Generous: a real job normally finishes in well under a minute. Adobe's own
# backend gave up with a 504 after ~10 minutes in an observed hang; this caps
# it well before that so the tool fails clearly instead of hanging forever.
_JOB_TIMEOUT_SECONDS = 240

_EXISTING_TEXT_LAYER_MIN_CHARS = 20
# Adobe PDF Services documents a 100 MB limit for all input files.
_MAX_FILE_BYTES = 100 * 1024 * 1024
# Not in Adobe's official limits table, but OCR requests beyond roughly this
# many pages are reported to fail with PAGE_LIMIT_EXCEEDED - so warn, don't block.
_PAGE_WARN_LIMIT = 100


class JobTimeout(Exception):
    """Adobe did not respond within the configured time budget."""


class UserCancelled(Exception):
    """The user cancelled a running job via the progress window."""


@dataclass
class Preflight:
    """Outcome of the local checks run before anything is sent to Adobe.

    `error` means Adobe would reject the file, so it is not sent at all.
    `warnings` are risks the user may choose to accept.
    """
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    pages: int = 0


def _run_with_timeout(func, *args, timeout=_JOB_TIMEOUT_SECONDS, **kwargs):
    """Run func in a daemon thread, enforcing a wall-clock timeout.

    If func doesn't finish in time, raises JobTimeout immediately. The
    worker thread is abandoned (an in-flight HTTP call cannot be cancelled
    from here) and dies with the process.
    """
    box = {"value": None, "exc": None, "done": False}

    def worker():
        try:
            box["value"] = func(*args, **kwargs)
        except BaseException as e:
            box["exc"] = e
        finally:
            box["done"] = True

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    if not box["done"]:
        raise JobTimeout(f"Adobe did not respond within {timeout}s")
    if box["exc"] is not None:
        raise box["exc"]
    return box["value"]


def _preflight(pdf_path: Path) -> Preflight:
    """Check a PDF locally for everything Adobe is known to reject or choke on."""
    from pypdf import PdfReader

    result = Preflight()

    size = pdf_path.stat().st_size
    if size > _MAX_FILE_BYTES:
        result.error = (
            f"The file is {size / 1024 / 1024:.0f} MB; Adobe accepts at most "
            f"{_MAX_FILE_BYTES // 1024 // 1024} MB."
        )
        return result

    # The PDF spec allows the header anywhere in the first 1024 bytes.
    with open(pdf_path, "rb") as f:
        if b"%PDF-" not in f.read(1024):
            result.error = "The file is not a PDF (only its name ends in .pdf)."
            return result

    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            if not reader.decrypt(""):
                result.error = (
                    "The PDF is password-protected. Remove the password "
                    "first, then try again."
                )
                return result
            result.warnings.append(
                "The PDF is encrypted (it opens without a password, but its "
                "permissions are restricted). Adobe may reject it."
            )
        result.pages = len(reader.pages)
    except Exception as e:
        logger.warning("Preflight could not read %s", pdf_path.name, exc_info=True)
        result.error = f"The PDF cannot be read and is probably damaged ({type(e).__name__})."
        return result

    if result.pages > _PAGE_WARN_LIMIT:
        result.warnings.append(
            f"The PDF has {result.pages} pages. Adobe's OCR is known to "
            f"reject documents beyond about {_PAGE_WARN_LIMIT} pages."
        )

    # Scanners sometimes embed their own (occasionally malformed) text/OCR
    # layer. Adobe's OCR has been observed to hang on such files until it
    # gives up with a 504 after ~10 minutes.
    for page in reader.pages:
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            continue
        if len(text) >= _EXISTING_TEXT_LAYER_MIN_CHARS:
            result.warnings.append(
                "The PDF already contains text (it is a digital PDF, or the "
                "scanner added its own OCR layer). This has been observed to "
                "make Adobe's OCR hang until it times out."
            )
            break

    return result


def _confirm_warnings(subject: str, warnings: list[str]) -> bool:
    """Ask the user whether to proceed despite the warnings. True = proceed."""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        return True

    root = tk.Tk()
    root.withdraw()
    proceed = messagebox.askyesno(
        "PDF-OCR-Converter",
        f"{subject}:\n\n"
        + "\n\n".join(f"• {w}" for w in warnings)
        + "\n\nRun OCR anyway?",
        icon="warning",
    )
    root.destroy()
    return proceed


def _show_error(title: str, message: str) -> None:
    """Show an error the user has to acknowledge.

    A desktop notification disappears after a few seconds, which is easy to
    miss after waiting minutes for Adobe - so failures get a modal dialog.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        _notify(title, message)
        return

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()


def _with_retry(func, *args, **kwargs):
    """Run func, retrying on transient network/timeout errors from the Adobe
    SDK (it does not retry these itself; a brief hiccup otherwise aborts the
    whole job with no output file). Non-transient errors raise immediately.
    """
    from adobe.pdfservices.operation.exception.exceptions import SdkException

    for attempt in range(1, _TRANSIENT_RETRIES + 2):
        try:
            return func(*args, **kwargs)
        except SdkException as e:
            tracking = getattr(e, "request_tracking_id", None)
            cause = tracking[1] if tracking else None
            is_transient = cause is not None and type(cause).__name__ in (
                "ReadTimeout",
                "ConnectTimeout",
                "ConnectionError",
                "Timeout",
            )
            if not is_transient or attempt > _TRANSIENT_RETRIES:
                raise
            logger.warning(
                "Transient network error (attempt %d/%d), retrying in %ds: %s",
                attempt, _TRANSIENT_RETRIES + 1, _TRANSIENT_RETRY_DELAY, cause,
            )
            time.sleep(_TRANSIENT_RETRY_DELAY)


def _notify(title: str, message: str) -> None:
    """Show a desktop notification.

    Tries plyer first, then falls back to notify-send (libnotify, standard on
    Fedora/GNOME), and finally to stdout so nothing is ever silently lost.
    """
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="PDF-OCR-Converter", timeout=6)
        return
    except Exception:
        pass
    try:
        import shutil
        import subprocess
        if shutil.which("notify-send"):
            subprocess.run(
                ["notify-send", "--app-name=PDF-OCR-Converter", title, message],
                check=False,
            )
            return
    except Exception:
        pass
    print(f"[{title}] {message}")


def _choose_locale(default: str) -> str:
    """Show a tkinter dropdown for OCR locale. Returns locale string."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        return default

    from setup_credentials import SUPPORTED_LOCALES

    result = {"locale": default, "confirmed": False}
    root = tk.Tk()
    root.title("PDF-OCR-Converter — Document Language")
    root.geometry("420x220")
    frm = ttk.Frame(root, padding=16)
    frm.pack(fill="both", expand=True)
    ttk.Label(
        frm,
        text="In which language is the text of the PDF you want to convert?",
        wraplength=380,
        font=("", 10, "bold"),
    ).pack(anchor="w", pady=(0, 6))
    ttk.Label(
        frm,
        text="Choose the language Adobe OCR should use to recognize the text.",
        foreground="gray",
        wraplength=380,
    ).pack(anchor="w", pady=(0, 10))
    var = tk.StringVar(value=default)
    ttk.Combobox(frm, textvariable=var, values=SUPPORTED_LOCALES,
                 state="readonly").pack(fill="x")
    btns = ttk.Frame(frm)
    btns.pack(fill="x", pady=(12, 0))

    def ok():
        result["locale"] = var.get()
        result["confirmed"] = True
        root.destroy()

    ttk.Button(btns, text="Start OCR", command=ok).pack(side="right")
    ttk.Button(btns, text="Cancel", command=root.destroy).pack(side="right", padx=(0, 8))
    root.mainloop()
    if not result["confirmed"]:
        return ""
    return result["locale"]


def _run_with_progress(work):
    """Run `work` in a background thread while showing an indeterminate
    spinner window. Returns whatever `work` returned, or re-raises its
    exception. Falls back to running synchronously if tkinter is unavailable.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        return work()

    root = tk.Tk()
    root.title("PDF-OCR-Converter")
    root.geometry("360x150")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    frm = ttk.Frame(root, padding=20)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="OCR running…",
              font=("", 11, "bold")).pack(anchor="w", pady=(0, 4))
    ttk.Label(frm, text="Adobe is processing your document. Please wait.",
              foreground="gray", wraplength=320).pack(anchor="w", pady=(0, 12))
    pb = ttk.Progressbar(frm, mode="indeterminate", length=320)
    pb.pack(fill="x")
    pb.start(12)
    ttk.Label(frm, text="Closing this window cancels the conversion.",
              foreground="gray", font=("", 8)).pack(anchor="w", pady=(10, 0))

    box = {"value": None, "exc": None, "cancelled": False}

    def worker():
        try:
            box["value"] = work()
        except BaseException as e:
            box["exc"] = e
        finally:
            root.after(0, root.destroy)

    def on_cancel():
        box["cancelled"] = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    if box["cancelled"]:
        raise UserCancelled("Cancelled by user")
    if box["exc"] is not None:
        raise box["exc"]
    return box["value"]


def _build_services(client_id: str, client_secret: str):
    from adobe.pdfservices.operation.auth.service_principal_credentials import (
        ServicePrincipalCredentials,
    )
    from adobe.pdfservices.operation.config.client_config import ClientConfig
    from adobe.pdfservices.operation.pdf_services import PDFServices

    creds = ServicePrincipalCredentials(client_id=client_id, client_secret=client_secret)
    # Adobe's SDK default connect_timeout (4s) is too tight for polling job
    # status over a real-world connection; a brief network hiccup aborts the
    # whole job with no retry and no output file.
    client_config = ClientConfig(connect_timeout=10000, read_timeout=20000)
    return PDFServices(credentials=creds, client_config=client_config)


def _ocr_then_export(pdf_services, input_pdf: Path, locale: str) -> bytes:
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.pdfjobs.jobs.ocr_pdf_job import OCRPDFJob
    from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_params import OCRParams
    from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_supported_locale import (
        OCRSupportedLocale,
    )
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import (
        ExportPDFParams,
    )
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import (
        ExportPDFTargetFormat,
    )
    from adobe.pdfservices.operation.pdfjobs.result.ocr_pdf_result import OCRPDFResult
    from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult

    with open(input_pdf, "rb") as f:
        input_stream = f.read()

    input_asset = pdf_services.upload(
        input_stream=input_stream, mime_type=PDFServicesMediaType.PDF
    )

    # 1) OCR
    locale_enum = _locale_to_enum(locale, OCRSupportedLocale)
    ocr_params = OCRParams(ocr_locale=locale_enum)
    ocr_job = OCRPDFJob(input_asset=input_asset, ocr_pdf_params=ocr_params)
    ocr_location = pdf_services.submit(ocr_job)
    ocr_response = pdf_services.get_job_result(ocr_location, OCRPDFResult)
    ocr_asset = ocr_response.get_result().get_asset()

    # 2) Export to DOCX
    export_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX)
    export_job = ExportPDFJob(input_asset=ocr_asset, export_pdf_params=export_params)
    export_location = pdf_services.submit(export_job)
    export_response = pdf_services.get_job_result(export_location, ExportPDFResult)
    result_asset = export_response.get_result().get_asset()

    stream_asset = pdf_services.get_content(result_asset)
    return stream_asset.get_input_stream()


def _locale_to_enum(locale: str, enum_cls):
    key = locale.replace("-", "_").upper()
    if hasattr(enum_cls, key):
        return getattr(enum_cls, key)
    return enum_cls.EN_US


def convert(pdf_path: Path, locale: str, pdf_services) -> Path:
    output_path = pdf_path.with_name(f"{pdf_path.stem}_OCR.docx")
    data = _run_with_timeout(_with_retry, _ocr_then_export, pdf_services, pdf_path, locale)
    output_path.write_bytes(data)
    return output_path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: ocr_convert.py <file.pdf> [<file2.pdf> ...]", file=sys.stderr)
        return 2

    files = [Path(p).expanduser().resolve() for p in argv[1:]]
    missing = [p for p in files if not p.is_file()]
    if missing:
        _show_error("OCR failed", f"File not found: {missing[0].name}")
        return 1

    try:
        cfg = load_config()
    except CredentialsMissingError as e:
        _show_error("OCR setup needed", str(e))
        return 1

    rejected: list[tuple[str, str]] = []
    to_process = []
    for pdf in files:
        pf = _preflight(pdf)
        if pf.error:
            logger.error("Preflight rejected %s: %s", pdf.name, pf.error)
            rejected.append((pdf.name, pf.error))
            continue
        if pf.warnings and not _confirm_warnings(pdf.name, pf.warnings):
            logger.info("Skipped by user after preflight warnings: %s", pdf.name)
            continue
        to_process.append(pdf)

    if rejected:
        _show_error("OCR not possible", _format_failures(rejected))
    if not to_process:
        return 1 if rejected else 0

    locale = _choose_locale(cfg.default_locale)
    if not locale:
        return 1 if rejected else 0  # User cancelled

    failures = _convert_all(to_process, locale, cfg)
    if failures:
        _show_error("OCR failed", _format_failures(failures))
    return 1 if rejected or failures else 0


def _format_failures(failures: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"{name}:\n{reason}" for name, reason in failures)


def _describe_error(e: Exception) -> str:
    """A short, human-readable reason for a failed Adobe call."""
    if isinstance(e, JobTimeout):
        return (
            f"Adobe did not respond within {_JOB_TIMEOUT_SECONDS // 60} minutes. "
            "Try again later; if it keeps happening, the file itself is "
            "probably the problem."
        )
    message = getattr(e, "message", None)
    code = getattr(e, "error_code", None)
    if message and code:
        return f"{message} ({code})"
    tracking = getattr(e, "request_tracking_id", None)
    if isinstance(tracking, tuple) and tracking:
        return f"Network problem while talking to Adobe ({tracking[0].__name__})."
    return message or type(e).__name__


def _convert_all(files: list[Path], locale: str, cfg) -> list[tuple[str, str]]:
    """Convert each file; returns (filename, reason) for every failure."""
    pdf_services = _build_services(cfg.client_id, cfg.client_secret)

    def _run_all():
        failures = []
        for pdf in files:
            try:
                out = convert(pdf, locale, pdf_services)
                _notify("OCR complete", f"Saved: {out.name}")
            except Exception as e:
                logger.exception("OCR failed for %s", pdf.name)
                failures.append((pdf.name, _describe_error(e)))
        return failures

    try:
        return _run_with_progress(_run_all)
    except UserCancelled:
        logger.info("Cancelled by user")
        return []


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    setup_logging()
    sys.exit(main(sys.argv))
