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
from pathlib import Path

from config import load_config, CredentialsMissingError, setup_logging

logger = logging.getLogger("pdf-ocr-converter")


def _notify(title: str, message: str) -> None:
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="PDF-OCR-Converter", timeout=6)
    except Exception:
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
    root.geometry("360x130")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    frm = ttk.Frame(root, padding=20)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="OCR running…",
              font=("", 11, "bold")).pack(anchor="w", pady=(0, 4))
    ttk.Label(frm, text="Adobe is processing your document. Please wait.",
              foreground="gray", wraplength=320).pack(anchor="w", pady=(0, 12))
    pb = ttk.Progressbar(frm, mode="indeterminate", length=320)
    pb.pack(fill="x")
    pb.start(12)

    box = {"value": None, "exc": None}

    def worker():
        try:
            box["value"] = work()
        except BaseException as e:
            box["exc"] = e
        finally:
            root.after(0, root.destroy)

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    if box["exc"] is not None:
        raise box["exc"]
    return box["value"]


def _build_services(client_id: str, client_secret: str):
    from adobe.pdfservices.operation.auth.service_principal_credentials import (
        ServicePrincipalCredentials,
    )
    from adobe.pdfservices.operation.pdf_services import PDFServices

    creds = ServicePrincipalCredentials(client_id=client_id, client_secret=client_secret)
    return PDFServices(credentials=creds)


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
    data = _ocr_then_export(pdf_services, pdf_path, locale)
    output_path.write_bytes(data)
    return output_path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: ocr_convert.py <file.pdf> [<file2.pdf> ...]", file=sys.stderr)
        return 2

    files = [Path(p).expanduser().resolve() for p in argv[1:]]
    missing = [p for p in files if not p.is_file()]
    if missing:
        _notify("OCR failed", f"File not found: {missing[0].name}")
        return 1

    try:
        cfg = load_config()
    except CredentialsMissingError as e:
        _notify("OCR setup needed", str(e))
        return 1

    locale = _choose_locale(cfg.default_locale)
    if not locale:
        return 0  # User cancelled
    pdf_services = _build_services(cfg.client_id, cfg.client_secret)

    def _run_all():
        errors = 0
        for pdf in files:
            try:
                out = convert(pdf, locale, pdf_services)
                _notify("OCR complete", f"Saved: {out.name}")
            except Exception as e:
                errors += 1
                logger.exception("OCR failed for %s", pdf.name)
                _notify("OCR failed", f"{pdf.name}: {type(e).__name__}")
        return errors

    errors = _run_with_progress(_run_all)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    setup_logging()
    sys.exit(main(sys.argv))
