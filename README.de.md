# PDF-OCR-Converter

![platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-blue)
![language](https://img.shields.io/badge/language-Python%203.10%2B-yellow)
![file-manager](https://img.shields.io/badge/file--manager-Nemo%20%7C%20Explorer-orange)
![OCR](https://img.shields.io/badge/OCR-Adobe%20PDF%20Services-red)
![license](https://img.shields.io/badge/license-GPL%20v3-blue)
![Stars](https://img.shields.io/github/stars/robitschmatthias-ui/PDF-OCR-Converter?style=social)

> 🇬🇧 **English version:** see [README.md](README.md)

Ein plattformübergreifendes Tool, das PDF-Dateien per **Adobe PDF Services
API** (OCR) in bearbeitbare DOCX-Dateien umwandelt – ausgelöst per
Rechtsklick im Dateimanager unter Linux (Nemo) und Windows (Explorer).

## Funktionen

- **Rechtsklick-Integration** unter Linux (Nemo) und Windows (Explorer)
- **OCR to DOCX** – einzelne PDF oder mehrere PDFs (einzeln verarbeitet)
- **Merge & OCR to DOCX** (nur Linux, Mehrfachauswahl) – fügt mehrere PDFs
  mit dem Quick Merge aus [Linux-PDF-Merge-in-Nemo](https://github.com/robitschmatthias-ui/Linux-PDF-Merge-in-Nemo)
  zusammen und schickt die zusammengeführte Datei zur Adobe OCR
- **Sprachauswahl-Dialog** – OCR-Sprache wählbar (tkinter)
- **Desktop-Benachrichtigungen** via `plyer`
- **Sichere Credential-Verwaltung** – Zugangsdaten werden außerhalb des
  Repos in `~/.config/pdf-ocr-converter/.env` gespeichert (nicht in git)

## Namensschema für die Ausgabedatei

Von Adobe zurückkommende Dateien erhalten immer das Suffix `_OCR`, z.B.
`rechnung.pdf` → `rechnung_OCR.docx`. Beim Zusammenführen mehrerer Dateien
übernimmt das Ergebnis den Namen der **ersten** Datei in der Auswahl.

## Voraussetzungen

- Python 3.10+
- Adobe Developer Console Account mit PDF Services API-Zugangsdaten
  (siehe [docs/adobe-credentials.md](docs/adobe-credentials.md))
- **Free-Tier:** 500 Transaktionen/Monat (~250 OCR-Konvertierungen)

## Adobe API-Zugangsdaten besorgen

Du brauchst einen kostenlosen Adobe Developer Account.
**Free-Tier: 500 Transaktionen/Monat** — jede OCR-Konvertierung verbraucht 2 Transaktionen
(OCR + DOCX-Export), damit lassen sich **~250 Dateien pro Monat** kostenlos verarbeiten.

1. Öffne <https://developer.adobe.com/console> und melde dich an (oder registriere dich – kostenlos).
2. Klicke auf **Create new project**.
3. Im Projekt: **Add API** → **PDF Services API** auswählen → **Next**.
4. Als Authentifizierung **OAuth Server-to-Server** wählen → **Save configured API**.
5. Auf der Credentials-Seite kopieren:
   - **Client ID**
   - **Client Secret** (*"Retrieve client secret"* klicken)
6. Beides in den Setup-Dialog eintragen (öffnet sich automatisch bei der ersten
   Installation oder per Rechtsklick → **OCR Settings**).

Die Zugangsdaten werden unter `~/.config/pdf-ocr-converter/.env` (Linux) bzw.
`%APPDATA%\pdf-ocr-converter\.env` (Windows) gespeichert – niemals im Repo.

Ausführliche Anleitung: [docs/adobe-credentials.md](docs/adobe-credentials.md).

## Installation

### Linux (Nemo)

```bash
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git ~/scripts/pdf-ocr-converter
cd ~/scripts/pdf-ocr-converter
bash install/linux/install.sh
```

Beim ersten Aufruf öffnet sich ein Dialog zur Eingabe der Adobe-Zugangsdaten;
diese werden unter `~/.config/pdf-ocr-converter/.env` gespeichert.

### Windows (Explorer)

```powershell
git clone https://github.com/robitschmatthias-ui/PDF-OCR-Converter.git $env:LOCALAPPDATA\pdf-ocr-converter
cd $env:LOCALAPPDATA\pdf-ocr-converter
install\windows\install.bat
```

Der `.bat`-Wrapper umgeht die PowerShell-Execution-Policy automatisch.
Python wird bei Bedarf per `winget` installiert. Falls Python nach einer frischen
Installation nicht erkannt wird: PowerShell schließen, eine neue Session öffnen
und den Installer erneut starten.

## Nutzung

Im Kontextmenü von PDF-Dateien erscheinen drei Einträge:

| Eintrag | Verhalten |
|---|---|
| **OCR to DOCX** | Einzelne Datei oder Mehrfachauswahl (jeweils einzeln verarbeitet) |
| **Merge & OCR to DOCX** | Nur bei Mehrfachauswahl (Linux); zuerst mergen, dann OCR |
| **OCR Settings** | Adobe-Zugangsdaten neu eingeben / ändern |

## Sicherheit

- Zugangsdaten werden **außerhalb** des Projektordners gespeichert (nie commitbar)
- Temporäre Merge-Dateien werden nach der Verarbeitung sicher gelöscht
- Logs enthalten keine Credentials oder sensitiven Pfade
- Geplanter Ausbau: OS-Keychain (GNOME Keyring / Windows Credential Manager)

> **Datenschutzhinweis:** Adobe verarbeitet die Dokumente auf AWS-Servern in
> den USA (US-East) und speichert sie bis zu 24 Stunden. Bei DSGVO-sensiblen
> Dokumenten entsprechend abwägen.

## Lizenz

GPL-3.0 – siehe [LICENSE](LICENSE).

## Credits

Aufbauend auf dem [Adobe PDF Services Python SDK](https://github.com/adobe/pdfservices-python-sdk-samples)
und inspiriert von [Linux-PDF-Merge-in-Nemo](https://github.com/robitschmatthias-ui/Linux-PDF-Merge-in-Nemo).

---

> 🤖 **Vibe-Coding:** Dieses Projekt ist in einer Dialog-Session mit einer KI
> entstanden — Design, Code, Installer und Doku wurden iterativ im Gespräch
> generiert.
