# DeepFind — local encrypted document search for Windows

> Turkish: [README.tr.md](./README.tr.md)

**Describe the document you remember, not the filename you saved it under.**

DeepFind indexes the documents already sitting in your folders — PDF, XLSX/XLS, DOCX, ODT, RTF, TXT/CSV and scanned JPG/PNG/TIFF — and finds them by meaning. The files never move. The index lives in a SQLCipher-encrypted vault on your machine, and nothing about your documents is sent anywhere.

![DeepFind · Search](./docs/screenshots/01-ara.png)

---

## Contents

- [What it does](#what-it-does)
- [Screens, one by one](#screens-one-by-one)
  - [1. First setup](#1-first-setup)
  - [2. Search](#2-search)
  - [3. Sources](#3-sources)
  - [4. Scan](#4-scan)
  - [5. History](#5-history)
  - [6. Scanned documents](#6-scanned-documents)
  - [7. Settings](#7-settings)
- [Install](#install)
- [How semantic search works](#how-semantic-search-works)
- [Vault and security](#vault-and-security)
- [OCR and preview](#ocr-and-preview)
- [Build from source](#build-from-source)
- [Limits worth knowing](#limits-worth-knowing)
- [License](#license)

---

## What it does

| Capability | Detail |
|---|---|
| **Semantic search** | EmbeddingGemma 2 Q8_0, 256-dimensional L2-normalised vectors — search by describing the content |
| **Broad format support** | PDF, XLSX/XLS, DOCX, ODT, RTF, TXT/CSV, JPG/PNG/TIFF |
| **OCR** | RapidOCR with bundled PP-OCR models and ONNX Runtime for scanned PDFs and images |
| **Encrypted vault** | SQLCipher database plus a password and a recovery key |
| **Local models** | text model, Vulkan/CPU engines and OCR ship with the installer — no internet, API key, Ollama or Python needed |
| **Optional GPU** | CUDA component downloaded on demand (~663 MB, pinned version and SHA-256); Vulkan and CPU are in the main package |
| **Source management** | add folders, exclude paths, live-watch for changes |
| **Preview** | PDF preview and thumbnails inside the app |
| **Filters** | folder, type, year and tags on top of semantic ranking |
| **Self-update** | daily check, SHA-256 verified, same install upgraded in place |

---

## Screens, one by one

### 1. First setup

![First setup](./docs/screenshots/00-ilk-kurulum.png)

Five steps, and the last one shows exactly what will happen.

1. **Welcome** — what the app does, in one screen.
2. **Vault password** — choose the password that encrypts the index. It can be remembered for the Windows user through DPAPI.
3. **Folders** — pick the folders to index, either from the tree or by typing a path. Nothing is moved or changed; the folder stays where it is.
4. **Layout** — decide how the folder context is read for each root, previewed before anything is saved.
5. **Final check** — a summary of the root count, the theme and whether a password was set, plus the note that documents are neither moved nor modified and that you can keep using the app while the first scan runs.

`Finish setup` starts the first scan. A large archive takes a while; the app stays usable throughout.

### 2. Search

![Search](./docs/screenshots/01-ara.png)

One box and a description of what you are looking for.

- **Search field** — describe the content: "house rental agreement" finds a document that only says "rental contract" inside. Quotes, `OR`/`AND` and the minus sign are **not** word-search operators; they are part of your description.
- **Filters on the left** — year, type, company or folder, tag. Applied on top of the semantic ranking, not instead of it.
- **Saved searches** — store a filter combination and return to it.
- **Tags** — tag the selected result, or remove a tag.
- **Results** — list, table or grid view, with `Export CSV` for export.
- **Preview panel** — the selected document's preview and its path, with `Copy path`.

Every result shows the most relevant section and page, so you land on the paragraph that matched instead of scrolling a 300-page PDF.

### 3. Sources

![Sources](./docs/screenshots/02-kaynaklar.png)

The folders that get indexed.

- `Add folder` adds a root; each root has its own card.
- Per root you see the name, the full path, whether search is enabled for it, and its exclusion list.
- `Remove` removes a root from the index — **the documents are not deleted**, only the index entries.
- Exclusions keep whole subtrees out of the index.

Changing sources does not require a rebuild: the next scan picks up the difference.

### 4. Scan

![Scan](./docs/screenshots/03-tarama.png)

What is being indexed and how far along it is.

- **Scope** — how many source folders are in play, with a pointer back to Sources.
- **Daily schedule** — the planned scan time (`12:30` in the capture).
- **Status** — `Ready`, `Scanning`, `Paused` and the reason for a failure.
- **Controls** — `Start scan`, `Pause`, `Cancel`, `Open scan details`.
- **Recent scans** — per run: time, root, result, how many documents were processed, found, still pending and failed.

Counting happens before percentage: the app walks the source completely, then reports progress against that total. If a folder is unreachable, the inventory is marked incomplete instead of pretending the scan covered everything. Stages that cannot be measured — verification, column removal, disk records — show elapsed time and a state, never a fabricated percentage.

### 5. History

![History](./docs/screenshots/04-gecmis.png)

Previous searches, one click away. The tab shows the count and an explicit empty state when nothing has been searched yet.

### 6. Scanned documents

![Scanned documents](./docs/screenshots/05-taranmis-evraklar.png)

Every indexed document with its path, state and source health.

| Column | Meaning |
|---|---|
| **Document** | filename with thumbnail |
| **Path** | full path as indexed |
| **State** | `Done` or `Partial` with the reason (for example `OCR_LOW_QUALITY`) |
| **Source** | whether the source was reachable (`ok`) |

Filters by state, page size, `Refresh`, `Coverage`, and previous/next navigation. A document that only partially indexed says so instead of silently looking complete.

### 7. Settings

![Settings](./docs/screenshots/06-ayarlar.png)

Four groups.

**Work**
- OCR components: Turkish text recognition state, with `Verify / repair`.
- Daily scan time.
- Reduce network load (throttle).
- Start with Windows.
- Live-watch changed folders.
- Minimise to tray on close.

**Consumption**
- Incoming folder — documents dropped there are picked up and can be filed automatically.
- Archive target — where processed documents are moved.
- Tag rules — tag and keyword pairs applied during filing.

**Vault security**
- Auto-lock after inactivity (15 minutes in the capture).
- `Change password`, `Remove remembered sign-in`.
- Recovery key: `Refresh key`, `Show key`, `Print / save`, `Remove`.

**Backups**
- `Create backup`, `Restore`, and the list of existing backups.

---

## Install

1. Download `DeepFind-<version>.exe` from [Releases](https://github.com/zeitgeist-c/DeepFind/releases/latest).
2. Run it. The installer carries the text model, the Vulkan/CPU engines and the OCR components, so search works offline immediately.
3. Choose a vault password and at least one folder on first launch.

A ZIP is published for older clients. The `_internal` and `licenses` folders must stay next to the EXE — the EXE alone will not run. Updating from a ZIP installation switches to the full installer.

Updates run from *Settings → Updates*: a daily silent check, SHA-256 verified download, install over the same directory through a fixed AppId, shortcuts and uninstaller preserved. A failed install offers a path back to the previous program; the live vault is never modified by the installer.

## How semantic search works

There is exactly one search path: semantic search. The text model produces a 256-dimensional L2-normalised vector for each section of each document; a query is embedded the same way and results are ranked by cosine similarity.

- Badly named files are findable by describing their content.
- Each result shows the best-matching section and page.
- Folder, type, year and tag filters narrow the ranking without replacing it.
- Similarity is not a guarantee of relevance — the top result can be wrong.

The model runs in a single shared local subprocess. Communication is over `127.0.0.1` only, with a temporary access key; document content is never sent to an external service. Long texts are split with overlap at token boundaries. The model process is closed on lock or exit, and Windows process ownership closes it after a crash too.

Old ONNX vectors are never mixed with the new model's vectors. Gaps from an older vault are filled during the next scan. If the model is not ready, the app says so plainly — there is no silent fallback to word search.

## Vault and security

| What | Where |
|---|---|
| Vault | `%LOCALAPPDATA%\DeepFind\Data\deepfind.db` |
| Backups | `%LOCALAPPDATA%\DeepFind\Backups` |
| Remembered login | `%LOCALAPPDATA%\DeepFind\Credentials` (DPAPI, per Windows user) |

- The database is encrypted with SQLCipher; the password is not stored anywhere.
- Backups do not include the source documents.
- Old backups require the password they were taken with.
- Keep the recovery key somewhere separate and safe. Without both the password and the key, the vault will not open — that is not a limitation to be worked around, it is the design.
- Do not open the same vault on two computers at the same time.
- Session lock or sleep closes connections and clears the model, preprocessing and history.

## OCR and preview

RapidOCR, bundled PP-OCR models and ONNX Runtime extract text from scanned PDFs and images. The embedding model does not replace OCR. PDF pages that already carry a good text layer are not OCR'd again. Images embedded inside Word or Excel files are outside OCR scope; legacy DOC content needs LibreOffice.

## Build from source

Requires Python 3.12+.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe eval/semantic_acceptance.py
.\.venv\Scripts\python.exe packaging/build.py
.\.venv\Scripts\python.exe eval/package_check.py
```

`packaging/fetch_engine.py` downloads the official model and engine versions into the project's `build/embedding` area and verifies their digests. BF16 is for developer comparison only; Q8_0 ships.

The version has a single source: `src/deepfind/version.py`. Patch releases go `0.10.1 → 0.10.2 → 0.10.3`.

Do not pass a real vault password on the command line.

## Limits worth knowing

- Real NAS, a clean Windows install, a very large archive and different GPU/DPI environments still need their own acceptance; try a small permitted or synthetic folder first.
- DOC content requires LibreOffice; embedded images inside Office files are not OCR'd.
- Semantic similarity is not exact matching — a query can return a plausible but wrong document.
- `Partial` state on a document means the index is incomplete for it, usually low-quality OCR of a scan.

## License

MIT — see [LICENSE](./LICENSE).
