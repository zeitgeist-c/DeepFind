import os, sys, tempfile, importlib.util, time, json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('ui_tests',ROOT/'tests/test_ui.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
app=m._app()
with tempfile.TemporaryDirectory(prefix='deepfind-native-015-') as tmp:
    fixture=m.pencere.__wrapped__(Path(tmp));pen=next(fixture)
    pen.setWindowTitle('DeepFind 0.1.5 • Sentetik görsel doğrulama')
    pen.show();pen.nav.setCurrentRow(2);pen._scan_state('running')
    pen.tarama_bilgi.setText('Tarama sürüyor…')
    pen.scan_started=__import__('datetime').datetime.now();pen._scan_elapsed=time.monotonic()
    pen._scan_progress({'stage':'İçerik işleniyor','path':'D:/Sentetik/rapor.pdf','found':100,'done':60,'pending':40})
    pen.tarama_bar.show();pen._scan_show()
    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000,pen.scan_dialog.hide)
    QTimer.singleShot(2500,pen.hide)
    QTimer.singleShot(7000,lambda:pen._scan_state('paused'))
    QTimer.singleShot(9000,lambda:pen._scan_state('idle'))
    deadline=time.monotonic()+10
    keys=set()
    captures=0
    while time.monotonic()<deadline:
        app.processEvents();time.sleep(.04)
        if pen.tepsi:
            keys.add(pen.tepsi.icon().cacheKey())
            rect=pen.tepsi.geometry()
            if not rect.isEmpty() and captures < 8 and pen._scan_status == 'running':
                screen=app.screenAt(rect.center())
                if screen:
                    image=screen.grabWindow(0,rect.x(),rect.y(),rect.width(),rect.height())
                    image.save(str(ROOT/'build'/f'tray-native-015-{captures}.png'))
                    captures+=1
    report={'platform':app.platformName(),'system_tray_available':bool(pen.tepsi),'observed_icon_keys':len(keys),'timer_stopped_at_idle':not pen._tray_timer.isActive() if pen.tepsi else None,'tray_screen_captures':captures,'physical_dpi':app.primaryScreen().logicalDotsPerInch()}
    (ROOT/'build/native-015.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    try:next(fixture)
    except StopIteration:pass
