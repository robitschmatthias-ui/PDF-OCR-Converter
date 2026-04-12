# PDF-OCR-Converter

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

```powershell
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git $env:LOCALAPPDATA\pdf-ocr-converter
cd $env:LOCALAPPDATA\pdf-ocr-converter
install\windows\install.ps1
```

## Usage

Three context-menu entries appear on PDF files:

| Entry | Behavior |
|---|---|
| **OCR to DOCX** | Single file or multi-select (each processed separately) |
| **Merge & OCR to DOCX** | Multi-select only (Linux); merges first, then OCR |
| **OCR Settings** | Re-enter / change Adobe credentials |

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
