"""Real isolated Inno 0.9->0.10->incremental reinstall; separate test AppId.

Never runs against the user's installed AppId, vault or shortcuts. Test setup
uses the exact production file lists/code with a separate AppId, local model
location, lowest privileges and uncompressed payload for quick acceptance.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from evrakci.installer import windows_file_version
from evrakci.model_indir import MODEL_SHA256


def main():
    target=(ROOT/'build'/('installed-acceptance-'+uuid.uuid4().hex)).resolve()
    iscc=os.environ.get('INNO_ISCC',r'C:\tmp\Inno\ISCC.exe')
    log=ROOT/'build/installer-acceptance.log'
    result={}
    with log.open('w',encoding='utf-8') as output:
        def compile_setup(*defines):
            subprocess.run([iscc,'/DTestInstall',*defines,str(ROOT/'packaging/Evrakci.iss')],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=300)
        def install(version):
            setup=ROOT/'build/test-installer'/f'Evrakçı-{version}.exe'
            assert windows_file_version(setup)==tuple(map(int,version.split('.')))
            subprocess.run([str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS',f'/DIR={target}'],check=True,timeout=300)
        compile_setup('/DTestPrevious')
        install('0.9.0')
        assert (target/'Evrakçı-0.9.0.exe').is_file()
        compile_setup()
        install('0.10.0')
        assert windows_file_version(target/'Evrakçı-0.10.0.exe')==(0,10,0)
        model=target/'_internal/embedding/embeddinggemma-2-Q8_0.gguf'
        with model.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==MODEL_SHA256
        before=model.stat().st_mtime_ns
        result['upgrade_0_9_to_0_10']=True
        compile_setup('/DUpdatePackage')
        install('0.10.0')
        assert model.stat().st_mtime_ns==before
        result['incremental_keeps_model']=True
        smoke=target/'acceptance-smoke.json'
        subprocess.run([str(target/'Evrakçı-0.10.0.exe'),'--package-smoke',str(smoke)],check=True,timeout=300)
        report=json.loads(smoke.read_text(encoding='utf-8'))
        assert report['ok'] and 'real-semantic-search' in report['checks']
        result['installed_runtime_smoke']=report
        subprocess.run([str(target/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=120)
        assert not (target/'Evrakçı-0.10.0.exe').exists()
        assert model.is_file()  # Explicit shared/model preservation contract.
        result['uninstall_preserves_model']=True
    (ROOT/'build/installer-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:val for key,val in result.items() if key!='installed_runtime_smoke'}),flush=True)


if __name__=='__main__':main()
