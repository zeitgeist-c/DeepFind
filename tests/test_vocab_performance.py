import sqlite3
import pytest
from evrakci import migrate,vocab

def database():
    con=sqlite3.connect(':memory:');migrate.ensure_current(con)
    fid=con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/kitap.pdf','iktisat.pdf','.pdf')").lastrowid
    con.executemany("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Sayfa',?)",[(fid,'Şırnak sözleşme sözleşme énergie iktisâd'),(fid,'İktisat sözleşme')]);con.commit()
    return con,fid

def test_vocab_reads_indexed_terms_instead_of_document_bodies():
    con,_=database();trace=[];con.set_trace_callback(trace.append)
    assert vocab.rebuild_vocab(con)>0
    assert not any('SELECT RAW_TEXT FROM SEGMENTS' in s.upper() for s in trace)
    assert con.execute("SELECT freq FROM vocabulary WHERE term='sozlesme'").fetchone()[0]==3
    assert con.execute("SELECT freq FROM vocabulary WHERE term='iktisat'").fetchone()[0]==2
    assert con.execute("SELECT freq FROM vocabulary WHERE term='nergie'").fetchone()[0]==1
    con.close()

def test_unchanged_scan_skips_rebuild_but_content_changes_refresh():
    con,fid=database();vocab.rebuild_vocab(con);trace=[];con.set_trace_callback(trace.append)
    vocab.rebuild_vocab(con)
    assert not any('DELETE FROM VOCABULARY' in s.upper() for s in trace)
    con.execute('DELETE FROM segments WHERE file_id=?',(fid,))
    con.executemany("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Sayfa','yeniterim')",[(fid,),(fid,)]);con.commit()
    vocab.rebuild_vocab(con)
    assert con.execute("SELECT freq FROM vocabulary WHERE term='yeniterim'").fetchone()[0]==2
    assert not con.execute("SELECT 1 FROM vocabulary WHERE term='sozlesme'").fetchone()
    con.close()

def test_cancel_preserves_live_vocabulary_and_retry_counts_progress():
    con,fid=database();vocab.rebuild_vocab(con)
    old=con.execute('SELECT * FROM vocabulary ORDER BY term').fetchall()
    con.execute('DELETE FROM segments WHERE file_id=?',(fid,))
    con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Sayfa','yeni')",(fid,));con.commit()
    with pytest.raises(InterruptedError):vocab.rebuild_vocab(con,stop=lambda:True)
    assert con.execute('SELECT * FROM vocabulary ORDER BY term').fetchall()==old
    reports=[];vocab.rebuild_vocab(con,progress=lambda d,t:reports.append((d,t)))
    assert reports and reports[-1][0]==reports[-1][1] and reports[-1][1]>0
    con.close()
