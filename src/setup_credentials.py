#!/usr/bin/env python3
"""Interactive credential setup for PDF-OCR-Converter.

Prompts for Adobe PDF Services API credentials (Client ID + Client Secret)
and the default OCR locale, then stores them in the user's config directory
OUTSIDE the project repo.

Usage:
  python setup_credentials.py           # GUI dialog (tkinter)
  python setup_credentials.py --cli     # Fallback CLI prompt
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

from config import config_dir, config_file, load_config, CredentialsMissingError


SUPPORTED_LOCALES = [
    "de-de", "de-ch", "en-us", "en-gb",
    "fr-fr", "it-it", "es-es", "nl-nl", "pt-br",
    "da-dk", "fi-fi", "nb-no", "sv-se",
    "cs-cz", "pl-pl", "hu-hu", "ro-ro", "sk-sk", "sl-si", "hr-hr",
    "bg-bg", "el-gr", "et-ee", "lt-lt", "lv-lv", "mk-mk", "mt-mt",
    "ru-ru", "tr-tr", "uk-ua",
    "ja-jp", "ko-kr", "zh-cn", "zh-hk",
    "iw-il",
]


def _write_env(client_id: str, client_secret: str, locale: str) -> Path:
    cfg_dir = config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    path = config_file()
    content = (
        "# PDF-OCR-Converter credentials — managed by setup_credentials.py\n"
        f"PDF_SERVICES_CLIENT_ID={client_id}\n"
        f"PDF_SERVICES_CLIENT_SECRET={client_secret}\n"
        f"OCR_DEFAULT_LOCALE={locale}\n"
    )
    path.write_text(content, encoding="utf-8")
    if sys.platform != "win32":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def _current_values() -> tuple[str, str, str]:
    try:
        cfg = load_config()
        return cfg.client_id, cfg.client_secret, cfg.default_locale
    except CredentialsMissingError:
        return "", "", "de-de"


def _mask(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def run_cli() -> int:
    client_id, client_secret, locale = _current_values()
    print("Adobe PDF OCR Converter — Credentials Setup")
    print("=" * 48)
    print(f"Config file: {config_file()}")
    print(f"Current Client ID:     {_mask(client_id)}")
    print(f"Current Client Secret: {_mask(client_secret)}")
    print(f"Current default locale: {locale or '(none)'}")
    print()
    new_id = input(f"Client ID [{_mask(client_id)}]: ").strip() or client_id
    new_secret = input(f"Client Secret [{_mask(client_secret)}]: ").strip() or client_secret
    print(f"Supported locales: {', '.join(SUPPORTED_LOCALES)}")
    new_locale = input(f"Default OCR locale [{locale}]: ").strip() or locale
    if not new_id or not new_secret:
        print("ERROR: Client ID and Client Secret are required.", file=sys.stderr)
        return 1
    path = _write_env(new_id, new_secret, new_locale)
    print(f"\n✓ Credentials saved to {path}")
    return 0


def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("tkinter not available, falling back to CLI.", file=sys.stderr)
        return run_cli()

    client_id, client_secret, locale = _current_values()
    result = {"ok": False}

    root = tk.Tk()
    root.title("PDF-OCR-Converter — Settings")
    root.geometry("520x280")

    frm = ttk.Frame(root, padding=16)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Adobe PDF Services API Credentials",
              font=("", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    ttk.Label(frm, text="Client ID:").grid(row=1, column=0, sticky="w", pady=4)
    id_var = tk.StringVar(value=client_id)
    ttk.Entry(frm, textvariable=id_var, width=48).grid(row=1, column=1, sticky="ew", pady=4)

    ttk.Label(frm, text="Client Secret:").grid(row=2, column=0, sticky="w", pady=4)
    secret_var = tk.StringVar(value=client_secret)
    ttk.Entry(frm, textvariable=secret_var, width=48, show="•").grid(row=2, column=1, sticky="ew", pady=4)

    ttk.Label(frm, text="Default locale:").grid(row=3, column=0, sticky="w", pady=4)
    locale_var = tk.StringVar(value=locale or "de-de")
    ttk.Combobox(frm, textvariable=locale_var, values=SUPPORTED_LOCALES,
                 state="readonly", width=12).grid(row=3, column=1, sticky="w", pady=4)

    ttk.Label(frm, text=f"Saved to: {config_file()}",
              foreground="gray").grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

    btns = ttk.Frame(frm)
    btns.grid(row=5, column=0, columnspan=2, pady=(16, 0), sticky="e")

    def on_save():
        if not id_var.get().strip() or not secret_var.get().strip():
            messagebox.showerror("Error", "Client ID and Client Secret are required.")
            return
        _write_env(id_var.get().strip(), secret_var.get().strip(), locale_var.get().strip())
        result["ok"] = True
        messagebox.showinfo("Success", "Credentials saved.")
        root.destroy()

    ttk.Button(btns, text="Cancel", command=root.destroy).pack(side="right", padx=(0, 0))
    ttk.Button(btns, text="Save", command=on_save).pack(side="right", padx=(0, 8))

    frm.columnconfigure(1, weight=1)
    root.mainloop()
    return 0 if result["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Adobe PDF Services credentials.")
    parser.add_argument("--cli", action="store_true", help="Use CLI prompts instead of GUI")
    args = parser.parse_args()
    return run_cli() if args.cli else run_gui()


if __name__ == "__main__":
    sys.exit(main())
