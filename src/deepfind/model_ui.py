"""Local model settings; work stays off the GUI thread."""
import threading
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtWidgets import (QComboBox, QPushButton, QDialog, QVBoxLayout,
                               QProgressBar, QCheckBox, QLabel)
from . import archive_ui, engine, migrate
from .theme import t
from .ui import bolum, label


def install(window, layout):
    layout.addWidget(bolum('Yerel anlamsal arama'))
    window.model_status = label('EmbeddingGemma 2 • hazırlanıyor', 'ikincil')
    window.model_status.setWordWrap(True)
    layout.addWidget(window.model_status)
    window.model_coverage = label('Vektör kapsamı tarama ilerledikçe tamamlanır.', 'ikincil')
    layout.addWidget(window.model_coverage)
    window.model_backend = QComboBox()
    for caption, value in [('Otomatik (CUDA / Vulkan / CPU)', 'auto'), ('Vulkan', 'vulkan'),
                            ('NVIDIA CUDA', 'cuda'), ('İşlemci (CPU)', 'cpu')]:
        window.model_backend.addItem(caption, value)
    saved = migrate.get_setting(window.con, 'embedding_backend', 'auto')
    window.model_backend.setCurrentIndex(max(0,window.model_backend.findData(saved)))
    engine.set_backend(window.model_backend.currentData())
    layout.addWidget(window.model_backend)
    window.model_retry = QPushButton(t('Motoru yeniden başlat'))
    layout.addWidget(window.model_retry)
    detail = label('Model kurulumla gelir. İnternet veya API anahtarı olmadan arar. '
                   'CPU, Vulkan ve CUDA motorları kurulumun içindedir.', 'ikincil')
    detail.setWordWrap(True)
    layout.addWidget(detail)
    def restart():
        if window.con is None: return
        backend = window.model_backend.currentData()
        migrate.set_setting(window.con, 'embedding_backend', backend)
        def work(_):
            engine.set_backend(backend)
            engine.isit_oturumu(cancel=lambda: window._locked or window._exiting)
            return engine.status()
        archive_ui.job(window, 'model_start', work, lambda _: refresh())
    def refresh():
        if window._locked: return
        state = engine.status()
        text = f"EmbeddingGemma 2 • {state['state']}"
        if state['backend']: text += ' • ' + state['backend'].upper()
        if state.get('device'): text += '\n' + state['device']
        if state['error']: text += '\n' + state['error']
        window.model_status.setText(text)
        if getattr(window, '_waiting_for_model', False) and engine.hazir_oturum() is not None:
            window._waiting_for_model = False
            window._ara_simdi()
    window.model_retry.clicked.connect(restart)
    window.model_backend.currentIndexChanged.connect(restart)
    from . import model_indir as _mi
    if _mi.gerekli_mi():
        window.model_indir_btn = QPushButton(t("Anlamsal arama modelini indir (~296 MB)"))
        window.model_indir_btn.clicked.connect(lambda: indir_penceresi(window))
        layout.addWidget(window.model_indir_btn)
    window.model_timer = QTimer(window)
    window.model_timer.timeout.connect(refresh)
    window.model_timer.start(1000)


def refresh_coverage(window):
    def operation(con):
        done = con.execute('SELECT count(*) FROM embeddings WHERE model_ver=?',(engine.MODEL_VER,)).fetchone()[0]
        total = con.execute("SELECT count(*) FROM segments WHERE kind NOT IN ('name_only','context')").fetchone()[0]
        return done,total
    def ready(value):
        done,total=value
        window.model_coverage.setText(f'Anlamsal indeks: {done}/{total} bölüm. Eksikler sonraki taramada tamamlanır.')
    archive_ui.job(window,'model_coverage',operation,ready)


class _IndirmeIsci(QObject):
    ilerleme = Signal(int, int)
    bitti = Signal(str)
    hata = Signal(str)

    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)
        self._dur = threading.Event()

    def iptal(self):
        self._dur.set()

    def calistir(self):
        from . import model_indir as _mi
        from . import engine as _e
        try:
            yol = _mi.indir(_mi.MODEL_URL, _mi.MODEL_SHA256, str(_e.user_model_path()),
                            ilerleme=lambda d, t: self.ilerleme.emit(d, t),
                            cancel=self._dur.is_set)
            self.bitti.emit(yol)
        except InterruptedError:
            self.hata.emit(t("İndirme iptal edildi."))
        except Exception as exc:
            self.hata.emit(f'{t("İndirme tamamlanamadı.")} {exc}')


def indir_penceresi(ebeveyn):
    """Model indirme penceresi: amac, boyut, lisans, ilerleme, iptal, yeniden deneme."""
    from . import model_indir as _mi
    from PySide6.QtWidgets import QThread
    from .theme import app_icon
    pencere = QDialog(ebeveyn)
    pencere.setWindowTitle(t("Anlamsal arama modelini indir (~296 MB)"))
    pencere.setWindowIcon(app_icon())
    pencere.setMinimumWidth(460)
    k = QVBoxLayout(pencere)
    k.addWidget(label(t("Model, çevrimdışı aramanın çalışması için gerekir; bir kez indirilir."), "ikincil"))
    lisans = QCheckBox(t("Model lisansını (Apache-2.0) kabul ediyorum"))
    k.addWidget(lisans)
    durum = QLabel(t("Model hazır.") if not _mi.gerekli_mi() else "")
    durum.setWordWrap(True)
    k.addWidget(durum)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    k.addWidget(bar)
    baslat = QPushButton(t("İndirmeyi başlat"))
    iptal = QPushButton(t("İptal"))
    yinele = QPushButton(t("Yeniden dene"))
    kapat = QPushButton(t("Kapat"))
    for dugme in (baslat, iptal, yinele, kapat):
        k.addWidget(dugme)
    yinele.hide()
    isci = _IndirmeIsci()
    kanal = QThread(pencere)
    isci.moveToThread(kanal)
    kanal.started.connect(isci.calistir)
    isci.ilerleme.connect(lambda d, to: (bar.setRange(0, 100),
                                         bar.setValue(int(d * 100 / to)) if to else bar.setRange(0, 0),
                                         durum.setText(t("Model indiriliyor…"))))
    def _tamam(yol):
        kanal.quit()
        bar.setValue(100)
        durum.setText(t("Model indirildi ve doğrulandı."))
        baslat.hide(); iptal.hide(); yinele.hide()
    def _bozuk(mesaj):
        kanal.quit()
        durum.setText(mesaj)
        baslat.hide(); iptal.hide(); yinele.show()
    isci.bitti.connect(_tamam)
    isci.hata.connect(_bozuk)
    baslat.clicked.connect(lambda: (lisans.setEnabled(False), baslat.setEnabled(False),
                                    durum.setText(t("Model indiriliyor…")), kanal.start()) if lisans.isChecked()
                           else durum.setText(t("Model lisansını (Apache-2.0) kabul ediyorum")))
    iptal.clicked.connect(lambda: isci.iptal())
    yinele.clicked.connect(lambda: (yinele.hide(), baslat.setEnabled(False),
                                    durum.setText(t("Model indiriliyor…")),
                                    kanal.start() if kanal.isFinished() else None))
    kapat.clicked.connect(lambda: (isci.iptal(), kanal.quit(), kanal.wait(3000), pencere.accept()))
    if not _mi.gerekli_mi():
        baslat.hide(); iptal.hide()
    else:
        baslat.setEnabled(True)
    lisans.toggled.connect(lambda acik: baslat.setEnabled(acik) if _mi.gerekli_mi() else None)
    baslat.setEnabled(False)
    pencere.exec()
