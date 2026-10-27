from PIL import Image
from deepfind import ocr

def test_entirely_white_page_skips_ocr_but_faint_ink_does_not(tmp_path,monkeypatch):
    png=tmp_path/'page.png';image=Image.new('RGB',(100,100),'white');image.save(png)
    monkeypatch.setattr(ocr,'engine_ok',lambda:(True,[]))
    monkeypatch.setattr(ocr,'render_page_png',lambda *a:(str(png),300))
    calls=[]
    monkeypatch.setattr(ocr,'recognize_png',lambda p:(calls.append(p) or ('silik',80,1)))
    result=ocr.ocr_page('synthetic.pdf',0,str(tmp_path))
    assert result.method=='blank' and result.error_code is None and not calls
    image.putpixel((50,50),(250,250,250));image.save(png)
    assert ocr.ocr_page('synthetic.pdf',0,str(tmp_path)).method=='basic' and len(calls)==1


def test_old_empty_page_failure_is_retried_once_and_completes(tmp_path,monkeypatch):
    import sqlite3
    from deepfind import migrate,coordinator as c,ocr_setup,job_queue as q,gom
    from deepfind.scan import Entry
    p=tmp_path/'blank.pdf';p.write_bytes(b'synthetic-stat-only')
    stat=p.stat();sig=q.signature_of(stat.st_size,stat.st_mtime_ns)
    con=sqlite3.connect(':memory:');migrate.ensure_current(con)
    fid=c.ensure_file(con,Entry(str(p),p.name,'.pdf',stat.st_size,stat.st_mtime_ns))
    rev=con.execute("INSERT INTO file_revisions(file_id,signature,extractor,created_at,active) VALUES (?,?,?,0,1)",(fid,sig,migrate.EXTRACTOR_VERSION)).lastrowid
    con.execute("INSERT INTO segments(file_id,rev_id,kind,page,label,raw_text) VALUES (?,?,'pdf_page',1,'Sayfa','')",(fid,rev))
    con.execute("UPDATE files SET index_status='partial',error_code='OCR_LOW_QUALITY'")
    con.execute("INSERT INTO ocr_coverage VALUES (?,?,1,'low','NO_TEXT')",(fid,rev))
    con.execute("UPDATE schema_meta SET v='rapid-1' WHERE k='ocr_version'");con.commit()
    assert ocr_setup.engine_backfill(con)==1
    monkeypatch.setattr(ocr,'ocr_document',lambda *a:([ocr.OcrPage(1,method='blank')],None))
    monkeypatch.setattr(ocr,'ram_allows',lambda:True)
    monkeypatch.setattr(gom,'model_var_mi',lambda:False)
    job=q.claim(con,('ocr',))
    assert c._process_ocr_job(con,job,str(tmp_path))=='done'
    assert con.execute('SELECT index_status,error_code FROM files').fetchone()==('ok',None)
    assert ocr_setup.engine_backfill(con)==0 and con.execute('SELECT outcome FROM ocr_coverage').fetchone()[0]=='blank'
    con.close()
