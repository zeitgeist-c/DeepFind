"""Tarama koordinatoru: tek aktif tarama, artimli kuyruk, kismi kapsam, degisen dosya."""
from __future__ import annotations

import os
import time

from . import exclusions as exc
from . import extract as ex
from . import gom as gom_mod
from . import normalize as nz
from . import ocr as ocr_mod
from . import job_queue as q
from . import scan as scan_mod
from .migrate import EXTRACTOR_VERSION
from . import migrate

STABLE_NS = 2_000_000_000  # 2 sn icinde degismisse kararli degil
DEFER_SEC = 60

KESIF_ASAMALARI = {"Klasörler keşfediliyor", "Kopyalar doğrulanıyor"}


def emit_progress(sink, payload=None, **kw):
    """Ilerleme olayi: kesif mi islem mi oldugunu 'phase' ile ayirir.
    payload tam sayac sozlugu olabilir; eksik cagrida yalniz verilenler gider."""
    data = dict(payload or {})
    data.update(kw)
    stage = data.get("stage", "")
    data["phase"] = "kesif" if stage in KESIF_ASAMALARI else "islem"
    sink(data)


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
            self.fh = None
            raise AlreadyRunning("baska bir tarama aktif")
        return self

    def __exit__(self, *a):
        if self.fh is None:
            return
        import msvcrt
        try:
            msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.fh.close()
            self.fh = None


def _stat_sig(path: str):
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime_ns
    except OSError:
        return None


def ensure_file(con, entry, *, commit=True) -> int:
    con.execute(
        "INSERT INTO files(path, name, ext, size, mtime_ns) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns",
        (entry.path, entry.name, entry.ext, entry.size, entry.mtime_ns),
    )
    if commit:
        con.commit()
    return con.execute("SELECT file_id FROM files WHERE path=?", (entry.path,)).fetchone()[0]


def active_signature(con, file_id: int) -> str | None:
    r = con.execute(
        "SELECT signature FROM file_revisions WHERE file_id=? AND active=1 AND extractor=?", (file_id, EXTRACTOR_VERSION)
    ).fetchone()
    return r[0] if r else None


def note_discovered(con, entry, *, commit=True) -> str:
    """Kesif sonucu: 'queued' | 'skipped'. Idempotent: bitmis imza tekrar kuyruga girmez.
    commit=False ile cagiran toplu commit yapar (kesif dongusu); tekil kullanimda True."""
    fid = ensure_file(con, entry, commit=commit)
    con.execute("CREATE TABLE IF NOT EXISTS scan_selected(file_id INTEGER PRIMARY KEY)")
    con.execute("INSERT OR IGNORE INTO scan_selected VALUES (?)", (fid,))
    sig = q.signature_of(entry.size, entry.mtime_ns)
    status = con.execute("SELECT index_status FROM files WHERE file_id=?", (fid,)).fetchone()[0]
    if active_signature(con, fid) != sig or status in ("missing", "excluded"):
        con.execute("UPDATE files SET index_status=CASE WHEN EXISTS(SELECT 1 FROM segments s WHERE s.file_id=files.file_id) THEN 'partial' ELSE 'pending' END,error_code='REINDEX_PENDING' WHERE file_id=?", (fid,))
        q.enqueue(con, fid, sig)
        if commit:
            con.commit()
        return "queued"
    if commit:
        con.commit()
    return "skipped"


def find_resumable_run(con, root: str):
    """Bitmemis (finished_at NULL) son taramayi dondur; yoksa None.
    Manifest anlik goruntuleri (result='manifest') resume'a konu olmaz."""
    row = con.execute(
        "SELECT run_id FROM scan_runs WHERE root=? AND finished_at IS NULL"
        " AND COALESCE(result, '') <> 'manifest'"
        " ORDER BY run_id DESC LIMIT 1", (root,)).fetchone()
    return row[0] if row else None


def apply_tag_rules(con, file_id: int, name: str, text: str = "") -> set:
    """Kayıtlı kuralları işletir, eklenen etiketleri döner. Elle etiketlere dokunmaz."""
    from . import rank as rank_mod
    from . import normalize as nz
    try:
        rules = rank_mod.tag_rules(con)
    except Exception:
        return set()
    if not rules:
        return set()
    blob = nz.folded((name or "") + "\n" + (text or ""))
    eklenen = set()
    for r in rules:
        keys = [k.strip().lower() for k in nz.folded(r["keywords"]).split(",")]
        keys = [k for k in keys if k]
        if not keys:
            continue
        vurdu = all(k in blob for k in keys) if r["mode"] == "all" else any(k in blob for k in keys)
        if vurdu:
            rank_mod.set_tag(con, file_id, r["tag"], auto=1)
            eklenen.add(r["tag"])
    return eklenen


def completed_dirs(con, run_id: int) -> set:
    """Bu run'da kesfi bitmis klasorler."""
    return {r[0] for r in con.execute(
        "SELECT dir FROM scan_scopes WHERE run_id=? AND complete=1", (run_id,))}


def build_manifest(con, root: str) -> tuple:
    """Taramadan once toplam listeyi cikarir. Donus: (run_id, toplam).
    Anlik goruntu satiridir (result='manifest'); resume'a konu olmaz."""
    absroot = os.path.abspath(root)
    run_id = con.execute(
        "INSERT INTO scan_runs(root, started_at, result) VALUES (?, ?, 'manifest')",
        (absroot, int(time.time()))
    ).lastrowid
    total = 0
    for e in scan_mod.walk_ro(absroot):
        if e.ext not in scan_mod.SUPPORTED_EXTS and e.ext not in scan_mod.NAME_ONLY_EXTS:
            continue
        fid = ensure_file(con, e, commit=False)
        con.execute("INSERT OR IGNORE INTO scan_manifest VALUES (?,?,?,?)",
                    (run_id, fid, e.size, e.mtime_ns))
        total += 1
        if total % 64 == 0:
            con.commit()
    con.execute("UPDATE scan_runs SET finished_at=?, result=? WHERE run_id=?",
                (int(time.time()), "manifest", run_id))
    con.commit()
    return run_id, total


def write_revision(con, file_id: int, sig: str, res: "ex.ExtractResult",
                     context: str = "") -> None:
    """Dosya + revizyon + segment + FTS tek transaction (DB-01: yarim FTS yok)."""
    import unicodedata
    from . import normalize as nz
    if 'start_offset' not in {r[1] for r in con.execute('PRAGMA table_info(segments)')}:
        migrate.ensure_archive(con)
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
            return (file_id, rev_id, kind, page, label, raw)

        if res.segments:
            for segment in res.segments:
                for part, start, end in ex.chunks(segment):
                    con.execute('INSERT INTO segments(file_id,rev_id,kind,page,label,raw_text,start_offset,end_offset) VALUES (?,?,?,?,?,?,?,?)',
                                _row(part.kind,part.page,part.label,part.raw_text)+(start,end))
        to_write = []
        if not res.segments:
            row = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()
            to_write = [_row("name_only", None, row[0], row[0])]
        if context.strip():
            cx = unicodedata.normalize("NFC", context.strip())
            to_write.append((file_id, rev_id, "context", None, "Konum", cx))
        name = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()[0]
        if res.segments:
            to_write.append(_row("name_only", None, "Dosya adı", name))
        con.executemany(
            "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            to_write,
        )
        con.execute("DELETE FROM file_years WHERE file_id=?", (file_id,))
        name = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()[0]
        years=set(nz.extract_years(name, context))
        for segment in res.segments or []:
            years.update(nz.extract_years(segment.raw_text))
        for y in sorted(years):
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
    try:
        name = con.execute("SELECT name FROM files WHERE file_id=?", (file_id,)).fetchone()[0]
        ornek = "\n".join(r[0] for r in con.execute(
            "SELECT substr(raw_text, 1, 2000) FROM segments WHERE file_id=?"
            " AND kind NOT IN ('name_only','context') LIMIT 6", (file_id,)).fetchall())
        apply_tag_rules(con, file_id, name or "", ornek)
    except Exception:
        pass


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
        con.execute("UPDATE files SET source_status='offline',error_code='SOURCE_OFFLINE' WHERE file_id=?",(fid,)); con.commit()
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
    if cur_sig!=sig:
        q.enqueue(con,fid,cur_sig)
        con.execute('DELETE FROM extraction_stage WHERE file_id=? AND signature=?',(fid,sig))
        con.commit(); q.complete(con,job['job_id'])
        return 'changed'
    cursor = con.execute('SELECT cursor FROM jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]
    if guarded:
        from .workers import run_work
        res = run_work("extract_window", (path, ext, size, cursor), stop=stop,timeout=180 if ext=='.doc' else 60)
    else:
        res = ex.extract_window(path, ext, size, cursor)
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
    previous=con.execute('SELECT 1 FROM segments WHERE file_id=? AND kind NOT IN (\'name_only\',\'context\') LIMIT 1',(fid,)).fetchone()
    if res.status not in ('ok','partial') or (res.status=='partial' and not res.segments):
        if not previous:
            write_revision(con,fid,cur_sig,res,_context_for(path,root))
        con.execute('UPDATE files SET index_status=?,error_code=?,coverage=? WHERE file_id=?',
                    ('partial' if previous else res.status,res.error_code,'Önceki indeks korunuyor' if previous else 'İçerik okunamadı',fid))
        con.commit()
        return q.fail(con,job['job_id'],res.error_code or 'EXTRACT_FAILED')
    if cursor==0:
        con.execute('DELETE FROM extraction_stage WHERE file_id=?',(fid,))
    position=con.execute('SELECT coalesce(max(position),-1)+1 FROM extraction_stage WHERE file_id=? AND signature=?',(fid,cur_sig)).fetchone()[0]
    for segment in res.segments:
        con.execute('INSERT INTO extraction_stage VALUES (?,?,?,?,?,?,?,?)',(fid,cur_sig,position,segment.kind,segment.page,segment.label,segment.raw_text,segment.start_offset)); position+=1
    if res.next_cursor is not None:
        con.execute("UPDATE jobs SET cursor=?,status='pending',lease_until=0 WHERE job_id=?",(res.next_cursor,job['job_id']))
        con.execute("UPDATE files SET coverage=? WHERE file_id=?",(f'{res.next_cursor} kaynak bölümü işlendi; devam ediyor',fid))
        con.commit()
        return 'continuing'
    class StagedSegments:
        def __bool__(self): return bool(position)
        def __iter__(self):
            for kind,page,label,raw,start in con.execute('SELECT kind,page,label,raw_text,start_offset FROM extraction_stage WHERE file_id=? AND signature=? ORDER BY position',(fid,cur_sig)):
                yield ex.Segment(kind,page,label,raw,start)
    res.segments=StagedSegments()
    con.commit()
    write_revision(con, fid, cur_sig, res, _context_for(path, root))
    con.execute("UPDATE files SET source_status='ok' WHERE file_id=?",(fid,)); con.commit()
    if gom_mod.model_var_mi():
        q.enqueue(con, fid, cur_sig, kind="embed")
    # Ince metinli PDF sayfalari -> agir OCR fazi (ayri is; ayni kaynagi paralel okumaz)
    if ext in ({'.pdf'} | {'.jpg','.jpeg','.png','.tif','.tiff'}) and res.status in ("ok", "partial"):
        thin = [s.page for s in (res.segments or [])
                if s.kind in ('pdf_page','image_page') and ocr_mod.needs_ocr(s.raw_text)]
        if thin:
            q.enqueue(con, fid, cur_sig, kind="ocr")
            con.execute("UPDATE files SET index_status='partial',error_code='OCR_PENDING' WHERE file_id=?",(fid,))
            con.commit()
    con.execute('DELETE FROM extraction_stage WHERE file_id=?',(fid,))
    con.execute("UPDATE files SET coverage=? WHERE file_id=?",('Metin kaydedildi; OCR durumu ayrıca izlenir',fid))
    q.complete(con, job["job_id"])
    return "done"


def _process_ocr_job(con, job: dict, vault_dir: str, stop=None, guarded=False, session=None) -> str:
    """Agir OCR fazi: ince sayfalari oku, ayni revizyona ocr_page segmentleri ekle.

    session: guarded modda tarama turu boyunca yeniden kullanilan isci (motoru
    bir kez yukler); None ise taze surec acilir."""
    from . import normalize as nz
    fid, sig = job["file_id"], job["signature"]
    if active_signature(con, fid) != sig:
        q.complete(con, job["job_id"])  # eski surum; yeni extract isi gecerli
        return "stale"
    row = con.execute("SELECT path,ext FROM files WHERE file_id=?", (fid,)).fetchone()
    if not row:
        q.complete(con, job["job_id"])
        return "gone"
    path,ext = row
    rev = con.execute("SELECT rev_id FROM file_revisions WHERE file_id=? AND active=1",
                      (fid,)).fetchone()
    if not rev:
        q.complete(con, job["job_id"])
        return "gone"
    rev_id = rev[0]
    thin = [(r[0], r[1]) for r in con.execute(
        "SELECT DISTINCT page, raw_text FROM segments WHERE file_id=? AND kind IN ('pdf_page','image_page') AND page NOT IN (SELECT page FROM ocr_coverage WHERE file_id=? AND rev_id=?)",
        (fid,fid,rev_id)).fetchall() if ocr_mod.needs_ocr(r[1])]
    if not thin:
        q.complete(con, job["job_id"])
        return "noop"
    if not ocr_mod.ram_allows():
        con.execute("UPDATE jobs SET not_before=?, error_code='MEMORY_LIMIT' WHERE job_id=?",
                    (q.now() + DEFER_SEC, job["job_id"]))
        con.commit()
        return "deferred"
    pages_0 = sorted({p - 1 for p, _t in thin if p})[:20]
    if ext != '.pdf':
        if guarded:
            if session is not None:
                results, _wd = session.call('image_ocr', (path, pages_0, vault_dir),
                                            timeout=min(1800, max(180, len(pages_0) * 90)), stop=stop)
            else:
                from .workers import run_work
                results, _wd = run_work('image_ocr', (path, pages_0, vault_dir),
                                        timeout=min(1800, max(180, len(pages_0) * 90)), stop=stop)
        else:
            from .image_ocr import ocr_images
            results, _wd = ocr_images(path, pages_0, vault_dir)
    elif guarded:
        # Sayfa render+OCR ~1-3 sn; butce sayfa basi 60 sn, tavan 30 dk.
        # Motor yuklenmesi oturumda bir kez odenir (session) ya da run_work'te.
        if session is not None:
            results, _wd = session.call("ocr", (path, pages_0, vault_dir),
                                        timeout=min(1800, max(120, len(pages_0) * 60)), stop=stop)
        else:
            from .workers import run_work
            results, _wd = run_work("ocr", (path, pages_0, vault_dir),
                                    timeout=min(1800, max(180, len(pages_0) * 60)), stop=stop)
    else:
        results, _wd = ocr_mod.ocr_document(path, pages_0, vault_dir)
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
            con.execute('INSERT OR REPLACE INTO ocr_coverage VALUES (?,?,?,?,?)',(fid,rev_id,r.page,r.method,r.error_code))
            # ayni sayfanin eski OCR metni vardiysa (motor degisimi/yeniden deneme)
            # once sil: iki kopya segment aramada duplication yaratir
            con.execute("DELETE FROM segments WHERE file_id=? AND rev_id=? AND kind='ocr_page' AND page=?",
                        (fid, rev_id, r.page))
            if r.words == 0 or not r.text.strip():
                continue
            raw = r.text.strip()
            con.execute(
                "INSERT INTO segments(file_id, rev_id, kind, page, label, raw_text,"
                " method, confidence) VALUES (?,?,?,?,?,?,?,?)",
                (fid, rev_id, "ocr_page", r.page, f"Sayfa {r.page} (OCR)",
                 raw, r.method, round(r.mean_conf, 1)),
            )
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        return q.fail(con, job["job_id"], "CORRUPT_DOCUMENT")
    if any(r.error_code or r.method=='low' or (r.words and r.mean_conf<40) for r in results):
        con.execute("UPDATE files SET index_status='partial',error_code='OCR_LOW_QUALITY' WHERE file_id=?",(fid,)); con.commit()
    if len({p for p,_ in thin})>len(pages_0):
        con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?",(job['job_id'],)); con.commit()
        return 'continuing'
    previous_low=con.execute("SELECT 1 FROM ocr_coverage WHERE file_id=? AND rev_id=? AND (outcome='low' OR error_code IS NOT NULL) LIMIT 1",(fid,rev_id)).fetchone()
    if not previous_low and results and all(r.words and not r.error_code and r.mean_conf>=40 for r in results):
        con.execute("UPDATE files SET index_status='ok',error_code=NULL WHERE file_id=? AND error_code='OCR_PENDING'",(fid,)); con.commit()
    # Tum sayfalar timeout/unavailable ise retry; aksi halde tamamla
    q.complete(con, job["job_id"])
    if gom_mod.model_var_mi():
        q.enqueue(con, fid, sig, kind="embed")
        con.commit()
    return "done"


def run_scan(con, vault_path: str, root: str, stop=None, guarded=False, progress=None, limit=None) -> dict:
    """Tam tarama: kesif + kuyruk isleme. stop(): duraklat/iptal bayragi.
    limit: bu calistirmada en fazla kac dosya islenir (kalan is pending kalir)."""
    nz.install(con)  # segment yazim/silim trigger'lari fold() UDF'ine bagli (v9)
    stats = {"found": 0, "done": 0, "changed": 0, "unstable": 0, "failed": 0,
             "missing": 0, "ocr_done": 0, "ocr_deferred": 0, "ocr_failed": 0,
             "embed_done": 0,
             "hashed": 0, "skipped": 0, "complete": False, "result": "partial"}
    if "updated_at" not in {r[1] for r in con.execute("PRAGMA table_info(scan_runs)")}:
        migrate.ensure_v8(con)
    migrate.ensure_archive(con)
    with ScanLock(vault_path):
        con.execute("CREATE TABLE IF NOT EXISTS scan_selected(file_id INTEGER PRIMARY KEY)")
        absroot = os.path.abspath(root)
        run_id = find_resumable_run(con, absroot)
        if run_id is None:
            run_id = con.execute(
                "INSERT INTO scan_runs(root, started_at) VALUES (?, ?)", (absroot, int(time.time()))
            ).lastrowid
            con.execute("DELETE FROM scan_selected")
            con.commit()
        q.recover_running(con)
        rules = exc.list_rules(con)
        all_complete = True
        seen = set()
        last_report = 0.0
        last_checkpoint = 0.0

        def checkpoint(stage, *, force=False):
            nonlocal last_checkpoint
            now = time.monotonic()
            if not force and now - last_checkpoint < 5:
                return
            con.execute(
                "UPDATE scan_runs SET updated_at=?, stage=?, found=?, done=?, pending=?, "
                "failed=?, ocr_done=?, ocr_failed=? WHERE run_id=?",
                (int(time.time()), stage, stats["found"], stats["done"],
                 con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running') "
                             "AND file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0],
                 stats["failed"], stats["ocr_done"],
                 stats["ocr_failed"], run_id),
            )
            con.commit()
            last_checkpoint = now

        def report(stage, path="", result="", force=False):
            nonlocal last_report
            now = time.monotonic()
            checkpoint(stage)
            if progress and (force or now - last_report >= 0.2):
                pending = con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running')"
                                      " AND file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
                emit_progress(progress, dict(stats, stage=stage, path=path, item_result=result, pending=pending))
                last_report = now

        def quota_full():
            return limit is not None and (stats["done"] + stats["ocr_done"]) >= limit

        def process_batch(cap=None):
            count = 0
            while (cap is None or count < cap) and not quota_full():
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
        run_started = con.execute(
            "SELECT started_at FROM scan_runs WHERE run_id=?", (run_id,)).fetchone()[0] or 0
        done_dirs = completed_dirs(con, run_id)
        stack = [os.path.abspath(root)]
        while stack:
            if stop and stop():
                break
            cur = stack.pop()
            if cur in done_dirs:
                # Bitmis ve run baslangic saniyesinden eski klasore tekrar girilmez;
                # ayni/ileri saniyede degismis klasor normal gezilir (yeni dosya kacmaz).
                try:
                    if os.stat(cur).st_mtime_ns // 1_000_000_000 < run_started:
                        continue
                except OSError:
                    pass
            report("Klasörler keşfediliyor", cur)
            dir_ok = True
            try:
                with os.scandir(cur) as it:
                    entries = list(it)
            except OSError:
                entries = []
                dir_ok = False
                stats["failed"] += 1
                con.execute('INSERT OR REPLACE INTO scan_errors VALUES (?,?,?)',(run_id,cur,'ACCESS_DENIED'))
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
                        if note_discovered(con, entry, commit=False) == "skipped":
                            stats["skipped"] += 1
                        stats["found"] += 1
                        if stats["found"] % 32 == 0:
                            con.commit()
                            process_batch(8)
                        report("Klasörler keşfediliyor", cur)
                except OSError:
                    dir_ok = False
                    stats['failed']+=1
                    con.execute('INSERT OR REPLACE INTO scan_errors VALUES (?,?,?)',(run_id,e.path,'ACCESS_DENIED'))
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
        # guarded modda tek isci oturumu: RapidOCR motoru turda bir kez yuklenir.
        ocr_session = None

        def _taze_ocr_oturumu():
            from .workers import OcrSession
            try:
                return OcrSession()
            except Exception:
                return None

        while True:
            if stop and stop():
                stats["result"] = "cancelled"
                break
            if quota_full():
                break
            job = q.claim(con, ("ocr",), scoped=True)
            if not job:
                break
            if guarded and ocr_session is None:
                ocr_session = _taze_ocr_oturumu()
            path = con.execute("SELECT path FROM files WHERE file_id=?", (job["file_id"],)).fetchone()[0]
            report("OCR ile metin okunuyor", path, force=True)
            try:
                r = _process_ocr_job(con, job, os.path.dirname(vault_path), stop, guarded,
                                     ocr_session if guarded else None)
            except InterruptedError:
                con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?", (job["job_id"],))
                con.commit()
                stats["result"] = "cancelled"
                break
            except TimeoutError:
                r = q.fail(con, job["job_id"], "PROCESS_TIMEOUT")
                ocr_session = None  # surec bekci tarafinda olduruldu; sonraki is taze alir
            except Exception:
                r = q.fail(con, job["job_id"], "CORRUPT_DOCUMENT")
                if guarded and ocr_session is not None:
                    ocr_session = _taze_ocr_oturumu()  # suruolen olmus olabilir; yenile
            stats["ocr_done"] += 1 if r == "done" else 0
            stats["ocr_deferred"] += 1 if r == "deferred" else 0
            if r in ("retry", "dead"):
                stats["ocr_failed"] += 1
            report("OCR işleniyor", path, r)
        if ocr_session is not None:
            ocr_session.kill()
        if gom_mod.model_var_mi():
            from .embed import MODEL_VER
            rows = con.execute("SELECT f.file_id,f.size,f.mtime_ns FROM files f "
                "JOIN scan_selected sel ON sel.file_id=f.file_id WHERE EXISTS("
                "SELECT 1 FROM segments s LEFT JOIN embeddings e ON e.seg_id=s.seg_id "
                "AND e.model_ver=? WHERE s.file_id=f.file_id AND s.kind NOT IN ('name_only','context') "
                "AND e.seg_id IS NULL)", (MODEL_VER,)).fetchall()
            for fid, size, modified in rows:
                q.enqueue(con, fid, q.signature_of(size,modified), kind='embed')
            con.commit()
        # Shared native process isolates driver failures without duplicate model loads.
        if gom_mod.model_var_mi():
            from . import embed as embedding
            ot = embedding.isit_oturumu()
            if ot is None:
                report('Vektör motoru açılamadı; klasik arama sürüyor', root, force=True)
            while ot is not None:
                if stop and stop():
                    stats['result'] = 'cancelled'
                    break
                job = q.claim(con, ('embed',), scoped=True)
                if not job: break
                fid = job['file_id']
                report('Vektör dizini hazırlanıyor', str(fid), force=True)
                try:
                    outcome = gom_mod.process_embed_job(con, job, kodla=lambda texts: ot.encode(texts, gorev='belge', cancel=stop))
                except InterruptedError:
                    con.execute("UPDATE jobs SET status='pending',lease_until=0 WHERE job_id=?", (job['job_id'],))
                    con.commit()
                    stats['result'] = 'cancelled'
                    break
                except Exception as error:
                    outcome = q.fail(con, job['job_id'], type(error).__name__)
                if outcome == 'done': stats['embed_done'] += 1
                if outcome in ('retry', 'dead'): stats['failed'] += 1
                report('Vektör işleniyor', str(fid), outcome)
        # --- kopya hash (arka plan; sinirli; kaynagi bir kez daha okur) ---
        try:
            from . import dup as dup_mod
            if not (stop and stop()):
                report("Kopyalar doğrulanıyor", root, force=True)
                stats["hashed"] = dup_mod.verify_pending(con, scoped=True, stop=stop).get("verified", 0)
        except Exception as error:
            stats["failed"] += 1
            con.execute("UPDATE scan_runs SET error_code='HASH_ERROR' WHERE run_id=?", (run_id,))
            con.commit()
            report("Kopya doğrulaması tamamlanamadı", root, type(error).__name__, force=True)
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
                    # Preserve searchable historical content when the source vanishes.
                    con.execute("UPDATE files SET index_status='missing' WHERE file_id=?", (fid,))
                    stats["missing"] += 1
            con.commit()
            pending = con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running') "
                                  "AND file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
            incomplete=con.execute("SELECT count(*) FROM files WHERE file_id IN (SELECT file_id FROM scan_selected) AND index_status NOT IN ('ok','excluded')").fetchone()[0]
            stats['incomplete']=incomplete
            stats["complete"] = not pending and not stats["failed"] and not stats["ocr_failed"] and not incomplete
            stats["result"] = "complete" if stats["complete"] else "partial"
        stats["pending"] = con.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running') "
                                       "AND file_id IN (SELECT file_id FROM scan_selected)").fetchone()[0]
        checkpoint("Bitti", force=True)
        report("Tarama tamamlandı" if stats["complete"] else "Tarama durdu", root, force=True)
        con.execute("UPDATE scan_runs SET finished_at=?, result=? WHERE run_id=?",
                    (int(time.time()), stats["result"], run_id))
        con.commit()
    return stats
