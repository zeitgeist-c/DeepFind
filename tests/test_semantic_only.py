"""Vector-only retrieval and v10 lifecycle contracts."""
import sqlite3
import numpy as np
import pytest
from deepfind import migrate,rank,embed,exclusions
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

def test_zayif_kuyruk_en_iyiye_gore_elenir(tmp_path):
    """En iyi skordan ESIK_MARJ geride kalan sonuca girmez; en iyi korunur."""
    import numpy as np
    con=_kasa(tmp_path)
    f1=_dosya(con,'ust.txt','kedi mamasi')
    f2=_dosya(con,'orta.txt','kedi tasmasi')
    f3=_dosya(con,'zayif.txt','kedi oyuncagi')
    q=np.zeros(256,dtype=np.float32);q[1]=1.0
    def _vec(benzerlik):
        v=np.zeros(256,dtype=np.float32);v[1]=benzerlik
        v[0]=(1.0-benzerlik**2)**0.5
        return v.tobytes()
    for fid,benzerlik in ((f1,1.0),(f2,0.985),(f3,0.90)):
        seg=con.execute("SELECT seg_id FROM segments WHERE file_id=? AND kind NOT IN ('name_only','context')",(fid,)).fetchone()[0]
        con.execute("INSERT INTO embeddings VALUES (?,?,?,?)",
                    (seg,embed.MODEL_VER,embed.DIM,_vec(benzerlik)))
    con.commit()
    kodla=lambda metinler:np.tile(q,(len(metinler),1))
    out=rank.search_semantic(con,'kedi',kodla=kodla)
    assert [r['file_id'] for r in out['results']]==[f1,f2]
    assert out['gizlenen']==1
    assert out['results'][0]['vec_skor']>=out['results'][1]['vec_skor']
    con.close()

def test_taban_alti_zayif_sadece_doner_istenince_acilir(tmp_path):
    """En iyi skor tabanin altindaysa liste bos + bayrak; bayrakla hepsi gelir."""
    import numpy as np
    con=_kasa(tmp_path)
    f1=_dosya(con,'zayif_a.txt','kedi mamasi')
    f2=_dosya(con,'zayif_b.txt','kedi tasmasi')
    q=np.zeros(256,dtype=np.float32);q[1]=1.0
    v=np.zeros(256,dtype=np.float32);v[1]=0.70;v[0]=(1.0-0.70**2)**0.5
    for fid in (f1,f2):
        seg=con.execute("SELECT seg_id FROM segments WHERE file_id=? AND kind NOT IN ('name_only','context')",(fid,)).fetchone()[0]
        con.execute("INSERT INTO embeddings VALUES (?,?,?,?)",
                    (seg,embed.MODEL_VER,embed.DIM,v.tobytes()))
    con.commit()
    kodla=lambda metinler:np.tile(q,(len(metinler),1))
    out=rank.search_semantic(con,'kedi',kodla=kodla)
    assert out['results']==[] and out['zayif_sadece'] and out['gizlenen']==2
    acik=rank.search_semantic(con,'kedi',kodla=kodla,zayiflari_goster=True)
    assert len(acik['results'])==2 and not acik['zayif_sadece'] and acik['gizlenen']==0
    con.close()

def test_sayfa_sec_bant_disini_elemez_ayrintiyi_one_cikarir():
    """Bant ici: cok ayrinti karsilayan kazanir; bant disi: skor birinciligi korunur."""
    ter = ["uzay", "giysisi", "kadin", "kizil", "cisim"]
    adaylar = [(0.800, 1, "Sayfa 10", 10), (0.795, 2, "Sayfa 20", 20), (0.700, 3, "Sayfa 30", 30)]
    metinler = {1: "uzay gemisi motoru", 2: "uzay giysisi giyen kadın ve kızıl cisim",
                3: "uzay giysisi giyen kadın kızıl cisim şehir koşu gezegen"}
    assert rank._sayfa_sec(ter, adaylar, metinler) == (2, "Sayfa 20", 20)

def test_motor_bandaki_cok_ayrintili_sayfayi_gosterir(tmp_path):
    """En yuksek benzerlik ilk gelse bile bant ici kapsama kazanan sayfa gosterilir."""
    import numpy as np
    con = _kasa(tmp_path)
    fid = _dosya(con, 'sahne.txt', 'kedi mamasi ve su kabi')
    seg_a = con.execute("SELECT seg_id FROM segments WHERE file_id=? AND kind NOT IN ('name_only','context')",
                        (fid,)).fetchone()[0]
    con.execute("UPDATE segments SET page=7, label='Sayfa 7' WHERE seg_id=?", (seg_a,))
    con.execute("INSERT INTO segments(file_id, kind, page, label, raw_text) VALUES (?,?,?,?,?)",
                (fid, 'para', 9, 'Sayfa 9', 'kedi tasmasi ve oyuncak'))
    seg_b = con.execute("SELECT seg_id FROM segments WHERE file_id=? AND page=9", (fid,)).fetchone()[0]
    v_a = np.zeros(256, dtype=np.float32); v_a[1] = 1.0
    v_b = np.zeros(256, dtype=np.float32); v_b[1] = 0.995; v_b[0] = (1.0 - 0.995**2) ** 0.5
    con.execute("INSERT INTO embeddings VALUES (?,?,?,?)", (seg_a, embed.MODEL_VER, 256, v_a.tobytes()))
    con.execute("INSERT INTO embeddings VALUES (?,?,?,?)", (seg_b, embed.MODEL_VER, 256, v_b.tobytes()))
    con.commit()
    q = np.zeros((1, 256), dtype=np.float32); q[0, 1] = 1.0
    out = rank.search_semantic(con, 'kedi tasmasi oyuncak', kodla=lambda m: q)
    assert out['results'] and out['results'][0]['page'] == 9
    con.close()

def test_zayif_acis_filtreyi_korur(tmp_path):
    """Etiket filtresi zayıflar açılırken de uygulanır."""
    import numpy as np
    con = _kasa(tmp_path)
    f1 = _dosya(con, 'etiketli.txt', 'kedi mamasi')
    f2 = _dosya(con, 'diger.txt', 'kedi mamasi')
    v = np.zeros(256, dtype=np.float32); v[1] = 0.70; v[0] = (1.0 - 0.70**2) ** 0.5
    for fid in (f1, f2):
        seg = con.execute("SELECT seg_id FROM segments WHERE file_id=? AND kind NOT IN ('name_only','context')", (fid,)).fetchone()[0]
        con.execute("INSERT INTO embeddings VALUES (?,?,?,?)",
                    (seg, embed.MODEL_VER, 256, v.tobytes()))
    con.commit()
    rank.set_tag(con, f1, 'onemli')
    q = np.zeros((1, 256), dtype=np.float32); q[0, 1] = 1.0
    kodla = lambda m: q
    kapali = rank.search_semantic(con, 'kedi', kodla=kodla, tag='onemli')
    assert kapali['results'] == [] and kapali['zayif_sadece']
    acik = rank.search_semantic(con, 'kedi', kodla=kodla, tag='onemli', zayiflari_goster=True)
    assert [r['file_id'] for r in acik['results']] == [f1]
    con.close()

def test_gui_scan_cannot_finish_without_content_vectors(tmp_path,monkeypatch):
    from deepfind import vault,coordinator,gom
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
