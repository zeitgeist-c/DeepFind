"""Behavioral regressions for independent semantic retrieval and local-only runtime."""
import json
import threading
import numpy as np
import pytest
from evrakci import engine, rank, migrate, model_indir, update
from test_hibrit import _kasa, _duzen, _kodla_b, _dosya, _vektor


def test_semantic_without_keyword_match(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        assert not rank.search_semantic(con, 'evcil hayvan')['results']
        rows = rank.search_semantic(con,'evcil hayvan',kodla=_kodla_b)['results']
        assert rows and rows[0]['name'] == 'b_belge.txt'
        assert rows[0]['score_class'] == 'semantic'
    finally: con.close()


def test_filters_applied_to_vector_candidates(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        assert not rank.search_semantic(con,'evcil hayvan',ext='.pdf',kodla=_kodla_b)['results']
        assert not rank.search_semantic(con,'evcil hayvan',folder='forbidden',kodla=_kodla_b)['results']
        assert not rank.search_semantic(con,'evcil hayvan',year=2021,kodla=_kodla_b)['results']
        assert not rank.search_semantic(con,'evcil hayvan',tag='private',kodla=_kodla_b)['results']
        fid = con.execute("SELECT file_id FROM files WHERE name='b_belge.txt'").fetchone()[0]
        rank.tags_many(con,[fid],'private')
        rows=rank.search_semantic(con,'evcil hayvan',tag='private',kodla=_kodla_b)['results']
        assert [r['file_id'] for r in rows] == [fid]
    finally: con.close()


def test_merge_precedes_pagination(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        _dosya(con,'c_belge.txt','hayvan oyuncakları')
        _vektor(con,'oyuncakları',1)
        first=rank.search_semantic(con,'kedi',limit=1,kodla=_kodla_b)
        second=rank.search_semantic(con,'kedi',limit=1,offset=1,kodla=_kodla_b)
        whole=rank.search_semantic(con,'kedi',limit=50,kodla=_kodla_b)
        assert first['has_more']
        assert [first['results'][0]['file_id'],second['results'][0]['file_id']] == [r['file_id'] for r in whole['results'][:2]]
        assert len({r['file_id'] for r in whole['results']}) == len(whole['results'])
    finally: con.close()


def test_quotes_and_exclusions_use_semantic_search(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        for query in ['"evcil hayvan"', 'kedi -tasması']:
            a=rank.search_semantic(con,query,kodla=_kodla_b)
            assert a['results'] and a['semantic']
    finally: con.close()


def test_broken_encoder_reports_unavailable(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        bad=lambda _: np.full((1,256),np.nan)
        r=rank.search_semantic(con,'kedi',kodla=bad)
        assert not r['results'] and r['semantic_error']
    finally: con.close()


def test_old_vectors_never_mixed_with_new_model(tmp_path):
    con = _kasa(tmp_path); _duzen(con)
    try:
        con.execute("UPDATE embeddings SET model_ver='eg2-text-256-v1'"); con.commit()
        assert not rank.search_semantic(con,'evcil hayvan',kodla=_kodla_b)['results']
    finally: con.close()


def test_token_chunks_cover_tail_and_repeat_task_prefix():
    session=object.__new__(engine.Oturum); session._kilit=threading.RLock()
    seen=[]
    def request(path,data):
        if path=='/tokenize': return {'tokens':[9001,9002] if data['add_special'] else list(range(1500))}
        seen.append(data['input'])
        v=np.zeros(768); v[0]=1
        return [{'embedding':[v.tolist()]}]
    session.request=request
    v=session.encode(['long text'])
    assert v.shape==(1,256) and np.isfinite(v).all()
    assert all(part[:2]==[9001,9002] and len(part)<=512 for part in seen)
    assert set(range(1500))=={t for part in seen for t in part[2:]}


def test_removed_cloud_settings_cleanup_is_idempotent(tmp_path):
    con=_kasa(tmp_path)
    try:
        migrate.set_setting(con,'gemini_api_key','synthetic-key')
        migrate.set_setting(con,'ai_model','old')
        migrate.set_setting(con,'tema','koyu')
        migrate.ensure_current(con); migrate.ensure_current(con)
        assert not migrate.get_setting(con,'gemini_api_key')
        assert not migrate.get_setting(con,'ai_model')
        assert migrate.get_setting(con,'tema')=='koyu'
    finally: con.close()


def test_installer_asset_preferred_and_digest_required():
    sha='a'*64
    payload={'tag_name':'v0.10.0','assets':[
        {'name':'Evrakci-0.10.0.zip','digest':'sha256:'+sha},
        {'name':'Evrakci-0.10.0.exe','digest':'sha256:'+sha}]}
    assert update.parse_release(payload).asset_name.endswith('.exe')
    payload['assets'][1]['digest']=''
    with pytest.raises(update.UpdateError):update.parse_release(payload)


def test_nonfinite_and_zero_vectors_rejected():
    for value in [np.zeros(256), np.full(256,np.inf)]:
        with pytest.raises(ValueError): engine.normalize(value)


def test_installer_handoff_uses_managed_path(tmp_path,monkeypatch):
    from evrakci import installer
    updates=tmp_path/'Updates'; updates.mkdir()
    setup=updates/'Evrakçı-0.10.0.exe'; setup.write_bytes(b'synthetic')
    current=tmp_path/'installed'/'Evrakçı-0.9.0.exe'; current.parent.mkdir()
    (current.parent/'unins000.exe').write_bytes(b'synthetic')
    calls=[]
    monkeypatch.setattr(installer,'windows_file_version',lambda _:(0,10,0))
    monkeypatch.setattr(installer.subprocess,'Popen',lambda *a,**k:calls.append((a,k)))
    script=installer.spawn_installer(123,setup,current,str(tmp_path/'vault with spaces.db'))
    assert script.parent==updates
    text=script.read_text(encoding='utf-8-sig')
    assert 'Wait-Process -Id 123' in text and 'ExitCode -ne 0' in text
    assert '/DIR=' in text and str(current.parent) in text
    assert calls and '-File' in calls[0][0][0]


@pytest.mark.parametrize('extra,model_sha,success',[(False,None,True),(True,None,False),(False,'wrong',False)])
def test_incremental_package_validates_contents(tmp_path,monkeypatch,extra,model_sha,success):
    import zipfile,hashlib
    archive=tmp_path/'source.evrakci'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('Evrakçı-0.10.0.exe',b'synthetic-exe')
        z.writestr('manifest.json',json.dumps({'program':'Evrakçı','version':'0.10.0','model_sha256':model_sha or model_indir.MODEL_SHA256}))
        if extra:z.writestr('../escape',b'bad')
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    info=update.UpdateInfo('0.10.0','Evrakçı-0.10.0.evrakci',archive.as_uri(),sha,archive.stat().st_size,'')
    monkeypatch.setattr(model_indir,'paylasilan_hazir',lambda:True)
    monkeypatch.setattr(update,'windows_file_version',lambda _:(0,10,0))
    dest=tmp_path/'Updates'; dest.mkdir()
    if success:
        result=update.prepare_incremental(info,dest)
        assert result.read_bytes()==b'synthetic-exe'
    else:
        with pytest.raises(update.UpdateError):update.prepare_incremental(info,dest)
        assert not (dest/'Evrakçı-0.10.0.exe').exists()
    assert not (dest/'Evrakçı-0.10.0.evrakci').exists()


def test_invalid_vectors_do_not_replace_previous_index(tmp_path):
    from evrakci import gom
    con=_kasa(tmp_path); _duzen(con)
    try:
        before=con.execute('SELECT * FROM embeddings ORDER BY seg_id').fetchall()
        sid=before[0][0]
        with pytest.raises(ValueError):gom.vektor_yaz(con,[(sid,'text')],np.full((1,256),np.nan))
        assert con.execute('SELECT * FROM embeddings ORDER BY seg_id').fetchall()==before
    finally:con.close()


def test_embedding_cancel_preserves_pending_job(tmp_path):
    from evrakci import gom,job_queue
    con=_kasa(tmp_path);_duzen(con)
    try:
        fid=con.execute('SELECT min(file_id) FROM files').fetchone()[0]
        job_queue.enqueue(con,fid,'10:20',kind='embed');con.commit()
        job=job_queue.claim(con,('embed',))
        def cancelled(_):raise InterruptedError('cancelled')
        with pytest.raises(InterruptedError):gom.process_embed_job(con,job,kodla=cancelled)
        assert con.execute('SELECT attempts FROM jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]==0
    finally:con.close()


def test_closed_window_cannot_start_model(monkeypatch):
    def unexpected(*a,**k):raise AssertionError('native process must not start')
    monkeypatch.setattr(engine,'Oturum',unexpected)
    assert engine.isit_oturumu(cancel=lambda:True) is None
