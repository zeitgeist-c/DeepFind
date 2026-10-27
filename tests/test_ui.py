"""A7 arayuz testleri (offscreen): tema, sihirbaz, arama, onizleme, kilit."""
import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from evrakci import coordinator, migrate, rank, schema, theme, vault  # noqa: E402
from evrakci.preview import Onizleme  # noqa: E402
from evrakci.migrate import ensure_v5  # noqa: E402
from evrakci.migrate import ensure_v7  # noqa: E402

PW = "arayuz-sifresi-1234"
APP = None


def _app():
    global APP
    if APP is None:
        APP = QApplication.instance() or QApplication([])
    return APP


def _wait_search(pen):
    deadline = time.monotonic() + 10
    while pen._search_thread is not None or pen._pending_search is not None:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline, "arama zaman aşımı"


def _wait_preview(preview):
    deadline = time.monotonic() + 20
    while preview.busy():
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline

def _pdf(kok, ad, metin, sayfalar=1):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("TR")
    except KeyError:
        pdfmetrics.registerFont(TTFont("TR", "C:/Windows/Fonts/arial.ttf"))
    p = os.path.join(kok, ad)
    c = canvas.Canvas(p)
    c.setFont("TR", 13)
    for i in range(max(1, sayfalar)):
        if i:
            c.showPage()
            c.setFont("TR", 13)
        c.drawString(72, 750, f"{metin} {i + 1}")
    c.save()
    return p


@pytest.fixture()
def pencere(tmp_path, monkeypatch):
    _app()
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "belge.pdf", "Ankara arayüz testi 2024 vergi levhası")
    time.sleep(2.5)
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?, ?)",
                (kok, os.path.normpath(kok).lower()))
    con.commit()
    coordinator.run_scan(con, db, kok, require_vectors=False)
    from semantic_helpers import seed_vectors,FixedSession
    from evrakci import embed
    seed_vectors(con)
    monkeypatch.setattr(embed,'hazir_oturum',lambda:FixedSession())
    con.close()
    from evrakci.app import AnaPencere
    pen = AnaPencere(db, PW)
    yield pen
    try:
        if pen.con is not None:
            vault.lock(pen.con, os.path.dirname(db))
    except Exception:
        pass
    pen._thumblari_durdur()
    pen._exiting = True
    pen.close()
    deadline = time.monotonic() + 20
    while pen._search_thread is not None or pen.isci_thread is not None or pen.onizleme.busy() or pen._jobs:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline
    pen.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def _wait_jobs(window):
    deadline=time.time()+15
    while window._jobs and time.time()<deadline:
        _app().processEvents()
        time.sleep(0.01)
    _app().processEvents()
    assert not window._jobs


def test_guncelleme_bolumu_kaynak_kopyada(pencere):
    """Kaynak koddan çalışırken güncelleme denetimi kapalı, açıklama görünür."""
    assert pencere.settings_page.isAncestorOf(pencere.update_durum)
    assert pencere.settings_page.isAncestorOf(pencere.update_bar)
    assert pencere.update_denetle_btn.isHidden()          # kaynak kopya: denetim yok
    assert pencere.update_indir_btn.isHidden()
    assert pencere.update_iptal_btn.isHidden()
    assert pencere.update_bar.isHidden()
    assert "kaynak koddan" in pencere.update_durum.text()
    # Tehlikeli iş yapılmadı: sessiz/kendiliğinden indirme yok.
    assert pencere._guncelleme_info is None


def test_tema_uc_mod(pencere):
    _app()
    assert theme.apply(_app(), "acik") == "acik"
    assert theme.apply(_app(), "koyu") == "koyu"
    assert theme.resolve("sistem", True) == "koyu"
    assert theme.resolve("sistem", False) == "acik"


def test_arama_sonuc_ve_onizleme(pencere, tmp_path):
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    idx = pencere.sonuc_model.index(0, 0)
    pencere._sec(idx)
    _wait_preview(pencere.onizleme)
    assert pencere.onizleme.baslik.text() == "belge.pdf"
    assert "Sayfa" in pencere.onizleme.bilgi.text()


def test_bos_sorgu_tum_arsivi_listelemez(pencere):
    pencere.arama_kutu.setText("")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() == 0


def test_model_ready_retries_waiting_query(pencere,monkeypatch):
    from evrakci import engine
    from semantic_helpers import FixedSession
    pencere.arama_kutu.setText('bakım sözleşmeleri')
    pencere._waiting_for_model=True
    monkeypatch.setattr(engine,'hazir_oturum',lambda:FixedSession())
    pencere.model_timer.timeout.emit()
    _wait_search(pencere)
    assert not pencere._waiting_for_model
    assert pencere.sonuc_model.rowCount()==1


def _wait_thumbs(pencere):
    deadline = time.monotonic() + 60
    while pencere._thumb_loader is not None or pencere._buyuk_loader is not None:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline, "küçük resim zaman aşımı"


def test_kucuk_resim_liste_ve_detay_panelinde(pencere, tmp_path, monkeypatch):
    """Arama sonucu satırında ve seçili evrak panelinde küçük resim oluşur."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from evrakci import thumbs
    dizin = str(tmp_path / "thumbs")
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: dizin)
    os.makedirs(dizin, exist_ok=True)
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    _wait_thumbs(pencere)
    veri = pencere.sonuc_model.index(0, 0).data(Qt.DecorationRole)
    assert isinstance(veri, QPixmap) and not veri.isNull()
    assert os.listdir(dizin), "önbellek dizini boş kaldı"

    # Seçim değişince büyük önizleme de dolmalı.
    pencere.sonuc_liste.setCurrentIndex(pencere.sonuc_model.index(0, 0))
    pencere._secim_guncelle()
    _wait_thumbs(pencere)
    goruntu = pencere.secim_gorsel.pixmap()
    assert goruntu is not None and not goruntu.isNull()
    # Düzen kuralı: kutu alttaki başlıkla çakışmaz (sabit yükseklik taşması yok).
    assert pencere.secim_gorsel.geometry().bottom() <= pencere.secim_ad.geometry().top()
    assert pencere.secim_gorsel.geometry().width() > 0


def _onizleme_pencere(pencere, tmp_path, monkeypatch, sayfalar=1, ad="cok-sayfali.pdf"):
    """Kasa köküne çok sayfalı PDF ekler, tarar ve bağımsız Onizleme açar."""
    from evrakci import thumbs
    kok = os.path.join(os.path.dirname(pencere.kasa_yolu), "arsiv")
    yol = _pdf(kok, ad, "Ankara çok sayfa", sayfalar=sayfalar)
    time.sleep(3.0)
    coordinator.run_scan(pencere.con, pencere.kasa_yolu, kok, require_vectors=False)
    dizin = str(tmp_path / "thumbs")
    os.makedirs(dizin, exist_ok=True)
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: dizin)
    con = vault.open_vault(pencere.kasa_yolu, PW)
    o = Onizleme()
    o.resize(900, 700)
    o.show()
    _app().processEvents()
    o.goster(con, {"path": yol, "name": ad, "ext": ".pdf", "label": "Sayfa 1",
                   "page": 1, "snippet": "Arama özeti", "why": ["ad"]})
    _wait_preview(o)
    _app().processEvents()
    return o, con


def _ikinci_belge(pencere):
    """Kasa köküne ikinci PDF'yi ekler ve indekslenene kadar tarar."""
    kok = os.path.join(os.path.dirname(pencere.kasa_yolu), "arsiv")
    yol = _pdf(kok, "ikinci-belge.pdf", "Ankara ikinci evrak 2024")
    time.sleep(3.0)
    # Tarayıcı yeni dosyayı kararlılık penceresi geçene kadar "pending" tutar.
    for _ in range(4):
        coordinator.run_scan(pencere.con, pencere.kasa_yolu, kok, require_vectors=False)
        if pencere.con.execute(
                "SELECT count(*) FROM files WHERE index_status='ok'").fetchone()[0] >= 2:
            break
        time.sleep(1.0)
    from semantic_helpers import seed_vectors
    seed_vectors(pencere.con)
    return yol


def _onizleme_kapat(o, con):
    o.temizle()
    deadline = time.monotonic() + 20
    while o.busy() and time.monotonic() < deadline:
        _app().processEvents()
        time.sleep(0.01)
    con.close()
    o.close()
    o.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_onizleme_zoom_kademeleri(pencere, tmp_path, monkeypatch):
    """Sığdırma kademeleri sayfayı görünür alana oturtur, yüzde kademesi büyütür."""
    o, con = _onizleme_pencere(pencere, tmp_path, monkeypatch, sayfalar=1)
    try:
        def otur():
            """Sığdırma yeniden hesapları bitene kadar olay çevrimini işle."""
            son = time.monotonic() + 30
            while (o.busy() or o._fit_timer.isActive()) and time.monotonic() < son:
                _app().processEvents()
                time.sleep(0.01)
            _app().processEvents()

        assert o.zoom_sec.count() == 8
        assert o.zoom_sec.currentData() == "genislik"
        otur()
        vp = o.canvas.viewport().size()
        pm = o.goruntu.pixmap()
        assert pm is not None and not pm.isNull()
        # Genişliğe sığdır: sayfa genişliği görünür alana oturur (ray görününce
        # tuval daralır ve sığdırma tazelenir).
        assert vp.width() - 34 <= pm.width() <= vp.width() + 4
        # Sayfaya sığdır: yükseklik de görünür alana oturur.
        o._zoom_ayarla("sayfa")
        otur()
        pm2 = o.goruntu.pixmap()
        assert pm2.height() <= vp.height() and pm2.height() >= vp.height() - 30
        # %200: sığdırmadan belirgin biçimde büyük.
        o._zoom_ayarla(2.0)
        otur()
        pm3 = o.goruntu.pixmap()
        assert pm3.width() > pm2.width() * 2
        # + düğmesi kademe adımlar: sığdırma modundan %100'e geçer.
        o._zoom_ayarla("genislik")
        o._zoom_adim(1)
        assert o.zoom_sec.currentData() == 1.0
        o._zoom_adim(1)
        assert o.zoom_sec.currentData() == 1.25
        o._zoom_adim(-1)
        assert o.zoom_sec.currentData() == 1.0
    finally:
        _onizleme_kapat(o, con)


def test_onizleme_sayfa_rayi_ve_klavye(pencere, tmp_path, monkeypatch):
    """Sayfa rayı küçük resimleri tembel üretir; ray ve klavye sayfa değiştirir."""
    o, con = _onizleme_pencere(pencere, tmp_path, monkeypatch, sayfalar=5)
    try:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        assert o.ray.isVisible() and o.ray.count() == 5
        deadline = time.monotonic() + 90
        while o._ray_loader is not None and time.monotonic() < deadline:
            _app().processEvents(); time.sleep(0.01)
        _app().processEvents()
        assert all(not o.ray.item(i).icon().isNull() for i in range(5))
        # Raydan sayfa seçimi.
        o._ray_secildi(o.ray.item(2))
        _wait_preview(o)
        assert o.sayfa_no.value() == 3 and o.ray.currentRow() == 2
        # Klavye: sağ ok ilerler, sol ok geri döner.
        o.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier))
        _wait_preview(o)
        assert o.sayfa_no.value() == 4
        o.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.NoModifier))
        _wait_preview(o)
        assert o.sayfa_no.value() == 3
        # Klavye: +/- kademe adımları, 0 %100'e döner.
        o._zoom_ayarla(2.0)
        _wait_preview(o)
        o.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Minus, Qt.NoModifier))
        assert o.zoom_sec.currentData() == 1.5
        o.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Plus, Qt.NoModifier))
        assert o.zoom_sec.currentData() == 2.0
        o.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_0, Qt.NoModifier))
        assert o.zoom_sec.currentData() == 1.0
        # Son sayfada ileri gitmek taşmaz.
        o._git(99)
        _wait_preview(o)
        assert o.sayfa_no.value() == 5
    finally:
        _onizleme_kapat(o, con)


def test_onizleme_indeks_metni_geri_doner(pencere, tmp_path, monkeypatch):
    """İndeks metni görünümü aynı düğmeyle sayfa görüntüsüne döner."""
    o, con = _onizleme_pencere(pencere, tmp_path, monkeypatch, sayfalar=1)
    try:
        o._show_index()
        assert o._index_view and o.metin.isVisible() and not o.canvas.isVisible()
        assert o.index_button.text() == "Sayfa görüntüsüne dön"
        o._show_index()
        assert not o._index_view and o.canvas.isVisible() and not o.metin.isVisible()
        assert o.index_button.text() == "İndeks metnini göster"
    finally:
        _onizleme_kapat(o, con)


def _cipler(pencere):
    return [pencere.filtre_cipleri.itemAt(i).widget()
            for i in range(pencere.filtre_cipleri.count())]


def test_filtre_cipleri_kaldirir_ve_yeniden_arar(pencere):
    """Aktif filtreler çip olur; çipin × düğmesi filtreyi düşürüp aramayı yeniler."""
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere.yil_filtre.setText("2024")
    pencere.tur_filtre.setCurrentIndex(pencere.tur_filtre.findText(".pdf"))
    _wait_search(pencere)
    assert pencere.filtre_sayi.text() == "2"
    cipler = _cipler(pencere)
    assert len(cipler) == 2
    assert "Yıl: 2024" in cipler[0].etiket.text()
    # Eski çipler görünür kalmamalı: pencere altında yalnız aktif çipler bulunur.
    from evrakci.ui import Cip
    assert len(pencere.findChildren(Cip)) == len(cipler)
    # Yıl çipini kaldır: filtre düşer, arama yeniden koşar.
    cipler = _cipler(pencere)
    # Yıl çipini kaldır: filtre düşer, arama yeniden koşar.
    cipler[0].kaldir.click()
    _wait_search(pencere)
    assert pencere.yil_filtre.text() == ""
    assert len(_cipler(pencere)) == 1
    assert len(pencere.findChildren(Cip)) == 1
    assert pencere.filtre_sayi.text() == "1"
    assert pencere.sonuc_model.rowCount() >= 1
    # Sıfırlama tüm filtreleri temizler.
    pencere._filtre_temizle()
    _wait_search(pencere)
    assert pencere.tur_filtre.currentText() == "tümü"
    assert _cipler(pencere) == []
    assert not pencere.filtre_sifirla.isVisible()


def test_gorunum_modu_kalicidir_ve_izgara(pencere):
    """Görünüm modu kalıcıdır; ızgara modunda ızgara yüzeyi etkinleşir."""
    from evrakci.ui import CardDelegate
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    assert pencere.sonuc_panel.currentIndex() == 0
    assert pencere.gorunum_btnleri["satir"].isChecked()
    pencere._gorunum_ayarla("izgara")
    assert migrate.get_setting(pencere.con, "gorunum_modu") == "izgara"
    assert pencere.sonuc_panel.currentIndex() == 1
    _app().processEvents()
    assert pencere.sonuc_izgara.isVisible()
    assert not pencere.goster_btn.isEnabled()  # alan seçimi ızgarada anlamlı değil
    # Kayıtlı ayar yeniden yüklendiğinde mod korunur.
    migrate.set_setting(pencere.con, "gorunum_modu", "izgara")
    pencere._gorunum = "satir"
    pencere._gorunum_uygula()
    assert pencere.sonuc_panel.currentIndex() == 0
    pencere._gorunum_yukle()
    assert pencere._gorunum == "izgara" and pencere.sonuc_panel.currentIndex() == 1
    assert pencere.gorunum_btnleri["izgara"].isChecked()
    # Kompakt mod kısa satır kullanır; satır modu daha yüksek.
    pencere._gorunum_ayarla("kompakt")
    assert pencere.sonuc_liste.itemDelegate().compact
    assert pencere.sonuc_panel.currentIndex() == 0
    assert pencere.sonuc_liste.itemDelegate()._satir_yuksekligi() == 56
    assert (pencere.sonuc_liste.itemDelegate()._satir_yuksekligi()
            < CardDelegate(pencere.sonuc_liste, thumb=True)._satir_yuksekligi())


def test_goster_alanlari_satiri_ve_ayari_etkiler(pencere):
    """Gösterilecek alanlar satır metnini değiştirir ve kasada saklanır."""
    from PySide6.QtCore import Qt
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    tam = pencere.sonuc_model.index(0, 0).data(Qt.DisplayRole)
    assert len(tam.splitlines()) >= 3
    full_path = pencere.sonuclar[0]["path"]
    assert full_path in tam  # gerçek fixture yolu görünür
    assert all(a.isChecked() for a in pencere.goster_menu.actions())
    # Yolu kapat: satırdan düşer, ayar saklanır, ipucunda yol kalır.
    pencere._alan_degistir("yol", False)
    assert migrate.get_setting(pencere.con, "goster_alanlari") == "tur,ozet,etiket"
    kisa = pencere.sonuc_model.index(0, 0).data(Qt.DisplayRole)
    assert full_path not in kisa
    assert len(kisa.splitlines()) == len(tam.splitlines()) - 1
    assert full_path in pencere.sonuc_model.index(0, 0).data(Qt.ToolTipRole)
    durum = {a.text(): a.isChecked() for a in pencere.goster_menu.actions()}
    assert durum == {"Yol": False, "Tür ve etiket": True,
                     "İçerik özeti": True, "Etiketler": True}
    # Tümü kapanırsa yalnız ad kalır (boş ayar "hepsi" sayılmaz).
    for anahtar in ("tur", "ozet", "etiket"):
        pencere._alan_degistir(anahtar, False)
    assert migrate.get_setting(pencere.con, "goster_alanlari") == ""
    assert pencere.sonuc_model.index(0, 0).data(Qt.DisplayRole).splitlines() == \
        [pencere.sonuclar[0]["name"]]
    assert not any(a.isChecked() for a in pencere.goster_menu.actions())
    # Alan geri açıldığında satıra döner.
    pencere._alan_degistir("yol", True)
    assert migrate.get_setting(pencere.con, "goster_alanlari") == "yol"
    assert full_path in pencere.sonuc_model.index(0, 0).data(Qt.DisplayRole)


def test_toplu_secim_etiket_ve_csv(pencere, tmp_path, monkeypatch):
    """Seçim denetimleri, toplu etiket (tek işlem) ve seçim CSV'si çalışır."""
    from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
    _ikinci_belge(pencere)
    pencere.show()
    pencere.arama_kutu.setText("Ankara")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() == 2
    assert not pencere.toplu_etiket_btn.isEnabled()  # seçim yokken kapalı
    # Tümünü seç: sayaç ve toplu düğmeler etkinleşir.
    pencere._secim_ayarla(-1)
    assert pencere.secim_sayac.text() == "2 seçili"
    assert pencere.toplu_etiket_btn.isEnabled() and pencere.toplu_csv_btn.isEnabled()
    assert len(pencere._secili_idler()) == 2
    # Sayfa seçimi ilk 50 sonuçla sınırlıdır.
    pencere._secim_ayarla(50)
    assert pencere.secim_sayac.text() == "2 seçili"
    # Hiçbiri: seçim ve düğmeler kapanır.
    pencere._secim_ayarla(0)
    assert pencere.secim_sayac.text() == "" and not pencere.toplu_csv_btn.isEnabled()
    # Toplu etiket ekleme: tek işlem, iki belgeye de yazılır.
    pencere._secim_ayarla(-1)
    uyarilar = []
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Vergi 2024", True))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: uyarilar.append(a))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    pencere._toplu_etiket()
    _wait_jobs(pencere)
    _wait_search(pencere)
    assert uyarilar == []
    for satir in pencere.sonuclar:
        assert "vergi 2024" in rank.file_tags(pencere.con, satir["file_id"])
    # Toplu etiket kaldırma.
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("vergi 2024", True))
    pencere._secim_ayarla(-1)
    pencere._toplu_etiket(kaldir=True)
    _wait_jobs(pencere)
    _wait_search(pencere)
    assert uyarilar == []
    for satir in pencere.sonuclar:
        assert "vergi 2024" not in rank.file_tags(pencere.con, satir["file_id"])
    # Seçim CSV'si: yalnız seçili satır yazılır.
    hedef = tmp_path / "secili.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(hedef), "CSV (*.csv)"))
    pencere._secim_ayarla(1)
    pencere._toplu_csv()
    satirlar = hedef.read_text(encoding="utf-8-sig").strip().splitlines()
    assert len(satirlar) == 2  # başlık + 1 seçili sonuç
    assert pencere.sonuclar[0]["name"] in satirlar[1]


def test_sorgu_sozdizimi_alanlari_uygular(pencere):
    """`alan:değer` sorgusu filtre denetimlerini besler ve çip olur."""
    pencere.show()
    pencere.arama_kutu.setText("Ankara yil:2024 tur:pdf")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert not pencere.sorgu_uyari.isVisible()
    assert pencere.yil_filtre.text() == "2024"
    assert pencere.tur_filtre.currentText() == ".pdf"
    assert pencere.sonuc_model.rowCount() >= 1
    assert len(_cipler(pencere)) == 2
    # Alan adı içermeyen sorgu eskisi gibi serbest metin arar.
    pencere.yil_filtre.clear()
    pencere.tur_filtre.setCurrentIndex(pencere.tur_filtre.findText("tümü"))
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    assert _cipler(pencere) == []
    # Yalnız alan verilirse liste boş kalır, kullanıcı yönlendirilir.
    pencere.arama_kutu.setText("etiket:vergi")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() == 0
    assert "bir sözcük de yazın" in pencere.oneri.text()
    assert len(_cipler(pencere)) == 1


def test_sorgu_hatasi_arama_calistirmaz_ve_imlec_gosterir(pencere):
    """Hatalı alanda arama koşmaz; eski sonuçlar korunur, imleç gösterilir."""
    pencere.show()
    pencere.arama_kutu.setText("Ankara vergi levhası")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    onceki = pencere.sonuc_model.rowCount()
    pencere.arama_kutu.setText("Ankara turl:pdf")
    pencere._ara_simdi()
    _app().processEvents()
    assert pencere.sorgu_uyari.isVisible()
    assert "bilinmeyen alan" in pencere.sorgu_uyari.text()
    assert "^" in pencere.sorgu_uyari.text()
    assert pencere._search_thread is None
    assert pencere.sonuc_model.rowCount() == onceki
    # Düzeltilince uyarı kaybolur ve arama yeniden koşar.
    pencere.arama_kutu.setText("Ankara tur:pdf")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert not pencere.sorgu_uyari.isVisible()
    assert pencere.tur_filtre.currentText() == ".pdf"
    assert pencere.sonuc_model.rowCount() >= 1


def test_onizleme_onceki_sonraki_belge(pencere, tmp_path, monkeypatch):
    """Önizlemedeki belge gezinmesi arama sonuçları içinde sıralı ilerler."""
    from evrakci import thumbs
    _ikinci_belge(pencere)
    dizin = str(tmp_path / "thumbs")
    os.makedirs(dizin, exist_ok=True)
    monkeypatch.setattr(thumbs, "onbellek_dizini", lambda: dizin)
    pencere.show()
    pencere.arama_kutu.setText("Ankara")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 2
    pencere.sonuc_liste.setCurrentIndex(pencere.sonuc_model.index(0, 0))
    pencere._secim_guncelle()
    pencere._open_preview(pencere.sonuclar[0])
    _wait_preview(pencere.onizleme)
    assert pencere.preview_konum.text() == f"1 / {pencere.sonuc_model.rowCount()}"
    assert not pencere.preview_once.isEnabled() and pencere.preview_sonra.isEnabled()
    pencere._onizleme_komsu(1)
    _wait_preview(pencere.onizleme)
    assert pencere.onizleme.baslik.text() == pencere.sonuclar[1]["name"]
    assert pencere.preview_konum.text().startswith("2 /")
    assert pencere.preview_once.isEnabled()
    pencere._onizleme_komsu(-1)
    _wait_preview(pencere.onizleme)
    assert pencere.preview_konum.text().startswith("1 /")
    _wait_thumbs(pencere)
    pencere.preview_dialog.close()



def test_sihirbaz_sayfa_ve_sifre_kurali():
    _app()
    from evrakci.wizard import Sihirbaz
    s = Sihirbaz()
    assert s.pageIds() and len(s.pageIds()) == 5
    s.restart()
    s.next()  # sifre sayfasi (page 1)
    s.s1.setText("kisa")
    s.s2.setText("kisa")
    assert s.validateCurrentPage() is False
    s.s1.setText("uzun-sifre-1234")
    s.s2.setText("uzun-sifre-1234")
    assert s.validateCurrentPage() is True
    s.close()
    s.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_sihirbaz_ekle_secili_klasor_yenile_ve_kaldir(tmp_path):
    _app()
    from evrakci.wizard import Sihirbaz
    from PySide6.QtWidgets import QWizard
    from PySide6.QtCore import QCoreApplication, QEvent
    s = Sihirbaz()
    root = tmp_path / "Belgeler"
    root.mkdir()
    idx = s.model.index(str(root))
    assert idx.isValid()
    s.agac.setCurrentIndex(idx)
    s.ekle.click()
    assert s.secim["kokler"] == [str(root)]
    assert s.kok_model.rowCount() == 1
    s.unc.setText(str(root) + os.sep)
    s.ekle.click()
    assert s.kok_model.rowCount() == 1
    assert "zaten" in s.kaynak_mesaj.text()
    old_model = s.model
    s.yenile.click()
    assert s.model is not old_model
    assert s.kok_model.rowCount() == 1
    s.kok_liste.setCurrentIndex(s.kok_model.index(0, 0))
    s._kaldir()
    assert s.secim["kokler"] == []
    s.unc.setText(str(tmp_path / "yok"))
    s.ekle.click()
    assert "ulaşılamıyor" in s.kaynak_mesaj.text()
    file = tmp_path / "bir-dosya.txt"
    file.write_text("sentetik")
    s.unc.setText(str(file))
    s.ekle.click()
    assert s.secim["kokler"] == []
    assert s.buttonText(QWizard.NextButton) == "İleri"
    assert s.buttonText(QWizard.BackButton) == "Geri"
    assert not s.windowIcon().isNull()
    assert s.agac.isHeaderHidden()
    assert "Diske/loga" not in s.page(1).subTitle()
    s.close()
    s.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_kilit_model_temizler(pencere, tmp_path, monkeypatch):
    pencere.arama_kutu.setText("Ankara")
    pencere._ara_simdi()
    _wait_search(pencere)
    assert pencere.sonuc_model.rowCount() >= 1
    # kilit diyalogunu atla: QInputDialog reddetsin -> pencere kapanir
    from PySide6.QtWidgets import QInputDialog
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    pencere.kilitle()
    assert pencere.con is None
    assert pencere.sonuc_model.rowCount() == 0


def test_pdf_onizleme_sayfa_render(pencere):
    _app()
    o = Onizleme()
    con = vault.open_vault(pencere.kasa_yolu, PW)
    try:
        row = con.execute("SELECT path FROM files").fetchone()
        class SegmentSorgusunuYasakla:
            def execute(self, sql, args=()):
                assert "segments" not in sql.lower(), "PDF seçimi arayüzde indeks taraması yaptı"
                return con.execute(sql, args)

        o.show()
        o.goster(SegmentSorgusunuYasakla(),
                 {"path": row[0], "name": "belge.pdf", "ext": ".pdf",
                  "label": "Sayfa 1", "page": 1, "snippet": "Arama özeti", "why": ["ad"]})
        assert o.yukleme.isVisible()
        assert o.yukleme_cubugu.minimum() == o.yukleme_cubugu.maximum() == 0
        _wait_preview(o)
        assert o.goruntu.pixmap() is not None and not o.goruntu.pixmap().isNull()
        assert not o.yukleme.isVisible()

        o.goster(SegmentSorgusunuYasakla(),
                 {"path": row[0] + ".yok", "name": "yok.pdf", "ext": ".pdf",
                  "label": "Sayfa 1", "page": 1, "snippet": "Arama özeti", "why": ["ad"]})
        assert o.yukleme.isVisible()
        _wait_preview(o)
        assert not o.yukleme.isVisible()
        assert o.metin.toPlainText() == "Arama özeti"
        assert "açılamadı" in o.uyari.text()
    finally:
        con.close()
        o.close()
        o.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_oturum_kilit_filtresi_uykuda_kilitler():
    _app()
    from evrakci.app import OturumKilitFiltresi
    import ctypes
    from ctypes import wintypes
    cagrildi = []
    f = OturumKilitFiltresi(lambda: cagrildi.append(1))
    msg = wintypes.MSG()
    msg.message = OturumKilitFiltresi.WM_POWERBROADCAST
    msg.wParam = OturumKilitFiltresi.PBT_APMSUSPEND
    tuketildi, _kod = f.nativeEventFilter(b"windows_generic",
                                          int(ctypes.addressof(msg)))
    assert tuketildi and cagrildi == [1]
    msg2 = wintypes.MSG()
    msg2.message = 0x0042  # ilgisiz mesaj
    tuketildi2, _k2 = f.nativeEventFilter(b"windows_generic",
                                          int(ctypes.addressof(msg2)))
    assert not tuketildi2 and cagrildi == [1]


def test_tarama_isci_eszamanli_kosar(tmp_path):
    _app()
    from evrakci.app import TaramaIsci
    kok = str(tmp_path / "arsiv")
    os.makedirs(kok)
    _pdf(kok, "is.pdf", "Ankara işçi testi 2024")
    time.sleep(2.5)
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.close()
    isci = TaramaIsci(db, PW, [kok])
    sonuc, hata = [], []
    isci.bitti.connect(sonuc.append)
    isci.hata.connect(hata.append)
    isci.kos()
    assert not hata, hata
    assert sonuc and sonuc[0].get("done", 0) >= 1, sonuc


def test_kok_kaldir_isci_surucu_koku_ve_koruma(tmp_path):
    """Kök kaldırma işçisi sürücü kökünü boşaltır, diğer kökleri korur."""
    from evrakci.app import KokKaldirIsci
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)", ("C:\\", os.path.normpath("C:\\").lower()))
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)", ("D:\\", os.path.normpath("D:\\").lower()))
    docs = (("C:\\a\\b.pdf", "SilinenBelge", 1),
            ("C:\\b\\c.pdf", "SilinenBelge", 1),
            ("D:\\x\\d.pdf", "DisDosya", 1))
    for p,text,freq in docs:
        con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)",(p,os.path.basename(p),".pdf"))
        fid=con.execute("SELECT file_id FROM files WHERE path=?",(p,)).fetchone()[0]
        con.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) VALUES (?,'text',1,'Sayfa 1',?)",(fid,text))
    from semantic_helpers import seed_vectors
    seed_vectors(con)
    con.commit()
    con.close()

    isci = KokKaldirIsci(db, PW, "C:\\")
    sonuc, hata = [], []
    isci.bitti.connect(sonuc.append)
    isci.hata.connect(hata.append)
    isci.kos()
    assert not hata, hata
    assert sonuc == [2]  # C:\ altındaki 2 dosya silindi

    con = vault.open_vault(db, PW)
    kalan = [p for (p,) in con.execute("SELECT path FROM files").fetchall()]
    assert kalan == ["D:\\x\\d.pdf"], kalan
    koklar = [r[0] for r in con.execute("SELECT display_path FROM roots").fetchall()]
    assert "C:\\" not in koklar and "D:\\" in koklar
    con.close()


def test_kok_kaldir_worker_gui_kilitlemez(tmp_path, monkeypatch):
    """Kök kaldırma QThread üzerinde çalışırken ana thread olay çevrimine yanıt verir."""
    from evrakci.app import KokKaldirIsci
    from PySide6.QtCore import QThread, QTimer
    original_open = vault.open_vault
    def slow_open(*args, **kwargs):
        time.sleep(.2)
        return original_open(*args, **kwargs)
    monkeypatch.setattr(vault,"open_vault",slow_open)
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path, canonical_path) VALUES (?,?)",
                ("Q:\\", "q:\\"))
    con.execute("INSERT INTO files(path, name, ext) VALUES (?,?,?)",
                ("Q:\\a\\b.pdf", "b.pdf", ".pdf"))
    con.commit()
    con.close()

    isci = KokKaldirIsci(db, PW, "Q:\\")
    th = QThread()
    isci.moveToThread(th)
    th.started.connect(isci.kos)
    biten = []
    isci.bitti.connect(lambda n: biten.append(n))
    isci.bitti.connect(th.quit)
    isci.bitti.connect(isci.deleteLater)
    hata = []
    isci.hata.connect(hata.append)
    th.start()
    _app()
    gui_pulse = []
    QTimer.singleShot(50, lambda: gui_pulse.append(True))
    # Worker sözlük yenilerken GUI timer'ı çalışmalı.
    deadline = time.monotonic() + 15
    while th.isRunning() and time.monotonic() < deadline:
        _app().processEvents()
        time.sleep(0.01)
    th.wait(2000)
    assert not hata, hata
    assert biten == [1], biten
    assert gui_pulse, "GUI olay çevrimi kaldırma sırasında yanıt vermedi"
    assert not th.isRunning()

    con = vault.open_vault(db, PW)
    assert con.execute("SELECT count(*) FROM files").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM roots WHERE display_path='Q:\\'").fetchone()[0] == 0
    con.close()




def test_haric_ui_islemi_arka_planda_ve_geri_acilir(pencere, monkeypatch):
    """Dışla işlemi UI'ı bloklamaz; tamamlanınca form yeniden etkinleşir."""
    from evrakci import exclusions
    original = exclusions.purge_rule
    def slow_purge(*args, **kwargs):
        time.sleep(0.2)
        return original(*args, **kwargs)
    monkeypatch.setattr(exclusions, "purge_rule", slow_purge)
    deadline = time.monotonic() + 20
    while (pencere._jobs or pencere._search_thread is not None or pencere.onizleme.busy()
           or pencere._debounce.isActive() or pencere.file_debounce.isActive()
          ):
        _app().processEvents(); time.sleep(.01)
        assert time.monotonic() < deadline
    assert pencere._exclusive_ready()
    rule = os.path.join(os.path.dirname(pencere.kasa_yolu), "haric-probe")
    os.makedirs(rule)
    pencere.haric_kutu.setText(rule)
    pencere._haric_ekle()
    assert pencere._haric_thread is not None
    assert not pencere.centralWidget().isEnabled()
    pulse = []
    from PySide6.QtCore import QTimer
    QTimer.singleShot(40, lambda: pulse.append(True))
    deadline = time.monotonic() + 10
    while pencere._haric_thread is not None:
        _app().processEvents(); time.sleep(.01)
        assert time.monotonic() < deadline
    assert pulse
    assert pencere.centralWidget().isEnabled()
    assert pencere.haric_uygula.isEnabled()
    assert pencere.haric_kutu.text() == ""
    assert rule in exclusions.list_rules(pencere.con)


def test_haric_isci_atomik_surucu_koku_temizligi(tmp_path):
    """Hariç worker sürücü kökünü temizler; file-name terimleri indeksli kalır."""
    from evrakci.app import HaricIsci
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con)
    ensure_v5(con)
    ensure_v7(con)
    con.execute("INSERT INTO roots(display_path,canonical_path) VALUES (?,?)", ("C:\\", "c:\\"))
    con.execute("INSERT INTO roots(display_path,canonical_path) VALUES (?,?)", ("D:\\", "d:\\"))
    for path, name, body in (("C:\\a\\namekeep.pdf", "NameKeep", "BodyRemove"),
                             ("C:\\b\\otherkeep.pdf", "OtherKeep", "BodyRemove"),
                             ("D:\\kept.pdf", "KeepName", "BodyRemove")):
        con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)", (path, name, ".pdf"))
        fid = con.execute("SELECT file_id FROM files WHERE path=?", (path,)).fetchone()[0]
        folded = body.lower()
        con.execute("INSERT INTO segments(file_id,kind,page,label,raw_text) VALUES (?,?,?,?,?)",
                    (fid,"text",1,"Sayfa 1",body))
    con.commit(); con.close()

    worker = HaricIsci(db, PW, "C:\\")
    done, errors = [], []
    worker.bitti.connect(lambda rule, count: done.append((rule, count)))
    worker.hata.connect(errors.append)
    worker.kos()
    assert not errors and done == [("C:\\", 2)]
    con = vault.open_vault(db, PW)
    assert con.execute("SELECT count(*) FROM segments").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM files WHERE index_status='excluded'").fetchone()[0] == 2
    con.close()


def test_haric_isci_hata_geri_alir_kural_ve_icerik(tmp_path, monkeypatch):
    """Hariç temizleme başarısızsa kural ve içerik birlikte geri alınır."""
    from evrakci.app import HaricIsci
    from evrakci import exclusions
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con); ensure_v5(con); ensure_v7(con)
    con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)", ("C:\\a.pdf","a.pdf",".pdf"))
    con.commit(); con.close()
    monkeypatch.setattr(exclusions, "purge_rule", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synthetic")))
    worker = HaricIsci(db, PW, "C:\\")
    done, errors = [], []
    worker.bitti.connect(lambda *_: done.append(True)); worker.hata.connect(errors.append)
    worker.kos()
    assert errors == ["RuntimeError"] and not done
    con = vault.open_vault(db, PW)
    assert con.execute("SELECT count(*) FROM exclusions").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM files").fetchone()[0] == 1
    con.close()


def test_haric_ve_kok_mutasyonlari_scan_kilidini_sayar(tmp_path):
    """Arka plan mutasyonu canlı tarama kilidi varken veriye dokunmaz."""
    from evrakci import coordinator, exclusions
    from evrakci.app import HaricIsci, KokKaldirIsci
    db = str(tmp_path / "k.db")
    con = vault.open_vault(db, PW)
    schema.ensure_schema(con); ensure_v5(con); ensure_v7(con)
    con.execute("INSERT INTO roots(display_path,canonical_path) VALUES (?,?)", ("C:\\", "c:\\"))
    con.execute("INSERT INTO files(path,name,ext) VALUES (?,?,?)", ("C:\\a.pdf","a.pdf",".pdf"))
    con.commit(); con.close()
    with coordinator.ScanLock(db):
        for worker in (KokKaldirIsci(db, PW, "C:\\"), HaricIsci(db, PW, "C:\\")):
            errors, done = [], []
            worker.hata.connect(errors.append)
            worker.bitti.connect(lambda *args: done.append(args))
            worker.kos()
            assert errors == ["AlreadyRunning"] and not done
    con = vault.open_vault(db, PW)
    assert con.execute("SELECT count(*) FROM files").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM roots").fetchone()[0] == 1
    assert exclusions.list_rules(con) == []
    con.close()


def test_kurulum_tema_ve_toplu_klasor_islemleri(tmp_path):
    from evrakci.wizard import Sihirbaz
    from PySide6.QtCore import QCoreApplication, QEvent
    s = Sihirbaz()
    try:
        for i in range(3):
            folder = tmp_path / str(i)
            folder.mkdir()
            s._ekle_yol(str(folder))
        s.tema.setCurrentIndex(2)
        assert _app().property('evrakci_theme') == 'koyu'
        s.kok_liste.selectAll()
        s._kaldir()
        assert not s.secim['kokler']
        s._ekle_yol(str(tmp_path / '0'))
        s._tumunu_kaldir()
        assert s.kok_model.rowCount() == 0
        assert all((tmp_path / str(i)).is_dir() for i in range(3))
    finally:
        s.close()
        s.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_dar_gezinme_kapsam_ve_hatirlanan_kilit(pencere, tmp_path, monkeypatch):
    from evrakci import remember
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    pencere._nav_toggle()
    assert pencere.rail.width() == 86 and pencere.nav.item(0).text() == ''
    assert pencere.nav.item(0).toolTip() == 'Ara'
    pencere._nav_toggle()
    assert pencere.nav.item(0).text() == 'Ara'
    pencere.scope_mode.setCurrentIndex(1)
    assert pencere.scope_sources.count() == 1
    remember.save(pencere.kasa_yolu, PW)
    pencere._otomatik_kilitle()
    assert not pencere._locked
    pencere.scan_log.appendPlainText('sentetik dosya yolu')
    pencere.kilitle()
    assert pencere._locked and not remember.enabled(pencere.kasa_yolu)
    assert not pencere.scan_log.toPlainText()

def test_015_popup_background_and_automatic(pencere, monkeypatch):
    from evrakci import app as app_module
    from PySide6.QtCore import Slot
    class SlowWorker(app_module.TaramaIsci):
        @Slot()
        def kos(self):
            while not self._dur.is_set():
                time.sleep(0.01)
            self.bitti.emit({'result': 'cancelled'})
    monkeypatch.setattr(app_module, 'TaramaIsci', SlowWorker)
    pencere.nav.setCurrentRow(1)
    pencere._tara_baslat(automatic=True)
    _app().processEvents()
    assert not pencere.scan_dialog.isVisible()
    assert pencere.nav.currentRow() == 1
    worker = pencere.isci
    pencere.tara_btn.click()
    assert pencere.isci is worker and pencere.scan_dialog.isVisible()
    pencere.scan_counts.setText('sentetik sayaç')
    pencere.scan_dialog.close()
    assert pencere.isci is worker and not pencere.scan_dialog.isVisible()
    pencere.tara_btn.click()
    assert pencere.scan_counts.text() == 'sentetik sayaç'
    pencere._tara_iptal()
    deadline = time.monotonic() + 5
    while pencere.isci_thread is not None:
        _app().processEvents()
        time.sleep(0.01)
        assert time.monotonic() < deadline
    assert pencere.tara_btn.text() == 'Şimdi tara'
    assert pencere.nav.item(2).text() == 'Tarama'


def test_015_time_source_and_layout(pencere, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *a: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: None)
    from evrakci import scheduler as sched
    monkeypatch.setattr(sched, "autostart_clear", lambda *a: None)
    from PySide6.QtCore import QTime, Qt
    from PySide6.QtWidgets import QPushButton
    for hour, minute in [(0, 0), (23, 59)]:
        pencere.scan_time_edit.setTime(QTime(hour, minute))
        pencere._ayar_kaydet()
        assert migrate.get_setting(pencere.con, 'saat') == str(hour)
        assert migrate.get_setting(pencere.con, 'dakika') == str(minute)
        assert pencere.tarama_time.text() == f'{hour:02}:{minute:02}'
    assert pencere.source_path.text() == pencere.kok_model.item(0).data()
    assert not any(b.text() == 'Hakkında' for b in pencere.findChildren(QPushButton))
    pencere.show()
    _app().processEvents()
    buttons = [b for b, _ in pencere.rail_actions]
    # Yeni ray düzeni: eylemler alt alta, daraltma düğmesinin altında.
    assert buttons[1].y() > buttons[0].y()
    assert pencere.rail_toggle.y() < buttons[0].y()
    assert all(b.width() >= b.fontMetrics().horizontalAdvance(b.text()) + 20 for b in buttons)
    pencere._nav_toggle()
    _app().processEvents()
    assert pencere.nav.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert pencere.nav.horizontalScrollBar().maximum() == 0


def test_015_pause_ack_and_tray_reset(pencere):
    from evrakci.app import TaramaIsci
    worker = TaramaIsci(pencere.kasa_yolu, PW, [])
    pencere.isci = worker
    pencere._tara_duraklat()
    assert pencere._scan_status == 'pausing'
    pencere._scan_paused(True)
    assert pencere._scan_status == 'paused'
    assert pencere.tara_btn.text() == 'Tarama duraklatıldı'
    pencere._tara_duraklat()
    assert pencere._scan_status == 'running'
    pencere._tara_iptal()
    pencere._scan_paused(False)
    assert pencere._scan_status == 'cancelling'
    pencere._scan_state('idle')
    if pencere.tepsi is not None:
        assert not pencere._tray_timer.isActive()
    pencere.isci = None
    assert len(theme.scan_icons()) == 8
    assert len({icon.cacheKey() for icon in theme.scan_icons()}) == 8

def test_015_lock_clears_dialog(pencere, monkeypatch):
    pencere._scan_show()
    pencere.popup_scope.setText('sentetik yol')
    pencere.scan_current.setText('sentetik dosya')
    pencere._scan_metrics_update({'found':100})
    pencere.kilitle()
    assert not pencere.scan_dialog.isVisible()
    assert not pencere.popup_scope.text()
    assert all(not v.text() for v in pencere.scan_metrics.values())
    assert not pencere.scan_log.toPlainText()


def test_scan_has_known_total_two_percentages_and_phase_eta(pencere):
    from types import SimpleNamespace
    import datetime, time
    pencere._scan_progress({'found':7,'inventory_ready':False})
    assert pencere.tarama_bar.maximum()==0
    assert pencere.scan_metrics['documents_remaining'].text()=='—'
    data={'inventory_ready':True,'inventory_complete':True,'found':10,'documents_total':10,
          'documents_done':4,'phase_key':'content','phase_done':8,'phase_total':10,
          'phase_elapsed':40,'stage':'İçerik okunuyor','path':'sentetik.txt'}
    pencere.scan_started=datetime.datetime.now();pencere._scan_elapsed=time.monotonic()-60
    pencere.isci=SimpleNamespace(snapshot=lambda:data)
    try:
        pencere._scan_clock_update()
        assert pencere.tarama_bar.value()==40 and pencere.scan_phase_bar.value()==80
        assert pencere.scan_metrics['documents_remaining'].text()=='6'
        assert '4 / 10' in pencere.scan_progress_detail.text()
        assert 'kalan ~0 dk 10 sn' in pencere.scan_clock.text()
    finally:pencere.isci=None


def test_inaccessible_inventory_is_labelled_as_partial(pencere):
    pencere._scan_progress({'inventory_ready':True,'inventory_complete':False,
        'documents_total':10,'documents_done':10,'found':10,'stage':'Son kontroller'})
    assert 'Envanter eksik' in pencere.scan_progress_detail.text()
    assert 'Bilinen belgeler' in pencere.tarama_bar.format()


def test_015_without_tray(pencere):
    tray = pencere.tepsi
    pencere.tepsi = None
    try:
        for state in ('running','pausing','paused','cancelling','idle'):
            pencere._scan_state(state)
        assert pencere.tara_btn.text() == 'Şimdi tara'
        pencere._scan_show()
        assert pencere.scan_dialog.isVisible()
    finally:
        pencere.tepsi = tray
