"""Buyuk sentetik v8 bicimli kasa: v9 migration + VACUUM oncesi/sonrasi boyut.
Kapi raporu: once/sonra MB + yuzde kazanc + sema dogrulamasi + integrity-check."""
import os, sys, time, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from deepfind import vault, migrate, normalize as nz

base = tempfile.mkdtemp(prefix="v9-boyut-")
db = os.path.join(base, "index.db")
PW = "boyut-kanit-12345"
con = vault.open_vault(db, PW)
migrate.ensure_current(con)  # v9 semasi
# v8 bicimine dusur
con.executescript("""
ALTER TABLE segments ADD COLUMN folded_text TEXT DEFAULT '';
CREATE VIRTUAL TABLE docs_fts_folded USING fts5(label, raw_text, content='segments', content_rowid='seg_id');
CREATE TRIGGER segf_ai AFTER INSERT ON segments BEGIN
  INSERT INTO docs_fts_folded(rowid,label,raw_text) VALUES(new.seg_id,new.label,new.folded_text); END;
CREATE TRIGGER segf_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts_folded(docs_fts_folded,rowid,label,raw_text) VALUES('delete',old.seg_id,old.label,old.folded_text); END;
DROP TRIGGER seg_ai; DROP TRIGGER seg_ad;
CREATE TRIGGER seg_ai AFTER INSERT ON segments BEGIN
  INSERT INTO docs_fts(rowid,label,raw_text) VALUES(new.seg_id,new.label,new.raw_text); END;
CREATE TRIGGER seg_ad AFTER DELETE ON segments BEGIN
  INSERT INTO docs_fts(docs_fts,rowid,label,raw_text) VALUES('delete',old.seg_id,old.label,old.raw_text); END;
DELETE FROM schema_meta WHERE k='fts_folded';
UPDATE schema_meta SET v='8' WHERE k='schema_version';
""")
import random
random.seed(7)
kelimeler = ["fatura","vergi","İstanbul","Iğdır","2024","sözleşme","makbuz","rapor","Şırnak","ÇANKIRI","kdv","dask"]
t0=time.perf_counter()
N=200000
with con:
    for f in range(N//50):
        rows=[]
        for j in range(50):
            i=f*50+j
            con.execute("INSERT INTO files(path,name,ext,index_status) VALUES (?,?,?,'ok')",
                        (f"C:/arşiv/{i}.pdf", f"belge-{i}.pdf", ".pdf"))
            fid=con.execute("SELECT last_insert_rowid()").fetchone()[0]
            ham=" ".join(random.choices(kelimeler,k=180))
            con.execute("INSERT INTO segments(file_id,kind,label,raw_text,folded_text) VALUES (?,'pdf_page','Sayfa 1',?,?)",
                        (fid,ham,nz.folded(ham)))
print(f"v8 bicimli kasa uretildi ({N} seg): {time.perf_counter()-t0:.0f}s")
con.close()
before=os.path.getsize(db)
con=vault.open_vault(db,PW)
t0=time.perf_counter(); migrate.ensure_current(con)
t1=time.perf_counter()
t2=time.perf_counter(); con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH '\"istanbul\"'").fetchone()
t3=time.perf_counter()
con.execute("VACUUM")
after=os.path.getsize(db)
cols={r[1] for r in con.execute("PRAGMA table_info(segments)")}
ok = ("folded_text" not in cols
      and not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts_folded'").fetchone()
      and con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()[0]=="9")
con.execute("INSERT INTO docs_fts(docs_fts) VALUES('integrity-check')")
con.close()
print(f"migration suresi: {t1-t0:.1f}s | katlanmis sorgu: {(t3-t2)*1000:.0f}ms")
print(f"once={before/1024**2:.0f} MB sonra={after/1024**2:.0f} MB  ({100*(1-after/before):.0f}% kazanc)")
print("sema v9 dogrulamasi:", "OK" if ok else "KOTU", "| integrity-check gecti")
