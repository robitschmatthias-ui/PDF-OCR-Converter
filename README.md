# PDF-OCR-Converter

![platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-blue)
![language](https://img.shields.io/badge/language-Python%203.10%2B-yellow)
![file-manager](https://img.shields.io/badge/file--manager-Nemo%20%7C%20Explorer-orange)
![OCR](https://img.shields.io/badge/OCR-Adobe%20PDF%20Services-red)
![license](https://img.shields.io/badge/license-GPL%20v3-blue)
![Stars](https://img.shields.io/github/stars/robitschmatthias-ui/PDF-OCR-Converter?style=social)

> 🇩🇪 **Deutsche Version:** siehe [README.de.md](README.de.md)

A cross-platform tool that converts PDF files to editable DOCX via the
**Adobe PDF Services API** (OCR), triggered by right-click context menu
on Linux (Nemo) and Windows (Explorer).

## Features

- **Right-click integration** on Linux (Nemo) and Windows (Explorer)
- **OCR to DOCX** — convert a single PDF or multiple PDFs (one-by-one)
- **Merge & OCR to DOCX** (Linux only, multi-selection) — combines several
  PDFs into one using the [Linux-PDF-Merge-in-Nemo](https://github.com/robitschmatthias-ui/Linux-PDF-Merge-in-Nemo)
  Quick Merge, then sends the merged file to Adobe OCR
- **Language dialog** — choose the OCR language (tkinter)
- **Desktop notifications** via `plyer`
- **Secure credential handling** — credentials are stored outside the repo
  in `~/.config/pdf-ocr-converter/.env` (never committed to git)

## Output naming

Files returned from Adobe always receive the suffix `_OCR`, e.g.
`invoice.pdf` → `invoice_OCR.docx`. When merging multiple files, the result
inherits the name of the **first** file in the selection.

## Prerequisites

- Python 3.10+
- An Adobe Developer Console account with PDF Services API credentials
  (see [docs/adobe-credentials.md](docs/adobe-credentials.md))
- **Free tier:** 500 transactions/month (~250 OCR conversions)

## Getting Adobe API credentials

You need a free Adobe Developer account.
**Free tier: 500 transactions/month** — each OCR conversion uses 2 transactions
(OCR + DOCX export), so you can process **~250 files per month** for free.

1. Go to <https://developer.adobe.com/console> and sign in (or sign up — free).
2. Click **Create new project**.
3. In the project, click **Add API** → select **PDF Services API** → **Next**.
4. Choose **OAuth Server-to-Server** authentication → **Save configured API**.
5. On the credentials page, copy:
   - **Client ID**
   - **Client Secret** (click *"Retrieve client secret"*)
6. Enter both in the setup dialog (opens automatically on first install, or via
   right-click → **OCR Settings**).

Credentials are saved to `~/.config/pdf-ocr-converter/.env` on Linux or
`%APPDATA%\pdf-ocr-converter\.env` on Windows — never inside the repo.

For the full walkthrough see [docs/adobe-credentials.md](docs/adobe-credentials.md).

## Installation

### Linux (Nemo)

```bash
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git ~/scripts/pdf-ocr-converter
cd ~/scripts/pdf-ocr-converter
bash install/linux/install.sh
```

On first use, a setup dialog prompts for your Adobe credentials and stores
them in `~/.config/pdf-ocr-converter/.env`.

### Windows (Explorer)

**Prerequisite: Git** must be installed. If PowerShell tells you
*"git: The term 'git' is not recognized..."*, install it once:

```powershell
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
```

Then **close PowerShell and open a new window** (the current session does
not yet know the new Git path).

Then install:

```powershell
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git $env:LOCALAPPDATA\pdf-ocr-converter
cd $env:LOCALAPPDATA\pdf-ocr-converter
install\windows\install.bat
```

The `.bat` wrapper handles PowerShell's execution policy automatically.
Python is installed automatically via `winget` if missing — the installer
restarts itself in a new shell to pick up the updated PATH, no manual steps needed.
A live spinner shows progress during long-running steps.

## Usage

Three context-menu entries appear on PDF files:

| Entry | Behavior |
|---|---|
| **OCR to DOCX** | Single file or multi-select (each processed separately) |
| **Merge & OCR to DOCX** | Multi-select only (Linux); merges first, then OCR |
| **OCR Settings** | Re-enter / change Adobe credentials |

A small progress window ("OCR running...") appears during processing and
closes automatically when Adobe is done. The bar is indeterminate because
the Adobe SDK provides no percentage feedback. A system notification fires
on success or failure.

## Security

- Credentials are stored **outside** the project directory (never commitable)
- Temporary merge files are securely deleted after processing
- Logs never contain credentials or sensitive paths
- Future upgrade path: OS keychain (GNOME Keyring / Windows Credential Manager)

> **Privacy note:** Adobe processes documents on AWS US-East servers and
> retains them for up to 24 hours. Consider this for GDPR-sensitive documents.

## License

GPL-3.0 — see [LICENSE](LICENSE).

## Credits

Built on top of the [Adobe PDF Services Python SDK](https://github.com/adobe/pdfservices-python-sdk-samples)
and inspired by [Linux-PDF-Merge-in-Nemo](https://github.com/robitschmatthias-ui/Linux-PDF-Merge-in-Nemo).

---

> 🤖 **Vibe-coded:** This project was built in a conversational "vibe coding"
> session with an AI assistant — design, code, installers, and docs generated
> through iterative dialogue.
