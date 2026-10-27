"""Synthetic layout matrix; scale-factor simulation is not a physical DPI session."""
import os, sys, tempfile, importlib.util, json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('ui_tests',ROOT/'tests/test_ui.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from PySide6.QtCore import Qt
from deepfind import theme
out=ROOT/'build'/'review-015';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='deepfind-015-') as tmp:
    from PySide6.QtGui import QFont, QFontDatabase
    app=m._app();QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf");app.setFont(QFont("Segoe UI",10))
    fixture=m.pencere.__wrapped__(Path(tmp));pen=next(fixture);pen.show()
    paths=['D:\\', 'E:\\', 'G:\\', 'P:\\']
    for path in paths:
        pen.con.execute('INSERT INTO roots(display_path,canonical_path) VALUES (?,?)',(path,path.lower()))
    pen.con.commit();pen._kok_tazele()
    records=[]
    for size in [(1280,720),(1920,1080)]:
        pen.resize(*size)
        for mode in ('acik','koyu'):
            theme.apply(app,mode)
            for page in (1,5):
                pen.nav.setCurrentRow(page)
                for _ in range(6): app.processEvents()
                if page==1: assert pen.source_split.orientation()==Qt.Horizontal
                name=f'{size[0]}-{mode}-{page}-{os.environ.get("QT_SCALE_FACTOR","1")}'
                pen.grab().save(str(out/(name+'.png')))
                records.append(name)
            pen._nav_toggle()
            for _ in range(6):app.processEvents()
            assert pen.nav.horizontalScrollBar().maximum()==0
            pen.grab().save(str(out/f'{size[0]}-{mode}-dar-{os.environ.get("QT_SCALE_FACTOR","1")}.png'))
            pen._nav_toggle()
    pen._scan_state('running')
    pen.tarama_bilgi.setText('Tarama sürüyor…')
    pen._scan_progress({'stage':'İçerik işleniyor','path':'D:/Arşiv/Finans/2026/Uzun klasör adı/rapor.pdf','found':1586,'done':1202,'pending':384,'failed':2,'ocr_done':48})
    pen.popup_scope.setText('5 kaynak • D:\\ | E:\\ | G:\\ | P:\\ | Sentetik arşiv')
    pen._scan_show()
    for _ in range(6):app.processEvents()
    pen.scan_dialog.grab().save(str(out/f'popup-{os.environ.get("QT_SCALE_FACTOR","1")}.png'))
    pen._scan_state('idle');pen.scan_dialog.hide()
    pen.resize(1100,720);pen.nav.setCurrentRow(1)
    for _ in range(8):app.processEvents()
    assert pen.source_split.orientation()==Qt.Vertical
    (out/f'layout-{os.environ.get("QT_SCALE_FACTOR","1")}.json').write_text(json.dumps({'screens':records,'narrow_vertical':True,'scale':os.environ.get('QT_SCALE_FACTOR','1'),'physical_dpi_verified':False},indent=2),encoding='utf-8')
    try:next(fixture)
    except StopIteration:pass
