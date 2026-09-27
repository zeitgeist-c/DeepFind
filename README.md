# Evrakçı (V1)

Yerel şifreli belge bulma aracı (Windows x64, Türkçe, çevrimdışı).
Kaynak belgeler salt-okunur taranır; metin+konum şifreli kasada (SQLCipher + FTS5) saklanır.

## Çalıştırma

Önkoşul: Python 3.13 + Tesseract-OCR (`tur` dili).

```bat
.venv\Scripts\python -m evrakci --kasa "%LOCALAPPDATA%\Evrakci\Data\evrakci.db"
```

CLI: `python -m evrakci --kasa ... --sifre ... {init,tara,ara,haric-tut,yedek-al,yedek-liste,geri-yukle,parola-degistir,tani}`

## Test / Eval

```bat
set EVRAKCI_TESSDATA=<tessdata-dizini>
.venv\Scripts\python -m pytest tests/ -q
.venv\Scripts\python eval/run_eval.py
```

## Paket

PyInstaller onedir → `dist/Evrakci-0.1.0/` → `Evrakçı-0.1.0.zip`.
Önkoşul: Tesseract-OCR + `tur` traineddata (paket dışı).

## Düzen

`src/evrakci/`: vault/schema/migrate/scan/extract/index/search/rank/normalize/vocab/snippet/history/dup/ocr/queue/exclusions/doc_adapter/coordinator/backup/sched/theme/wizard/preview/app/cli.
`tests/`: vertical/durability/search/ocr/backup/sched/ui. `eval/`: corpus/run_eval/lang_compare/ocr_report/ui_shots/license_manifest.

Kararlar: `DURUM.md`. Plan: `Evrakçı-Plan-V4.md` (talimat değil, referans).
Sürüm: `src/evrakci/version.py` (tek kaynak, 0.1.0).
