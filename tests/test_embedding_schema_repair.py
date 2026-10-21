import sqlite3
import pytest
import numpy as np

from evrakci import migrate, coordinator, gom, embed, vault, job_queue
from test_scan_progress import files


@pytest.mark.parametrize('version', ['7', '8', '9'])
def test_current_marker_does_not_hide_missing_embedding_table(version):
    con = sqlite3.connect(':memory:')
    migrate.ensure_current(con)
    fid = con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/old.txt','old.txt','.txt')").lastrowid
    con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Belge','Şırnak sözleşme')", (fid,))
    con.execute('DROP TABLE embeddings')
    con.execute("UPDATE schema_meta SET v=? WHERE k='schema_version'", (version,))
    con.commit()
    trace = []; con.set_trace_callback(trace.append)
    migrate.ensure_current(con)
    assert con.execute('SELECT count(*) FROM embeddings').fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH 'sirnak'").fetchone()[0] == 1
    assert not any("'delete-all'" in sql.lower() for sql in trace)
    assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    con.close()


def test_dead_work_cannot_be_reported_as_a_complete_scan(tmp_path, monkeypatch):
    root=tmp_path/'source';files(root,1)
    path=str(tmp_path/'vault.db');con=vault.open_vault(path,'synthetic-dead-1234');migrate.ensure_current(con)
    monkeypatch.setattr(gom,'model_var_mi',lambda:False)
    assert coordinator.run_scan(con,path,str(root))['complete']
    fid,size,mtime=con.execute('SELECT file_id,size,mtime_ns FROM files').fetchone()
    job_queue.enqueue(con,fid,job_queue.signature_of(size,mtime))
    con.execute("UPDATE jobs SET status='dead'");con.commit()
    result=coordinator.run_scan(con,path,str(root))
    assert result['documents_done']==0 and not result['complete'] and result['result']=='partial'
    con.close()


def test_incorrect_vector_dimensions_are_backfilled(tmp_path, monkeypatch):
    root=tmp_path/'source';files(root,1)
    path=str(tmp_path/'vault.db');con=vault.open_vault(path,'synthetic-vector-1234');migrate.ensure_current(con)
    monkeypatch.setattr(gom,'model_var_mi',lambda:False)
    coordinator.run_scan(con,path,str(root))
    sid=con.execute('SELECT seg_id FROM segments').fetchone()[0]
    con.execute('INSERT INTO embeddings VALUES (?,?,?,?)',(sid,embed.MODEL_VER,128,np.ones(128,dtype=np.float32).tobytes()));con.commit()
    monkeypatch.setattr(gom,'model_var_mi',lambda:True)
    class Model:
        def encode(self,texts,**kwargs):return np.ones((len(texts),embed.DIM),dtype=np.float32)/16
    monkeypatch.setattr(embed,'isit_oturumu',lambda:Model())
    result=coordinator.run_scan(con,path,str(root))
    assert result['complete'] and result['documents_done']==1 and result['embed_done']==1
    assert con.execute('SELECT dim,length(vec) FROM embeddings').fetchone()==(embed.DIM,4*embed.DIM)
    con.close()


def test_repeated_preparation_preserves_vectors_and_restores_only_missing_index():
    con = sqlite3.connect(':memory:'); migrate.ensure_current(con)
    fid = con.execute("INSERT INTO files(path,name,ext) VALUES ('c:/old.txt','old.txt','.txt')").lastrowid
    sid = con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'para','Belge','Sözleşme')", (fid,)).lastrowid
    vector = (np.ones(embed.DIM, dtype=np.float32)/16).tobytes()
    con.execute('INSERT INTO embeddings VALUES (?,?,?,?)', (sid,embed.MODEL_VER,embed.DIM,vector))
    con.execute('DROP INDEX idx_embeddings_ver'); con.commit()
    for _ in range(3): migrate.ensure_current(con)
    assert con.execute('SELECT vec FROM embeddings WHERE seg_id=?',(sid,)).fetchone()[0] == vector
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name='idx_embeddings_ver'").fetchone()
    con.close()


def test_scan_repairs_old_vault_and_really_extracts_and_embeds(tmp_path, monkeypatch):
    root=tmp_path/'source'; files(root,3)
    path=str(tmp_path/'vault.db'); password='synthetic-repair-1234'
    con=vault.open_vault(path,password); migrate.ensure_current(con)
    con.execute('DROP TABLE embeddings'); con.commit()
    monkeypatch.setattr(gom,'model_var_mi',lambda:True)
    class Model:
        def encode(self,texts,**kwargs):return np.ones((len(texts),embed.DIM),dtype=np.float32)/16
    monkeypatch.setattr(embed,'isit_oturumu',lambda:Model())
    result=coordinator.run_scan(con,path,str(root))
    assert result['complete'] and result['documents_done']==result['documents_total']==3
    assert con.execute('SELECT count(*) FROM embeddings WHERE model_ver=? AND dim=?',(embed.MODEL_VER,embed.DIM)).fetchone()[0] == 3
    assert con.execute("SELECT count(*) FROM docs_fts WHERE docs_fts MATCH 'sirnak'").fetchone()[0] == 3
    assert not con.execute("SELECT 1 FROM jobs WHERE status IN ('pending','running','dead')").fetchone()
    vectors=con.execute('SELECT seg_id,vec FROM embeddings ORDER BY seg_id').fetchall()
    repeated=coordinator.run_scan(con,path,str(root))
    assert repeated['complete'] and repeated['documents_done']==3 and repeated['done']==0
    assert con.execute('SELECT seg_id,vec FROM embeddings ORDER BY seg_id').fetchall() == vectors
    con.close()
