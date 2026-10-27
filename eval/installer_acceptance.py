"""Real isolated Inno upgrade, missing/corrupt model and cleanup acceptance.

Never runs against the user's installed AppId, vault or shortcuts. Test setup
uses the exact production file lists/code with a separate AppId, local model
location, lowest privileges and uncompressed payload for quick acceptance.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import shutil
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from deepfind.installer import windows_file_version
from deepfind.model_indir import MODEL_SHA256
from deepfind.version import __version__


def main():
    target=(ROOT/'build'/('installed-acceptance-'+uuid.uuid4().hex)).resolve()
    iscc=os.environ.get('INNO_ISCC',r'C:\tmp\Inno\ISCC.exe')
    log=ROOT/'build/installer-acceptance.log'
    result={}
    with log.open('w',encoding='utf-8') as output:
        def compile_setup(*defines):
            subprocess.run([iscc,'/DTestInstall',*defines,str(ROOT/'packaging/DeepFind.iss')],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=300)
        def install(version, success=True):
            setup=ROOT/'build/test-installer'/f'DeepFind-{version}.exe'
            assert windows_file_version(setup)==tuple(map(int,version.split('.')))
            run = subprocess.run([str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS',f'/DIR={target}'],timeout=300)
            assert (run.returncode == 0) == success, run.returncode
        compile_setup('/DTestPrevious')
        install('0.10.4')
        assert (target/'DeepFind-0.10.4.exe').is_file()
        assert (target/'_internal/rapidfuzz').is_dir()
        # The small package must refuse before replacing any app file.
        compile_setup('/DUpdatePackage')
        install(__version__, success=False)
        assert (target/'DeepFind-0.10.4.exe').is_file()
        assert not (target/f'DeepFind-{__version__}.exe').exists()
        result['missing_model_blocks_before_upgrade']=True
        legacy=target/'legacy-model/embeddinggemma-2-Q8_0.gguf'
        legacy.parent.mkdir()
        shutil.copyfile(ROOT/'build/embedding/embeddinggemma-2-Q8_0.gguf',legacy)
        sentinel=target/'owner-document.txt'; sentinel.write_text('preserve',encoding='utf-8')
        unknown=target/'DeepFind-0.1.0.exe'; unknown.write_bytes(b'not-a-managed-exe')
        install(__version__)
        assert windows_file_version(target/f'DeepFind-{__version__}.exe')==tuple(map(int,__version__.split('.')))
        model=target/'_internal/embedding/embeddinggemma-2-Q8_0.gguf'
        with model.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==MODEL_SHA256
        before=model.stat().st_mtime_ns
        assert not legacy.exists()
        assert not (target/'DeepFind-0.10.4.exe').exists()
        assert not (target/'DeepFind-0.10.4.bat').exists()
        assert not (target/'_internal/rapidfuzz').exists()
        result['obsolete_keyword_runtime_removed']=True
        assert sentinel.read_text(encoding='utf-8')=='preserve' and unknown.is_file()
        result['legacy_model_moved_and_old_launchers_removed']=True
        install(__version__)
        assert model.stat().st_mtime_ns==before
        result['incremental_keeps_model']=True
        # A full installer repairs corruption and also cleans a 0.10.2 launcher.
        shutil.copyfile(ROOT/'dist/DeepFind-0.10.2/DeepFind-0.10.2.exe',target/'DeepFind-0.10.2.exe')
        shutil.copyfile(ROOT/'dist/DeepFind-0.10.2/DeepFind-0.10.2.bat',target/'DeepFind-0.10.2.bat')
        model.write_bytes(b'corrupt')
        compile_setup()
        install(__version__)
        with model.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==MODEL_SHA256
        assert not (target/'DeepFind-0.10.2.exe').exists()
        assert not (target/'DeepFind-0.10.2.bat').exists()
        result['full_setup_repairs_model_and_cleans_0_10_2']=True
        smoke=target/'acceptance-smoke.json'
        subprocess.run([str(target/f'DeepFind-{__version__}.exe'),'--package-smoke',str(smoke)],check=True,timeout=300)
        report=json.loads(smoke.read_text(encoding='utf-8'))
        assert report['ok'] and 'real-semantic-search' in report['checks']
        result['installed_runtime_smoke']=report
        subprocess.run([str(target/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=120)
        assert not (target/f'DeepFind-{__version__}.exe').exists()
        assert not model.exists()
        assert sentinel.is_file() and unknown.is_file()
        result['uninstall_removes_program_model_preserves_unknown_files']=True
    (ROOT/f'build/installer-acceptance-{__version__}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:val for key,val in result.items() if key!='installed_runtime_smoke'}),flush=True)


if __name__=='__main__':main()
