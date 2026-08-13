# Adobe PDF Services API — Credentials Setup Guide

This tool uses the **Adobe PDF Services API** for OCR and DOCX export.
You need a free Adobe Developer account and a set of API credentials
(Client ID + Client Secret).

## 1. Create an Adobe Developer account

Sign up (free) at: <https://developer.adobe.com/document-services/apis/pdf-services/>

## 2. Create a project and credentials

1. Go to the **Adobe Developer Console**: <https://developer.adobe.com/console>
2. Click **Create new project**.
3. In the project, click **Add API** → choose **PDF Services API** → **Next**.
4. Select **OAuth Server-to-Server** as the authentication type → **Save configured API**.
5. Open the credentials page — you will see:
   - **Client ID**
   - **Client Secret** (click "Retrieve client secret")

## 3. Enter credentials into PDF-OCR-Converter

### Option A — GUI (recommended)
Right-click any PDF in your file manager and choose **OCR Settings**,
or run:

```bash
# Linux Mint
~/scripts/pdf-ocr-converter/install/linux/setup_credentials.sh
```

```bash
# Fedora
bash install/fedora/setup_credentials.sh
```

```powershell
# Windows
& "$env:LOCALAPPDATA\pdf-ocr-converter\.venv\Scripts\python.exe" `
  "$env:LOCALAPPDATA\pdf-ocr-converter\src\setup_credentials.py"
```

### Option B — CLI
```bash
python src/setup_credentials.py --cli
```

On Fedora, if you installed via `install/fedora/install.sh`, use the venv
Python instead: `./.venv/bin/python src/setup_credentials.py --cli`
(run from `~/.local/share/pdf-ocr-converter`).

Your credentials are written to:
- Linux / Fedora: `~/.config/pdf-ocr-converter/.env`
- Windows: `%APPDATA%\pdf-ocr-converter\.env`

These files are **outside the project repo** and cannot be accidentally
committed to git.

## 4. Free Tier limits

- **500 transactions/month**
- Each OCR + DOCX export uses **2 transactions** → ~250 conversions/month
- Merging multiple PDFs into one before OCR saves transactions
- Beyond the free tier, Adobe only offers enterprise pricing (~$25k/year)

## 5. Supported OCR locales

```
de-de, de-ch, en-us, en-gb,
fr-fr, it-it, es-es, nl-nl, pt-br,
da-dk, fi-fi, nb-no, sv-se,
cs-cz, pl-pl, hu-hu, ro-ro, sk-sk, sl-si, hr-hr,
bg-bg, el-gr, et-ee, lt-lt, lv-lv, mk-mk, mt-mt,
ru-ru, tr-tr, uk-ua,
ja-jp, ko-kr, zh-cn, zh-hk,
iw-il
```

The default locale is set in the setup dialog and can be overridden per
conversion via the language picker that appears when you trigger OCR. If a
locale is not recognized by the installed SDK, the tool falls back to
`en-us`.

## 6. Privacy note

Adobe temporarily stores uploaded documents on AWS (US-East, Virginia)
for up to 24 hours during processing. This falls under Adobe's terms of
service and is outside the control of this tool. For GDPR-sensitive
documents, consider a local OCR alternative such as
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF).

## 7. Troubleshooting (Fedora)

- **"Adobe rejected the credentials"** — double-check the Client ID/Secret and
  that the credential type is *OAuth Server-to-Server*.
- **Nothing happens on right-click** — make sure `nautilus-python` is
  installed (`rpm -q nautilus-python`) and log out/in once so GNOME loads the
  extension.
- **Logs** — errors are written to `~/.config/pdf-ocr-converter/ocr.log`.
