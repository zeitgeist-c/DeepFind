"""Local model settings; work stays off the GUI thread."""
import threading
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QPushButton
from . import archive_ui, engine, migrate
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
    window.model_retry = QPushButton('Motoru yeniden başlat')
    layout.addWidget(window.model_retry)
    window.cuda_install = QPushButton('NVIDIA CUDA bileşenini indir (yaklaşık 663 MB)')
    layout.addWidget(window.cuda_install)
    detail = label('Model kurulumla gelir. İnternet veya API anahtarı olmadan arar. '
                   'CUDA isteğe bağlıdır; Vulkan ve CPU kurulumun içindedir.', 'ikincil')
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
    def download():
        window.cuda_install.setEnabled(False)
        window.cuda_install.setText('CUDA indiriliyor ve doğrulanıyor…')
        def work(_):
            from .model_indir import install_cuda
            stop = window._job_keys['cuda_install'].stop
            install_cuda(cancel=stop.is_set)
            return True
        def done(_):
            window.cuda_install.setText('CUDA hazır')
            window.cuda_install.setEnabled(True)
            restart()
        def failed(error):
            window.cuda_install.setText('CUDA indirmesi tamamlanamadı; yeniden dene')
            window.cuda_install.setEnabled(True)
            window.model_status.setText(error)
        archive_ui.job(window, 'cuda_install', work, done, failed=failed)
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
    window.cuda_install.clicked.connect(download)
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
