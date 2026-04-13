"""Configuration and credential loading for PDF-OCR-Converter.

Credentials are stored OUTSIDE the project directory to avoid accidental
commits. Location:
  Linux:   ~/.config/pdf-ocr-converter/.env
  Windows: %APPDATA%\\pdf-ocr-converter\\.env
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


APP_NAME = "pdf-ocr-converter"


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def config_file() -> Path:
    return config_dir() / ".env"


def log_file() -> Path:
    return config_dir() / "ocr.log"


def setup_logging() -> None:
    """Attach a file handler so errors are visible even under pythonw.exe (Windows).

    Log rotates at 1 MB; 3 backups kept. Never writes credentials.
    """
    import logging
    from logging.handlers import RotatingFileHandler

    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers if called twice
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(path)
               for h in root.handlers):
        root.addHandler(handler)


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    default_locale: str


class CredentialsMissingError(RuntimeError):
    pass


def load_config() -> Config:
    path = config_file()
    if not path.exists():
        raise CredentialsMissingError(
            f"No credentials found at {path}. Run setup_credentials.py first."
        )
    values = dotenv_values(path)
    client_id = (values.get("PDF_SERVICES_CLIENT_ID") or "").strip()
    client_secret = (values.get("PDF_SERVICES_CLIENT_SECRET") or "").strip()
    default_locale = (values.get("OCR_DEFAULT_LOCALE") or "de-de").strip()
    if not client_id or not client_secret:
        raise CredentialsMissingError(
            f"Credentials in {path} are incomplete. Run setup_credentials.py."
        )
    return Config(client_id, client_secret, default_locale)


def credentials_configured() -> bool:
    try:
        load_config()
        return True
    except CredentialsMissingError:
        return False
