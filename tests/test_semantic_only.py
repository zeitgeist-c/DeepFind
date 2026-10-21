"""Vector-only retrieval and v10 lifecycle contracts."""
import sqlite3
import numpy as np
import pytest
from evrakci import migrate,rank,embed,exclusions
from test_hibrit import _duzen,_kasa,_kodla_b,_vektor,_dosya

def test_fresh_schema_has_no_lexical_store():
    con=sqlite3.connect(':memory:');migrate.ensure_current(con)
    names={r[0] for r in con.execute('SELECT name FROM sqlite_master')}
    assert not {'docs_fts','docs_fts_folded','vocabulary','vocabulary_build'} & names
    assert not any(n.startswith('vocab_') for n in names)
    assert con.execute("SELECT v FROM schema_meta WHERE k='schema_version'").fetchone()==('10',)
    con.close()

def test_migration_preserves_vectors_settings_and_text_without_rebuild():
    con=sqlite3.connect(':memory:');migrate.ensure_current(con)
    fid=_dosya(con,'scan0047.txt','makinelerin periyodik bakım sözleşmesi')
    _vektor(con,'periyodik',1)
    con.execute("INSERT INTO settings VALUES ('example','preserved')")
    con.executescript("""
        CREATE VIRTUAL TABLE docs_fts USING fts5(raw_text);
        CREATE VIRTUAL TABLE docs_fts_folded USING fts5(raw_text);
        CREATE TABLE vocabulary(term TEXT PRIMARY KEY,freq INTEGER);
        CREATE TRIGGER seg_ai AFTER INSERT ON segments BEGIN
        INSERT INTO docs_fts(raw_text) VALUES (new.raw_text); END;
        UPDATE schema_meta SET v='9' WHERE k='schema_version';
    """)
    before=con.execute('SELECT * FROM embeddings').fetchall()
    trace=[];con.set_trace_callback(trace.append);migrate.ensure_current(con)
    assert con.execute('SELECT * FROM embeddings').fetchall()==before
    assert con.execute("SELECT v FROM settings WHERE k='example'").fetchone()==('preserved',)
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts'").fetchone()
    assert not any('INSERT INTO docs_fts' in sql for sql in trace)
    trace.clear()
    for _ in range(3):migrate.ensure_current(con)
    assert not any('DROP TABLE' in sql for sql in trace)
    assert rank.search_semantic(con,'onarım anlaşması',kodla=_kodla_b)['results'][0]['file_id']==fid
    con.close()

def test_unhelpful_name_found_by_content_and_best_page(tmp_path):
    con=_kasa(tmp_path)
    fid=_dosya(con,'scan0047.txt','makinelerin bakımı')
    _vektor(con,'bakımı',1)
    sid=con.execute("INSERT INTO segments(file_id,kind,label,page,raw_text) VALUES (?,'para','Sayfa 5',5,'periyodik servis sözleşmesi')",(fid,)).lastrowid
    con.execute("UPDATE embeddings SET vec=?",(np.ones(256,dtype=np.float32).tobytes(),))
    con.execute('INSERT INTO embeddings VALUES (?,?,?,?)',(sid,embed.MODEL_VER,embed.DIM,_kodla_b(['x'])[0].tobytes()))
    con.commit()
    out=rank.search_semantic(con,'cihazların onarım anlaşmaları',kodla=_kodla_b)
    assert len(out['results'])==1
    assert out['results'][0]['page']==5
    assert out['results'][0]['score_class']=='semantic'
    con.close()

def test_no_vectors_is_explicitly_not_a_keyword_fallback(tmp_path):
    con=_kasa(tmp_path);_duzen(con);con.execute('DELETE FROM embeddings');con.commit()
    out=rank.search_semantic(con,'kedi',kodla=_kodla_b)
    assert out['results']==[] and not out['empty']
    con.close()

def test_no_model_or_bad_vector_never_leaks_lexical_results(tmp_path):
    con=_kasa(tmp_path);_duzen(con)
    assert rank.search_semantic(con,'kedi')['semantic_error']
    for bad in [np.zeros((1,256)),np.full((1,256),np.nan),np.ones((1,128))]:
        out=rank.search_semantic(con,'kedi',kodla=lambda _,bad=bad:bad)
        assert out['results']==[] and out['semantic_error']
    con.close()

def test_quotes_and_boolean_words_are_natural_query_text(tmp_path):
    con=_kasa(tmp_path);_duzen(con);seen=[]
    def encoder(texts):seen.extend(texts);return _kodla_b(texts)
    for query in ['"evcil hayvan"','kedi -tasması','kedi OR köpek','NOT ödenen borçlar']:
        out=rank.search_semantic(con,query,kodla=encoder)
        assert out['results'] and seen[-1]==query
    con.close()

def test_missing_excluded_and_wrong_version_vectors_never_return(tmp_path):
    con=_kasa(tmp_path);_duzen(con)
    con.execute("UPDATE files SET source_status='missing'");con.commit()
    assert not rank.search_semantic(con,'kedi',kodla=_kodla_b)['results']
    con.execute("UPDATE files SET source_status='ok'");con.commit()
    exclusions.add_and_purge(con,'b_belge.txt')
    assert not rank.search_semantic(con,'kedi',kodla=_kodla_b)['results']
    con.close()

def test_query_limits_and_empty_without_model(tmp_path):
    con=_kasa(tmp_path)
    assert rank.search_semantic(con,'  ')['empty']
    with pytest.raises(ValueError):rank.search_semantic(con,'a'*2001)
    con.close()

def test_gui_scan_cannot_finish_without_content_vectors(tmp_path,monkeypatch):
    from evrakci import vault,coordinator,gom
    from test_scan_progress import files
    source=tmp_path/'source';files(source,1)
    path=str(tmp_path/'vault.db')
    con=vault.open_vault(path,'synthetic-missing-model-1234');migrate.ensure_current(con)
    monkeypatch.setattr(gom,'model_var_mi',lambda:False)
    result=coordinator.run_scan(con,path,str(source))
    assert result['done']==1
    assert not result['complete'] and result['documents_done']==0
    assert result['result']=='partial'
    con.close()
