"""A4 testleri: kuyruk, kurtarma, kilit, haric, kaynak-yazmama. Sentetik veri."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evrakci import coordinator, exclusions, extract, queue, scan, schema, search, vault  # noqa: E402
from evrakci.migrate import ensure_v4, ensure_v6  # noqa: E402
from evrakci.vocab import ensure_v5  # noqa: E402

PW = "test-sifresi-12345"


def _kasa(tmp_path):
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v4(con)
    ensure_v6(con)
    ensure_v5(con)
    return con, db


def _yaz(path: str, icerik: bytes = b"test"):
    with open(path, "wb") as f:
        f.write(icerik)


def _pdf(kok: str, ad: str, metin: str) -> str:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 14)
    c.drawString(72, 750, metin)
    c.save()
    return p


def _dizin_anlik(dizin: str) -> dict:
    out = {}
    for dp, _dn, fn in os.walk(dizin):
        for f in fn:
            p = os.path.join(dp, f)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def test_scn01_kesinti_tekrarsiz(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    for i in range(4):
        _pdf(kok, f"b{i}.pdf", f"belge numara {i} Ankara")
    time.sleep(2.5)  # kararlilik esigi disi: kararli dosyalar
    con, db = _kasa(tmp_path)
    s1 = coordinator.run_scan(con, db, kok)
    assert s1["result"] == "complete" and s1["found"] == 4, s1
    assert s1["done"] == 4, s1
    n_seg = con.execute("SELECT count(*) FROM segments").fetchone()[0]
    # ikinci tarama: ayni surumler tekrar islenmez
    s2 = coordinator.run_scan(con, db, kok)
    assert s2["found"] == 4 and q_pending(con) == 0, s2
    assert con.execute("SELECT count(*) FROM segments").fetchone()[0] == n_seg
    # yarim is birak ve kurtar
    con.execute("UPDATE jobs SET status='running' WHERE 0")
    fid = con.execute("SELECT file_id FROM files LIMIT 1").fetchone()[0]
    con.execute("INSERT INTO jobs(file_id, signature, kind, status) VALUES (?,?, 'extract','running')",
                (fid, "0:0"))
    con.commit()
    assert queue.recover_running(con) == 1
    con.close()


def q_pending(con):
    return queue.pending_count(con)


def test_degisen_dosya_yeni_surun(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    p = _pdf(kok, "degisen.pdf", "eski icerik Kayseri")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    assert search.search(con, "Kayseri")
    _pdf(kok, "degisen.pdf", "yeni icerik Trabzon")
    time.sleep(2.5)  # yeni surum kararli hale gelsin
    s = coordinator.run_scan(con, db, kok)
    assert s["result"] == "complete", s
    assert search.search(con, "Trabzon"), "yeni icerik bulunmali"
    assert not search.search(con, "Kayseri"), "eski icerik normal aramada olmamali"
    con.close()


def test_scn05_tek_koordinator(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    con, db = _kasa(tmp_path)
    with coordinator.ScanLock(db):
        with pytest.raises(coordinator.AlreadyRunning):
            with coordinator.ScanLock(db):
                pass
    con.close()


def _belgeler(rows):
    """Segment-duzeyi eski aramayi belge duzeyine indirger (A5 sozlesmesi)."""
    return sorted({r["path"] for r in rows})


def test_exc01_haric_temizligi(tmp_path):
    kok = str(tmp_path / "arsiv")
    alt = os.path.join(kok, "gizli")
    os.makedirs(alt)
    _pdf(kok, "acik.pdf", "acik belge Ankara")
    _pdf(alt, "sakli.pdf", "sakli belge Ankara")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    assert len(_belgeler(search.search(con, "sakli"))) == 1
    exclusions.add(con, alt)
    n = exclusions.purge_rule(con, alt)
    assert n == 1, n
    assert search.search(con, "sakli") == [], "haric icerik aramada olmamali"
    assert len(_belgeler(search.search(con, "acik"))) == 1
    con.close()


def test_saf01_kaynaga_yazma_yok(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    for i in range(3):
        _pdf(kok, f"k{i}.pdf", f"kaynak_guvenlik {i}")
    time.sleep(2.5)
    once = _dizin_anlik(kok)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    search.search(con, "kaynak_guvenlik")
    con.close()
    sonra = _dizin_anlik(kok)
    assert once == sonra, "kaynak dizinde dosya/mtime degisti!"
    # kod denetimi (yardimci; tek kanit degil): kaynak okuma yolu disinda yazan acis yok.
    # Izinli istisnalar (plan bolum 16/17): kasa kilidi, kontrollu temp temizligi,
    # salt-okunur PATH aramasi (shutil.which). Kaynak-dizin runtime kaniti yukarida.
    import pathlib
    src = pathlib.Path(os.path.dirname(__file__), "..", "src", "evrakci")
    yazan = []
    for f in src.glob("*.py"):
        if f.name in ("cli.py", "backup.py", "recovery.py"):
            # backup.py / recovery.py: yalniz yonetilen yerel hedeflere yazar
            # (dest/staging/manifest ve kasa klasorundeki evrakci-kurtarma.*);
            # kaynak-dizin kaniti test_backup.py::test_bak_kaynaga_dokunmaz ve
            # test_recovery.py::test_kurtarma_islem_kaynaga_dokunmaz (runtime).
            continue
        in_guard = False  # _rmtree_tmp: tek korumali silme noktasi (ocr-tmp alti)
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            s = ln.strip()
            if s.startswith("def _rmtree_tmp"):
                in_guard = True
                continue
            if in_guard and (not ln.startswith((" ", "\t")) or s.startswith("def ")):
                in_guard = False
            if in_guard:
                continue
            if s.startswith("#") or s.startswith('"'):
                continue
            if ("shutil.which(" in ln or "_rmtree_tmp" in ln
                    or "self.path" in ln or "TemporaryDirectory" in ln):
                continue
            if ("open(" in ln and (", \"w" in ln or ", 'w" in ln or 'mode="w' in ln
                    or "mode='w" in ln or '"a"' in ln or "'a'" in ln)) \
                    or "os.remove(" in ln or "os.rename(" in ln or "shutil." in ln:
                yazan.append(f"{f.name}:{i}:{s}")
    assert yazan == [], f"kaynak yazma suphesi: {yazan}"
    # kontrollu temp kaynaga degil kasa cevresine yazilir
    assert not os.path.exists(os.path.join(kok, "ocr-tmp")), "temp kaynaga sizdi!"


def test_scn04_silinen_missing(tmp_path):
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    p = _pdf(kok, "gidecek.pdf", "gidici belge Edirne")
    _pdf(kok, "kalacak.pdf", "kalici belge Edirne")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    coordinator.run_scan(con, db, kok)
    assert search.search(con, "gidici")
    os.remove(p)
    s = coordinator.run_scan(con, db, kok)
    assert s["result"] == "complete" and s["missing"] == 1, s
    assert search.search(con, "gidici") == [], "silinen normal sonucta olmamali"
    assert len(_belgeler(search.search(con, "kalici"))) == 1
    con.close()


def test_saf02_salt_okunur_kaynak(tmp_path):
    import subprocess
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "ro.pdf", "saltokunur belge Bursa")
    time.sleep(2.5)
    subprocess.run(["attrib", "+r", kok], check=True)
    try:
        once = _dizin_anlik(kok)
        con, db = _kasa(tmp_path)
        s = coordinator.run_scan(con, db, kok)
        assert s["result"] == "complete" and s["done"] == 1, s
        assert search.search(con, "saltokunur")
        con.close()
        assert _dizin_anlik(kok) == once, "salt-okunur kaynaga yazildi!"
    finally:
        subprocess.run(["attrib", "-r", kok], check=True)


def test_retry_dead(tmp_path):
    con, db = _kasa(tmp_path)
    con.execute("INSERT INTO files(path,name,ext) VALUES ('x.pdf','x.pdf','.pdf')")
    fid = con.execute("SELECT file_id FROM files").fetchone()[0]
    queue.enqueue(con, fid, "1:1")
    con.commit()
    job = queue.claim(con)
    for _ in range(3):
        assert queue.fail(con, job["job_id"], "CORRUPT_DOCUMENT") == "retry"
    assert queue.fail(con, job["job_id"], "CORRUPT_DOCUMENT") == "dead"
    assert queue.pending_count(con) == 0
    con.close()


def test_doc_adaptru_yoksa_ad_yol(tmp_path):
    from evrakci import doc_adapter
    assert doc_adapter.find_office() is None  # bu makinede LO yok; onkosul raporlanir
    assert doc_adapter.extract_doc_guarded("yok.doc") is None
    r = extract.extract("arsiv.dp", ".doc", 10)
    assert r.status == "unsupported_content" and r.error_code == "UNSUPPORTED_CONTENT"


def test_scn06_iptal_devam_tutarliligi(tmp_path):
    """Iptal (stop) -> result cancelled; yeniden tarama complete + kayipsiz."""
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    for i in range(4):
        _pdf(kok, f"c{i}.pdf", f"iptal testi {i} Ankara")
    time.sleep(2.5)
    con, db = _kasa(tmp_path)
    cagrilar = []
    def erken_dur():
        cagrilar.append(1)
        return len(cagrilar) > 2  # kesif basinda dur: cancelled + kaldi yerden devam
    s1 = coordinator.run_scan(con, db, kok, stop=erken_dur)
    assert s1["result"] == "cancelled", s1
    s2 = coordinator.run_scan(con, db, kok)
    assert s2["result"] == "complete", s2
    assert s1["done"] + s2["done"] == 4, (s1, s2)  # kayip is yok
    assert len(search.search(con, "iptal")) == 4
    con.close()
