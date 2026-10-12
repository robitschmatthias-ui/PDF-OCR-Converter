# PDF-OCR-Converter

![platform](https://img.shields.io/badge/platform-Linux%20%7C%20Fedora%20%7C%20Windows-blue)
![language](https://img.shields.io/badge/language-Python%203.10%2B-yellow)
![file-manager](https://img.shields.io/badge/file--manager-Nemo%20%7C%20Nautilus%20%7C%20Explorer-orange)
![OCR](https://img.shields.io/badge/OCR-Adobe%20PDF%20Services-red)
![license](https://img.shields.io/badge/license-GPL%20v3-blue)
![Stars](https://img.shields.io/github/stars/robitschmatthias-ui/PDF-OCR-Converter?style=social)

> 🇩🇪 **Deutsche Version:** siehe [README.de.md](README.de.md)

A cross-platform tool that converts PDF files to editable DOCX via the
**Adobe PDF Services API** (OCR), triggered by right-click context menu
on Linux Mint (Nemo), Fedora/GNOME (Nautilus), and Windows (Explorer).

## Features

- **Right-click integration** on Linux Mint (Nemo), Fedora/GNOME (Nautilus),
  and Windows (Explorer)
- **OCR to DOCX** — convert a single PDF or multiple PDFs (one-by-one)
- **Merge & OCR to DOCX** (Linux and Fedora, multi-selection) — combines
  several PDFs into one, then sends the merged file to Adobe OCR. The merge
  is built in (pypdf) and needs no additional tool
- **Language dialog** — choose the OCR language (tkinter)
- **Checks before upload** — files Adobe would reject are caught locally,
  before any transaction is used (see [Checks before upload](#checks-before-upload))
- **Desktop notification** via `plyer` on success; failures open a dialog
  that stays until you close it
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

Credentials are saved to `~/.config/pdf-ocr-converter/.env` on Linux/Fedora or
`%APPDATA%\pdf-ocr-converter\.env` on Windows — never inside the repo.

For the full walkthrough see [docs/adobe-credentials.md](docs/adobe-credentials.md).

## Installation

### Linux (Nemo)

**Prerequisite: Git** must be installed. If you see
`bash: git: command not found`, install it once:

```bash
sudo apt install -y git
```

Then install:

```bash
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git ~/scripts/pdf-ocr-converter
cd ~/scripts/pdf-ocr-converter
bash install/linux/install.sh
```

On first use, a setup dialog prompts for your Adobe credentials and stores
them in `~/.config/pdf-ocr-converter/.env`.

### Fedora (GNOME Files / Nautilus)

**Prerequisite: Git** must be installed. If you see
`bash: git: command not found`, install it once:

```bash
sudo dnf install -y git
```

Then install:

```bash
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git ~/scripts/pdf-ocr-converter
cd ~/scripts/pdf-ocr-converter
bash install/fedora/install.sh
```

The installer pulls any missing system packages via `dnf` (one sudo prompt:
`python3-tkinter`, `nautilus-python`, `python3-dbus`, `libnotify`), then
copies the app into `~/.local/share/pdf-ocr-converter` and builds a `.venv`
there — so the cloned folder can be deleted afterwards, the tool keeps
working. If the right-click entries don't appear right away, log out and
back in once so GNOME loads the new Nautilus extension. To uninstall later,
run `bash install/fedora/uninstall.sh` from the app folder.

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
| **Merge & OCR to DOCX** | Multi-select only (Linux Mint, Fedora); merges first, then OCR |
| **OCR Settings** | Re-enter / change Adobe credentials |

A small progress window ("OCR running...") appears during processing and
closes automatically when Adobe is done. The bar is indeterminate because
the Adobe SDK provides no percentage feedback. **Closing the window cancels
the conversion.** If Adobe does not answer within **4 minutes**, the tool
gives up on its own instead of waiting indefinitely. A system notification
fires on success; failures are shown in a dialog with the reason.

Brief network drops while waiting for Adobe are retried automatically
(up to 2 retries).

## Checks before upload

Before anything is sent to Adobe, each PDF is checked locally. No Adobe
transactions are used for files that fail these checks.

| Check | Result |
|---|---|
| File larger than 100 MB (Adobe's documented limit) | Rejected |
| Not actually a PDF (only the name ends in `.pdf`) | Rejected |
| Damaged, cannot be read | Rejected |
| Needs a password to open | Rejected — remove the password first |
| Encrypted, but opens without a password (permissions restricted only) | Warning — Adobe may reject it |
| More than 100 pages | Warning — Adobe's OCR is known to fail beyond about 100 pages |
| Already contains text (digital PDF, or the scanner added its own OCR layer) | Warning — Adobe's OCR has been seen to hang on such files until it times out |

For warnings you can choose to continue anyway. With **Merge & OCR** every
input file is checked, and the merged file is checked again for size and
page count.

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
