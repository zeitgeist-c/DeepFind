"""Tarama koordinatoru: tek aktif tarama, artimli kuyruk, kismi kapsam, degisen dosya."""
from __future__ import annotations

import os
import time

from . import exclusions as exc
from . import extract as ex
from . import ocr as ocr_mod
from . import queue as q
from . import scan as scan_mod
from .migrate import EXTRACTOR_VERSION

STABLE_NS = 2_000_000_000  # 2 sn icinde degismisse kararli degil
DEFER_SEC = 60


class AlreadyRunning(Exception):
    pass


class ScanLock:
    """Kasa dizininde capraz-surec kilidi (SCN-05: ikinci tarama acilmaz)."""

    def __init__(self, vault_path: str):
        self.path = os.path.join(os.path.dirname(os.path.abspath(vault_path)), "scan.lock")
        self.fh = None

    def __enter__(self):
        import msvcrt
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.fh = open(self.path, "w")
        try:
            msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.fh.close()
            raise AlreadyRunning("baska bir tarama aktif")
        return self

    def __exit__(self, *a):
        import msvcrt
        try:
            msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.fh.close()


def _stat_sig(path: str):
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime_ns
    except OSError:
        return None


def ensure_file(con, entry) -> int:
    con.execute(
        "INSERT INTO files(path, name, ext, size, mtime_ns) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns",
        (entry.path, entry.name, entry.ext, entry.size, entry.mtime_ns),
    )
    con.commit()
    return con.execute("SELECT file_id FROM files WHERE path=?", (entry.path,)).fetchone()[0]


def active_signature(con, file_id: int) -> str | None:
    r = con.execute(
        "SELECT signature FROM file_revisions WHERE file_id=? AND active=1 AND extractor=?", (file_id, EXTRACTOR_VERSION)
    ).fetchone()
    return r[0] if r else None


def write_revision(con, file_id: int, sig: str, res: "ex.ExtractResult",
                     context: str = "") -> None:
    """Dosya + revizyon + segment + FTS tek transaction (DB-01: yarim FTS yok)."""
    import unicodedata
    from . import normalize as nz
    cur = con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("UPDATE file_revisions SET active=0 WHERE file_id=?", (file_id,))
        con.execute(
            "INSERT INTO file_revisions(file_id, signature, extractor, created_at, active)"
            " VALUES (?, ?, ?, ?, 1)",
            (file_id, sig, EXTRACTOR_VERSION, int(time.time())),
        )
        rev_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("DELETE FROM segments WHERE file_id=?", (file_id,))

        def _row(kind, page, label, raw):
            raw = unicodedata.normalize("NFC", raw or "")
            return (file_id, rev_id, kind, page, label, raw, nz.folded(raw))

        to_write = []
        if res.segments:
            to_write = [_row(s.kind, s.page, s.label, s.raw_text) for s in res.segments]
        else:
            row = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()
            to_write = [_row("name_only", None, row[0], row[0])]
        if context.strip():
            cx = unicodedata.normalize("NFC", context.strip())
            to_write.append((file_id, rev_id, "context", None, "Konum", cx, nz.folded(cx)))
        name = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()[0]
        if res.segments:
            to_write.append(_row("name_only", None, "Dosya adı", name))
        con.executemany(
            "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text, folded_text)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            to_write,
        )
        con.execute("DELETE FROM file_years WHERE file_id=?", (file_id,))
        name = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()[0]
        for y in nz.extract_years(name, context, *[s.raw_text for s in (res.segments or [])]):
            con.execute(
                "INSERT INTO file_years(file_id, year, source, evidence) VALUES (?,?,?,?)"
                " ON CONFLICT(file_id, year) DO NOTHING",
                (file_id, y, "name", name),
            )
        con.execute(
            "UPDATE files SET index_status=?, error_code=? WHERE file_id=?",
            (res.status, res.error_code, file_id),
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def _context_for(path: str, root: str) -> str:
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        rel = os.path.basename(path)
    parts = [p for p in os.path.dirname(rel).split(os.sep) if p and p != "."]
    return " / ".join(parts[-2:])


def _process_job(con, job: dict, rules: list, vault_dir: str, root: str, stop=None, guarded=False) -> str:
    fid, sig = job["file_id"], job["signature"]
    row = con.execute("SELECT path, ext FROM files WHERE file_id=?", (fid,)).fetchone()
    if not row:
        q.complete(con, job["job_id"])
        return "gone"
    path, ext = row
    if exc.is_excluded(path, rules):
        con.execute("DELETE FROM segments WHERE file_id=?", (fid,))
        con.execute("DELETE FROM jobs WHERE file_id=?", (fid,))
        con.commit()
        return "excluded"
    st = _stat_sig(path)
    if st is None:
        q.fail(con, job["job_id"], "SOURCE_OFFLINE")
        return "offline"
    size, mtime = st
    if time.time_ns() - mtime < STABLE_NS:
        con.execute(
            "UPDATE jobs SET not_before=?, error_code='FILE_UNSTABLE' WHERE job_id=?",
            (q.now() + DEFER_SEC, job["job_id"]),
        )
        con.commit()
        return "unstable"
    cur_sig = q.signature_of(size, mtime)
    if guarded:
        from .workers import run_work
        res = run_work("extract", (path, ext, size), stop=stop)
    else:
        res = ex.extract(path, ext, size)
    st2 = _stat_sig(path)
    if st2 is None or st2 != (size, mtime):
        # SCN-03: okuma sirasinda degisti -> karisik cikti aktif yapilmaz
        nsig = q.signature_of(*st2) if st2 else cur_sig
        con.execute("UPDATE files SET size=?, mtime_ns=? WHERE file_id=?",
                    (st2[0] if st2 else size, st2[1] if st2 else mtime, fid))
        q.enqueue(con, fid, nsig)
        con.commit()
        q.complete(con, job["job_id"])
        return "changed"
    if res.status == "corrupt" and res.error_code == "CORRUPT_DOCUMENT":
        pass  # asagida fail/retry politikasi
    write_revision(con, fid, cur_sig, res, _context_for(path, root))
    # Ince metinli PDF sayfalari -> agir OCR fazi (ayri is; ayni kaynagi paralel okumaz)
    if ext == ".pdf" and res.status in ("ok", "partial"):
        thin = [s.page for s in (res.segments or [])
                if s.kind == "pdf_page" and ocr_mod.needs_ocr(s.raw_text)]
        if thin:
            q.enqueue(con, fid, cur_sig, kind="ocr")
            con.commit()
    q.complete(con, job["job_id"])
    return "done"


def _process_ocr_job(con, job: dict, vault_dir: str, stop=None, guarded=False) -> str:
    """Agir OCR fazi: ince sayfalari oku, ayni revizyona ocr_page segmentleri ekle."""
    from . import normalize as nz
    fid, sig = job["file_id"], job["signature"]
    if active_signature(con, fid) != sig:
        q.complete(con, job["job_id"])  # eski surum; yeni extract isi gecerli
        return "stale"
    row = con.execute("SELECT path FROM files WHERE file_id=?", (fid,)).fetchone()
    if not row:
        q.complete(con, job["job_id"])
        return "gone"
    path = row[0]
    rev = con.execute("SELECT rev_id FROM file_revisions WHERE file_id=? AND active=1",
                      (fid,)).fetchone()
    if not rev:
        q.complete(con, job["job_id"])
        return "gone"
    rev_id = rev[0]
    thin = [(r[0], r[1]) for r in con.execute(
        "SELECT page, raw_text FROM segments WHERE file_id=? AND kind='pdf_page'",
        (fid,)).fetchall() if ocr_mod.needs_ocr(r[1])]
    if not thin:
        q.complete(con, job["job_id"])
        return "noop"
    if not ocr_mod.ram_allows():
        con.execute("UPDATE jobs SET not_before=?, error_code='MEMORY_LIMIT' WHERE job_id=?",
                    (q.now() + DEFER_SEC, job["job_id"]))
        con.commit()
        return "deferred"
    pages_0 = [p - 1 for p, _t in thin if p]
    from . import migrate
    try:
        language = migrate.get_setting(con, "ocr_dili", "tur")
    except Exception:  # eski şema: OCR varsayılan Türkçe kalır
        language = "tur"
    if language not in ("tur", "eng"):
        language = "tur"
    if guarded:
        from .workers import run_work
        results, _wd = run_work("ocr", (path, pages_0, vault_dir, language),
                               timeout=min(1800, max(60, len(pages_0) * 180)), stop=stop)
    else:
        results, _wd = ocr_mod.ocr_document(path, pages_0, vault_dir, language)
    st = _stat_sig(path)
    if st is None or q.signature_of(*st) != sig:
        q.complete(con, job["job_id"])
        return "stale"
    if results and any(r.method in ("deferred", "unavailable") for r in results):
        con.execute("UPDATE jobs SET status='pending',not_before=?,error_code=? WHERE job_id=?",
                    (q.now() + DEFER_SEC, results[0].error_code or "MODEL_MISSING", job["job_id"]))
        con.execute("UPDATE files SET index_status='partial',error_code=? WHERE file_id=?",
                    (results[0].error_code or "MODEL_MISSING", fid))
        con.commit()
        return "deferred"
    cur = con.execute("BEGIN IMMEDIATE")
    try:
        for r in results:
            if r.method in ("deferred", "unavailable"):
                continue  # klasik metin aramasi surer; dosya basarisiz sayilmaz
            if r.method == "timeout":
                raise TimeoutError("PROCESS_TIMEOUT")
            if r.words == 0 or not r.text.strip():
                continue
            raw = r.text.strip()
            con.execute(
                "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text,"
                " folded_text, method, confidence) VALUES (?,?,?,?,?,?,?,?,?)",
                (fid, rev_id, "ocr_page", r.page, f"Sayfa {r.page} (OCR)",
                 raw, nz.folded(raw), r.method, round(r.mean_conf, 1)),
            )
        con.execute("COMMIT")
    except TimeoutError:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return q.fail(con, job["job_id"], "PROCESS_TIMEOUT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return q.fail(con, job["job_id"], "CORRUPT_DOCUMENT")
    # Tum sayfalar timeout/unavailable ise retry; aksi halde tamamla
    if results and all(r.method in ("timeout",) for r in results):
        return q.fail(con, job["job_id"], "PROCESS_TIMEOUT")
    q.complete(con, job["job_id"])
    return "done"


def run_scan(con, vault_path: str, root: str, stop=None, guarded=False, progress=None) -> dict:
    """Tam tarama: kesif + kuyruk isleme. stop(): duraklat/iptal bayragi."""
    stats = {"found": 0, "done": 0, "changed": 0, "unstable": 0, "failed": 0,
             "missing": 0, "ocr_done": 0, "ocr_deferred": 0, "ocr_failed": 0,
             "hashed": 0, "skipped": 0, "complete": False, "result": "partial"}
    with ScanLock(vault_path):
        con.execute("CREATE TEMP TABLE IF NOT EXISTS scan_selected(file_id INTEGER PRIMARY KEY)")
        con.execute("DELETE FROM scan_selected")
        q.recover_running(con)
        rules = exc.list_rules(con)
        run_id = con.execute(
            "INSERT INTO scan_runs(root, started_at) VALUES (?, ?)", (root, int(time.time()))
        ).lastrowid
        con.commit()
        all_complete = True
        seen = set()
        last_report = 0.0

        def report(stage, path="", result="", force=False):
            nonlocal last_report
            now = time.monotonic()
            if progress and (force or now - last_report >= 0.2):
                pending = con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running')"
                                      " AND file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
                progress(dict(stats, stage=stage, path=path, item_result=result, pending=pending))
                last_report = now

        def process_batch(limit=None):
            count = 0
            while limit is None or count < limit:
                if stop and stop():
                    stats["result"] = "cancelled"
                    return
                job = q.claim(con, scoped=True)
                if not job:
                    return
                path = con.execute("SELECT path FROM files WHERE file_id=?", (job["file_id"],)).fetchone()[0]
                report("İçerik okunuyor", path, force=True)
                try:
                    r = _process_job(con, job, rules, os.path.dirname(vault_path), os.path.abspath(root), stop, guarded)
                except InterruptedError:
                    con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?", (job["job_id"],))
                    con.commit()
                    stats["result"] = "cancelled"
                    return
                except TimeoutError:
                    r = q.fail(con, job["job_id"], "PROCESS_TIMEOUT")
                except Exception:
                    r = q.fail(con, job["job_id"], "CORRUPT_DOCUMENT")
                for key, outcome in (("done", "done"), ("changed", "changed"), ("unstable", "unstable")):
                    stats[key] += int(r == outcome)
                stats["failed"] += int(r in ("retry", "dead"))
                count += 1
                if r in ("retry", "dead"):
                    error = con.execute("SELECT error_code FROM jobs WHERE job_id=?", (job["job_id"],)).fetchone()
                    code = error[0] if error else ""
                    message = {"PROCESS_TIMEOUT": "Dosya işlemi zaman aşımına uğradı", "CORRUPT_DOCUMENT": "Dosya okunamadı"}.get(code, "Dosya işlenemedi")
                    report(message, path, r, force=True)
                else:
                    report("İçerik işleniyor", path, r)

        # --- kesif (lazy, dizin bazinda kapsam) ---
        stack = [os.path.abspath(root)]
        while stack:
            if stop and stop():
                break
            cur = stack.pop()
            report("Klasörler keşfediliyor", cur)
            dir_ok = True
            try:
                with os.scandir(cur) as it:
                    entries = list(it)
            except OSError:
                entries = []
                dir_ok = False
                stats["failed"] += 1
                report("Klasöre erişilemiyor", cur, "erişim hatası", force=True)
            con.execute("INSERT OR IGNORE INTO scan_scopes(run_id, dir, complete) VALUES (?,?,?)",
                        (run_id, cur, 0))
            for e in entries:
                if stop and stop():
                    dir_ok = False
                    break
                try:
                    if exc.is_excluded(e.path, rules):
                        stats["skipped"] += 1
                        continue
                    if e.stat(follow_symlinks=False).st_file_attributes & 0x400:
                        continue  # Windows junction/reparse point izlenmez.
                    if e.is_dir(follow_symlinks=False):
                        if e.name in scan_mod.SKIP_DIRS or e.name.startswith("~$"):
                            continue
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        if e.name.startswith("~$"):
                            continue
                        st = e.stat(follow_symlinks=False)
                        ext = os.path.splitext(e.name)[1].lower()
                        if ext not in scan_mod.SUPPORTED_EXTS and ext not in scan_mod.NAME_ONLY_EXTS:
                            continue
                        entry = scan_mod.Entry(e.path, e.name, ext, st.st_size, st.st_mtime_ns)
                        if exc.is_excluded(entry.path, rules):
                            continue
                        seen.add(entry.path)
                        fid = ensure_file(con, entry)
                        con.execute("INSERT OR IGNORE INTO scan_selected VALUES (?)", (fid,))
                        sig = q.signature_of(entry.size, entry.mtime_ns)
                        status = con.execute("SELECT index_status FROM files WHERE file_id=?", (fid,)).fetchone()[0]
                        if active_signature(con, fid) != sig or status in ("missing", "excluded"):
                            con.execute("UPDATE files SET index_status='pending' WHERE file_id=?", (fid,))
                            q.enqueue(con, fid, sig)
                        else:
                            stats["skipped"] += 1
                        stats["found"] += 1
                        if stats["found"] % 32 == 0:
                            con.commit()
                            process_batch(8)
                        report("Klasörler keşfediliyor", cur)
                except OSError:
                    dir_ok = False
                    continue
            if dir_ok:
                con.execute("UPDATE scan_scopes SET complete=1 WHERE run_id=? AND dir=?", (run_id, cur))
            else:
                all_complete = False
            con.commit()
            process_batch(8)
        # --- kuyruk isleme ---
        process_batch()
        # --- agir OCR fazi (cikarma bitince; kaynagi paralel okumaz, UI/aramayi bekletmez) ---
        while True:
            if stop and stop():
                stats["result"] = "cancelled"
                break
            job = q.claim(con, ("ocr",), scoped=True)
            if not job:
                break
            path = con.execute("SELECT path FROM files WHERE file_id=?", (job["file_id"],)).fetchone()[0]
            report("OCR ile metin okunuyor", path, force=True)
            try:
                r = _process_ocr_job(con, job, os.path.dirname(vault_path), stop, guarded)
            except InterruptedError:
                con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?", (job["job_id"],))
                con.commit()
                stats["result"] = "cancelled"
                break
            except TimeoutError:
                r = q.fail(con, job["job_id"], "PROCESS_TIMEOUT")
            except Exception:
                r = q.fail(con, job["job_id"], "CORRUPT_DOCUMENT")
            stats["ocr_done"] += 1 if r == "done" else 0
            stats["ocr_deferred"] += 1 if r == "deferred" else 0
            if r in ("retry", "dead"):
                stats["ocr_failed"] += 1
            report("OCR işleniyor", path, r)
        # --- kopya hash (arka plan; sinirli; kaynagi bir kez daha okur) ---
        try:
            from . import dup as dup_mod
            if not (stop and stop()):
                report("Kopyalar doğrulanıyor", root, force=True)
                stats["hashed"] = dup_mod.verify_pending(con, scoped=True, stop=stop).get("verified", 0)
        except Exception:
            pass
        # --- kayip dosya: yalniz tam kapsamda ---
        if all_complete and not (stop and stop()):
            rows = con.execute("SELECT file_id, path FROM files").fetchall()
            for fid, p in rows:
                # Bir kökün taraması diğer köklerin indeksini silemez.
                try:
                    if os.path.commonpath([os.path.abspath(p), os.path.abspath(root)]) != os.path.abspath(root):
                        continue
                except ValueError:
                    continue
                if p not in seen and not exc.is_excluded(p, rules):
                    con.execute("DELETE FROM segments WHERE file_id=?", (fid,))
                    con.execute("UPDATE files SET index_status='missing' WHERE file_id=?", (fid,))
                    stats["missing"] += 1
            con.commit()
            pending = con.execute("SELECT count(*) FROM jobs WHERE file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
            stats["complete"] = not pending and not stats["failed"] and not stats["ocr_failed"]
            stats["result"] = "complete" if stats["complete"] else "partial"
        stats["pending"] = con.execute("SELECT count(*) FROM jobs WHERE file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
        report("Tarama tamamlandı" if stats["complete"] else "Tarama durdu", root, force=True)
        con.execute("UPDATE scan_runs SET finished_at=?, result=? WHERE run_id=?",
                    (int(time.time()), stats["result"], run_id))
        con.commit()
    return stats
