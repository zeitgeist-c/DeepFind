"""Reproducible synthetic latency/visual acceptance; never opens user vaults."""
import json,os,platform,sqlite3,statistics,tempfile,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from deepfind import schema,migrate,rank,vault,theme
from deepfind.vocab import ensure_v5

def pump(app,predicate=lambda:False,seconds=30):
    deadline=time.monotonic()+seconds
    while predicate():
        app.processEvents(); time.sleep(.005)
        if time.monotonic()>deadline: raise TimeoutError('UI completion timeout')
    app.processEvents()

def main():
    from deepfind.version import __version__
    output=Path('build/archive'+__version__.replace('.','')); output.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(':memory:'); schema.ensure_schema(con); ensure_v5(con); migrate.ensure_current(con)
    count=10000
    con.executemany("INSERT INTO files(file_id,path,name,ext,index_status) VALUES (?,?,?,'.pdf','ok')",[(i,f'C:/synthetic/{i:05}.pdf',f'{i}.pdf') for i in range(1,count+1)])
    con.executemany('INSERT INTO segments(file_id,kind,page,label,raw_text) VALUES (?,\'pdf_page\',1,\'Sayfa 1\',?)',[(i,f'tahsilat makbuzu evrak {i}') for i in range(1,count+1)]); con.commit()
    durations=[]
    for i in range(30):
        start=time.perf_counter(); result=rank.search_ranked(con,'tahsilat makbuzu'); durations.append((time.perf_counter()-start)*1000)
        assert len(result['results'])==50
    specific=rank.search_ranked(con,'tahsilat 9999')['results']; assert specific and specific[0]['name']=='9999.pdf'
    p95=sorted(durations)[int(len(durations)*.95)-1]
    from PySide6.QtWidgets import QApplication
    from deepfind.app import AnaPencere
    app=QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    with tempfile.TemporaryDirectory(prefix='deepfind-034-eval-') as directory:
        db=str(Path(directory)/'index.db'); password='synthetic-eval-034-1234'
        encrypted=vault.open_vault(db,password); migrate.ensure_current(encrypted)
        encrypted.execute("INSERT INTO files(path,name,ext,index_status) VALUES ('C:/synthetic/12345.pdf','12345.pdf','.pdf','ok')")
        encrypted.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) VALUES (1,'pdf_page',1,'Sayfa 1','Tahsilat makbuzu 54321: 18750 TL')"); encrypted.commit(); encrypted.close()
        window=AnaPencere(db,password); window.show(); app.processEvents()
        for mode in ('acik','koyu'):
            for width,height in ((1500,1000),(1050,760)):
                theme.apply(app,mode); window.resize(width,height); window.nav.setCurrentRow(0); app.processEvents()
                from deepfind.archive_ui import layout_cards
                layout_cards(window); app.processEvents()
                for page,name in ((0,'ara'),(1,'ai'),(6,'ayarlar')):
                    window.nav.setCurrentRow(page); pump(app,lambda:bool(window._jobs))
                    window.grab().save(str(output/f'{mode}-{width}-{name}.png'))
        timings=[]
        for _ in range(20):
            for tab in (0,1,3,4,5):
                start=time.perf_counter(); window.nav.setCurrentRow(tab); app.processEvents(); timings.append((time.perf_counter()-start)*1000)
        pump(app,lambda:bool(window._jobs))
        source=Path(directory)/'source'; source.mkdir()
        from openpyxl import Workbook
        for n in range(3):
            book=Workbook()
            for r in range(150): book.active.append([f'tarama evrak {n} satır {r}'])
            path=source/f'{n}.xlsx'; book.save(path); os.utime(path,(time.time()-10,time.time()-10))
        window.con.execute('INSERT INTO roots(display_path,canonical_path) VALUES (?,?)',(str(source),str(source).lower())); window.con.commit()
        window._tara_baslat(); active_timings=[]
        for _ in range(20):
            for tab in (0,1,3,4,5):
                start=time.perf_counter(); window.nav.setCurrentRow(tab); app.processEvents(); active_timings.append((time.perf_counter()-start)*1000)
        pump(app,lambda:window.isci_thread is not None,seconds=60)
        pump(app,lambda:bool(window._jobs))
        window.nav.setCurrentRow(5); pump(app,lambda:bool(window._jobs)); assert window.file_model.rowCount()==4
        window.file_list.setCurrentIndex(window.file_model.index(0,0)); window._file_open(); pump(app,window.onizleme.busy)
        assert '54321' in window.onizleme._fallback
        window.preview_dialog.close(); window._cikis(); pump(app,lambda:bool(window._jobs) or window.onizleme.busy())
    con.close()
    report=dict(machine=platform.platform(),python=platform.python_version(),documents=count,segments=count,
        search_runs=len(durations),search_p95_ms=round(p95,2),search_target_pass=p95<=2000,
        tab_transitions=len(timings),tab_p95_ms=round(sorted(timings)[94],2),tab_max_ms=round(max(timings),2),tab_target_pass=max(timings)<=250,
        active_scan_tab_transitions=len(active_timings),active_scan_tab_max_ms=round(max(active_timings),2),active_scan_tab_target_pass=max(active_timings)<=250,
        corpus='synthetic; not workplace archive',screenshots=[p.name for p in output.glob('*.png')])
    (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False)); assert report['search_target_pass'] and report['tab_target_pass'] and report['active_scan_tab_target_pass']

if __name__=='__main__': main()
