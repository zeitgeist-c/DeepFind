import os
import time
import numpy as np
from evrakci import coordinator as C, job_queue as q, vault, migrate
from evrakci.scan_progress import DocumentProgress
from test_scan_resume import database


def files(root, count):
    root.mkdir()
    for i in range(count):
        p=root/f'{i}.txt';p.write_text('Şırnak sözleşme',encoding='utf-8')
        os.utime(p,(time.time()-10,time.time()-10))


def test_inventory_completes_before_any_source_content_is_read(tmp_path, monkeypatch):
    root=tmp_path/'source';files(root,40)
    con=database(tmp_path/'vault.db')
    original=C._process_job
    counts=[]
    def checked(con, *args, **kwargs):
        counts.append(con.execute('SELECT count(*) FROM scan_manifest').fetchone()[0])
        return original(con,*args,**kwargs)
    monkeypatch.setattr(C,'_process_job',checked)
    result=C.run_scan(con,str(tmp_path/'vault.db'),str(root), require_vectors=False)
    assert counts and set(counts)=={40}
    assert result['documents_total']==40 and result['documents_done']==40
    con.close()


def test_worker_counts_all_roots_once_and_reuses_snapshot(tmp_path, monkeypatch):
    from evrakci.app import TaramaIsci
    from evrakci import gom,embed
    from semantic_helpers import FixedSession
    monkeypatch.setattr(gom,'model_var_mi',lambda:True)
    monkeypatch.setattr(embed,'isit_oturumu',lambda **kwargs:FixedSession())
    roots=[tmp_path/'first',tmp_path/'second'];files(roots[0],2);files(roots[1],3)
    path=str(tmp_path/'vault.db');password='synthetic-counted-scan-1234'
    con=vault.open_vault(path,password);migrate.ensure_current(con);con.close()
    worker=TaramaIsci(path,password,list(map(str,roots)))
    walks=[];scandir=os.scandir
    def listed(path):
        if str(path) in list(map(str,roots)):walks.append(str(path))
        return scandir(path)
    monkeypatch.setattr(os,'scandir',listed)
    original_scan=C.run_scan;original_process=C._process_job
    def scan(*args,**kwargs):
        kwargs['guarded']=False
        return original_scan(*args,**kwargs)
    seen=[]
    def process(con,*args,**kwargs):
        assert worker._document_total==5
        assert con.execute('SELECT count(*) FROM scan_manifest').fetchone()[0]==5
        seen.append(1)
        return original_process(con,*args,**kwargs)
    monkeypatch.setattr(C,'run_scan',scan);monkeypatch.setattr(C,'_process_job',process)
    results=[];errors=[];worker.bitti.connect(results.append);worker.hata.connect(errors.append)
    worker.kos()
    assert not errors and len(seen)==5
    assert results[0]['documents_total']==5 and results[0]['documents_done']==5
    assert worker.snapshot()['documents_total']==5
    assert sorted(walks)==sorted(map(str,roots))
    con=vault.open_vault(path,password)
    assert con.execute('SELECT count(*) FROM scan_manifest').fetchone()[0]==0
    assert con.execute('SELECT count(*) FROM scan_runs WHERE finished_at IS NULL').fetchone()[0]==0
    con.close()


def test_inventory_cancel_never_reads_content_or_reports_known_total(tmp_path,monkeypatch):
    from evrakci.app import TaramaIsci
    root=tmp_path/'source';files(root,30)
    path=str(tmp_path/'vault.db');password='synthetic-cancel-1234'
    con=vault.open_vault(path,password);migrate.ensure_current(con);con.close()
    worker=TaramaIsci(path,password,[str(root)])
    original=C.note_discovered
    calls=[]
    def note(*args,**kwargs):
        result=original(*args,**kwargs);calls.append(1)
        if len(calls)==5:worker.durdur()
        return result
    def forbidden(*a,**k):raise AssertionError('content started during inventory')
    monkeypatch.setattr(C,'note_discovered',note);monkeypatch.setattr(C,'_process_job',forbidden)
    results=[];errors=[];worker.bitti.connect(results.append);worker.hata.connect(errors.append)
    worker.kos()
    assert not errors and results[0]['result']=='cancelled'
    assert not results[0]['inventory_ready'] and len(calls)==5
    assert len(list(root.glob('*.txt')))==30


def test_document_is_not_complete_while_ocr_or_embedding_is_missing():
    from evrakci.embed import MODEL_VER
    con=database()
    fid=con.execute("INSERT INTO files(path,name,ext,index_status) VALUES ('c:/x','x','.pdf','ok')").lastrowid
    sid=con.execute("INSERT INTO segments(file_id,kind,label,raw_text) VALUES (?,'body','Sayfa','test')",(fid,)).lastrowid
    rid=con.execute("INSERT INTO scan_runs(root,started_at) VALUES ('c:/',0)").lastrowid
    con.execute('INSERT INTO scan_manifest VALUES (?,?,1,1)',(rid,fid));con.commit()
    progress=DocumentProgress(con,rid,True)
    assert progress.done==0
    con.execute('INSERT INTO embeddings VALUES (?,?,?,?)',(sid,MODEL_VER,256,(np.ones(256,dtype=np.float32)/16).tobytes()))
    q.enqueue(con,fid,'1:1','ocr');con.commit();progress.refresh(fid)
    assert progress.done==0
    con.execute('DELETE FROM jobs');con.commit();progress.refresh(fid)
    assert progress.done==1 and progress.total==1
    q.enqueue(con,fid,'1:1','embed');con.execute("UPDATE jobs SET status='dead'");con.commit()
    progress.refresh(fid);assert progress.done==0
    con.close()


def test_pause_time_is_excluded_from_phase_eta(monkeypatch):
    from types import SimpleNamespace
    from evrakci import app
    clock=[100.0];monkeypatch.setattr(app,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    worker=app.TaramaIsci('synthetic.db','synthetic',[])
    worker.report_progress({'phase_key':'content','phase_done':1,'phase_total':10},{})
    clock[0]=110;worker._pause_started=110
    clock[0]=210;assert worker.snapshot()['phase_elapsed']==10
    worker._paused_seconds=100;worker._pause_started=None
    clock[0]=220;assert worker.snapshot()['phase_elapsed']==20


def test_multi_window_document_is_counted_once(tmp_path, monkeypatch):
    from evrakci import extract
    root=tmp_path/'source';files(root,1)
    con=database(tmp_path/'vault.db');cursors=[]
    def window(path,ext,size,cursor=0):
        cursors.append(cursor)
        return extract.ExtractResult([extract.Segment('para',None,'Parça',f'Sözleşme bölüm {cursor}')],
                                    next_cursor=cursor+1 if cursor<2 else None)
    monkeypatch.setattr(extract,'extract_window',window)
    events=[];result=C.run_scan(con,str(tmp_path/'vault.db'),str(root),progress=events.append, require_vectors=False)
    assert cursors==[0,1,2]
    assert result['documents_done']==1 and result['documents_total']==1
    assert all(e['phase_done']<=1 for e in events if e.get('phase_key')=='content')
    con.close()


def test_inaccessible_folder_never_claims_complete_inventory(tmp_path,monkeypatch):
    root=tmp_path/'source';files(root,2);files(root/'blocked',1)
    original=os.scandir
    def denied(path):
        if str(path)==str(root/'blocked'):raise PermissionError('synthetic denial')
        return original(path)
    monkeypatch.setattr(os,'scandir',denied)
    con=database(tmp_path/'vault.db')
    result=C.run_scan(con,str(tmp_path/'vault.db'),str(root), require_vectors=False)
    assert result['found']==2 and not result['inventory_complete'] and not result['complete']
    con.close()
