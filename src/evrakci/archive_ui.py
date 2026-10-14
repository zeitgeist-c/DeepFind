"""Archive workspace composition and asynchronous, paged UI operations."""
import os,time
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QStandardItem,QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QScrollArea,QPushButton,QLineEdit,
    QComboBox,QListView,QDialog,QHBoxLayout,QProgressBar,QBoxLayout,QLabel,QSplitter)
from .ui import bolme, card, label
from .tasks import DatabaseTask,list_files
from . import ai,backup,history,diagnostics

STATUS={'pending':'Bekliyor','ok':'Tamamlandı','partial':'Kısmi','encrypted':'Kilitli',
        'unsupported_content':'İçerik motoru yok','corrupt':'Hatalı','missing':'Erişilemiyor','excluded':'Hariç'}

def job(window,key,operation,callback,writable=False,failed=None):
    if (window.con is None and key!='restore') or window._locked: return
    previous=window._job_keys.get(key)
    if previous:
        previous.stop.set()
        window._job_pending[key]=(operation,callback,writable,failed)
        return
    token=window._job_generation
    worker=DatabaseTask(window.kasa_yolu,window._sifre,operation,window,writable)
    window._jobs.append(worker); window._job_keys[key]=worker
    def ready(value):
        if not window._locked and token==window._job_generation and window._job_keys.get(key) is worker and key not in window._job_pending:
            callback(value)
    def error(message):
        if not window._locked and token==window._job_generation and window._job_keys.get(key) is worker:
            if failed: failed(message)
            else: window.durum.showMessage('İşlem tamamlanamadı: '+message)
    def finished():
        if worker in window._jobs: window._jobs.remove(worker)
        if window._job_keys.get(key) is worker: window._job_keys.pop(key,None)
        worker.deleteLater()
        pending=window._job_pending.pop(key,None)
        if pending and not window._locked and not window._exiting:
            job(window,key,*pending[:2],writable=pending[2],failed=pending[3])
    worker.ready.connect(ready); worker.failed.connect(error); worker.finished.connect(finished); worker.start()

def scroll(widget):
    area=QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QScrollArea.NoFrame); area.setWidget(widget)
    area.setStyleSheet('QScrollArea {background:transparent; border:none;} QScrollArea > QWidget > QWidget {background:transparent;}')
    return area

def install(w):
    # Existing behaviors are reparented, rather than duplicated or discarded.
    w._list_cache={}
    search=w.yigin.widget(0); backups=w.yigin.widget(4); settings=w.yigin.widget(5); assistant=w.yigin.widget(6)
    w.yigin.removeWidget(backups); w.yigin.removeWidget(assistant)
    # Ara ekranı üç sütun işlik olarak hazır; üstüne arama çubuğu ve ilerleme eklenir.
    search.layout().insertWidget(0,w.search_bar)
    w.search_progress=QProgressBar(); w.search_progress.setRange(0,0); w.search_progress.setTextVisible(False); w.search_progress.hide()
    search.layout().insertWidget(1,w.search_progress)
    # AI: sol kurulum rail + sağ numaralı adımlar
    kurulum,kurulum_layout=card(); kurulum.setObjectName("sideRail")
    kurulum_layout.addWidget(label('KURULUM','eyebrow'))
    kurulum_layout.addWidget(w.ai_kurulum)
    adimlar=QWidget(); adim_layout=QVBoxLayout(adimlar); adim_layout.setContentsMargins(0,0,0,0)
    for num,box,baslik in (('1',w.ai_soru,'SORU'),('2',w.ai_alinti,'ALINTILAR'),('3',w.ai_yanit,'YANIT')):
        satir=QHBoxLayout()
        rozet=QLabel(num); rozet.setObjectName("numb"); satir.addWidget(rozet,0,Qt.AlignTop)
        adim,adim_inner=card(); adim_inner.addWidget(label(baslik,'eyebrow')); adim_inner.addWidget(box)
        satir.addWidget(adim,1); adim_layout.addLayout(satir)
    adim_layout.addStretch(1)
    adim_kaydir = QScrollArea()
    adim_kaydir.setWidgetResizable(True)
    adim_kaydir.setFrameShape(QScrollArea.NoFrame)
    adim_kaydir.setWidget(adimlar)
    for box in (w.ai_kurulum,w.ai_soru,w.ai_alinti,w.ai_yanit):
        for text in box.findChildren(QLabel): text.setWordWrap(True)
    w.ai_page=QWidget(); ai_sayfa=QVBoxLayout(w.ai_page); ai_sayfa.setContentsMargins(0,0,0,0)
    ai_split=QSplitter(Qt.Horizontal); ai_split.setChildrenCollapsible(False)
    ai_split.addWidget(kurulum); ai_split.addWidget(adim_kaydir)
    ai_split.setStretchFactor(0,0); ai_split.setStretchFactor(1,1); ai_split.setSizes([250,730])
    w.ai_split=ai_split; ai_sayfa.addWidget(ai_split)
    w.backup_card,backup_layout=card()
    baslik_satir=QHBoxLayout()
    baslik_satir.addWidget(label('Yedekler','baslik'))
    w.yedek_sayi=label('','pill'); w.yedek_sayi.hide(); baslik_satir.addWidget(w.yedek_sayi)
    baslik_satir.addStretch(1)
    backup_layout.addLayout(baslik_satir)
    backup_layout.addWidget(backups)
    w.yedek_bolum.layout().addWidget(w.backup_card)
    settings_index=w.yigin.indexOf(settings); w.yigin.removeWidget(settings)
    w.settings_page=QWidget(); QVBoxLayout(w.settings_page).addWidget(scroll(settings))
    w.yigin.insertWidget(settings_index,w.settings_page)
    files=QWidget(); layout=QVBoxLayout(files); layout.setContentsMargins(0,0,0,0)
    filters=QHBoxLayout(); w.file_filter=QLineEdit(); w.file_filter.setPlaceholderText('Dosya adı veya tam yol')
    w.file_status=QComboBox(); w.file_status.addItem('Tüm durumlar','')
    for value,caption in STATUS.items(): w.file_status.addItem(caption,value)
    filters.addWidget(w.file_filter,1); filters.addWidget(w.file_status)
    w.file_notice=label('','pill'); w.file_notice.hide(); filters.addWidget(w.file_notice); layout.addLayout(filters)
    from PySide6.QtGui import QStandardItemModel
    split=QSplitter(Qt.Horizontal); split.setChildrenCollapsible(False)
    sol=QWidget(); sl=QVBoxLayout(sol); sl.setContentsMargins(0,18,0,0)
    sl.addWidget(label('KAYITLAR','eyebrow'))
    w.file_model=QStandardItemModel(); w.file_list=QListView(); w.file_list.setModel(w.file_model); w.file_list.setWordWrap(True)
    w.file_list.clicked.connect(w._dosya_ayrinti)
    sl.addWidget(w.file_list,1); split.addWidget(sol)
    dosya,dl=card(); dl.addWidget(label('SEÇİLİ KAYIT','eyebrow'))
    w.dosya_ad=label('Bir kayıt seçin','subheading'); w.dosya_ad.setWordWrap(True); dl.addWidget(w.dosya_ad)
    w.dosya_yol=label('','ikincil'); w.dosya_yol.setTextFormat(Qt.PlainText)
    w.dosya_yol.setTextInteractionFlags(Qt.TextSelectableByMouse); w.dosya_yol.setWordWrap(True); dl.addWidget(w.dosya_yol)
    w.dosya_bilgi=label('','ikincil'); w.dosya_bilgi.setWordWrap(True); dl.addWidget(w.dosya_bilgi)
    dl.addWidget(bolme())
    dl.addStretch(1)
    w.dosya_onizle=QPushButton('Ön izle'); w.dosya_onizle.setProperty('birincil',True)
    w.dosya_onizle.clicked.connect(w._file_open); w.dosya_onizle.setEnabled(False); dl.addWidget(w.dosya_onizle)
    split.addWidget(dosya); split.setStretchFactor(0,1); split.setStretchFactor(1,0); split.setSizes([520,280])
    w.dosya_split=split
    layout.addWidget(split,1)
    controls=QHBoxLayout()
    refresh=QPushButton('Yenile'); refresh.clicked.connect(lambda:w._files_refresh(reset=True))
    errors=QPushButton('Kapsam'); errors.setToolTip('Kapsam hatalarını göster'); errors.clicked.connect(w._coverage_report)
    prev=QPushButton('Önceki'); prev.clicked.connect(lambda:w._files_page(-1))
    w.file_next=QPushButton('Sonraki'); w.file_next.clicked.connect(lambda:w._files_page(1))
    for button in (refresh,errors,prev,w.file_next): controls.addWidget(button)
    layout.addLayout(controls); w.yigin.insertWidget(4,files)
    w._dosya_ayrinti()
    w.yigin.insertWidget(1,w.ai_page)
    w.file_offset=0; w.file_rows=[]
    w.file_debounce=QTimer(w); w.file_debounce.setSingleShot(True); w.file_debounce.setInterval(300)
    w.file_debounce.timeout.connect(lambda:w._files_refresh(reset=True))
    w.file_filter.textChanged.connect(lambda:w.file_debounce.start()); w.file_status.currentIndexChanged.connect(lambda:w._files_refresh(reset=True))
    w.file_list.doubleClicked.connect(w._file_open)
    w.nav.blockSignals(True); w.nav.clear(); w.nav.addItems(['Ara','AI ile ara','Kaynaklar','Tarama','Geçmiş','Taranmış Evraklar','Ayarlar']); w.nav.setCurrentRow(0); w.nav.blockSignals(False)
    from . import theme
    for i,kind in enumerate(('search','search','folder','scan','history','folder','settings')): w.nav.item(i).setIcon(theme.symbol_icon(kind))
    w.yigin.setCurrentIndex(0)

def layout_cards(w):
    if not hasattr(w,'ai_row'): return
    width=w.yigin.width()-70; columns=2 if width>=850 else 1
    w.ai_row.setDirection(QBoxLayout.LeftToRight if columns==2 else QBoxLayout.TopToBottom)
    for i,frame in enumerate(w.ai_cards):
        frame.setMinimumHeight((300 if i==0 else 600) if columns==1 else 0)

def files_refresh(w,reset=False):
    if reset: w.file_offset=0
    text=w.file_filter.text(); status=w.file_status.currentData(); offset=w.file_offset
    w.file_notice.setText('Kayıtlar yükleniyor…'); w.file_notice.show()
    def ready(rows):
        cache=(text,status,offset,rows)
        if w._list_cache.get('files')==cache:
            w.file_notice.setText(f'{offset+1}–{offset+len(w.file_rows)} kayıt' if rows else 'Kayıt bulunamadı.'); w.file_notice.show(); return
        w._list_cache['files']=cache
        w.file_rows=rows[:100]; w.file_model.clear()
        for fid,path,name,ext,state,error,source in w.file_rows:
            item=QStandardItem(f'{name}\n{path}\n{STATUS.get(state,state)} • {error or ""} • Kaynak: {source}')
            item.setEditable(False); item.setData(path,Qt.UserRole+1); w.file_model.appendRow(item)
        w._dosya_ayrinti()
        w.file_next.setEnabled(len(rows)>100); w.file_notice.setText(f'{offset+1}–{offset+len(w.file_rows)} kayıt' if rows else 'Kayıt bulunamadı.'); w.file_notice.show()
    job(w,'files',lambda con:list_files(con,text,status,offset),ready)

def files_page(w,direction):
    w.file_offset=max(0,w.file_offset+100*direction); files_refresh(w)

def file_open(w,*_):
    idx=w.file_list.currentIndex()
    if not idx.isValid() or idx.row()>=len(w.file_rows): return
    fid,path,name,ext,state,error,source=w.file_rows[idx.row()]
    w._open_preview(dict(file_id=fid,path=path,name=name,ext=ext,label='',page=1))

def refresh_backups(w):
    directory=w._yedek_dizin()
    def ready(rows):
        if hasattr(w,'_list_cache'):
            if w._list_cache.get('backups')==rows: return
            w._list_cache['backups']=rows
        w.yedek_model.clear()
        for b in rows:
            item=QStandardItem(f'{os.path.basename(b["path"])}\n{b["boyut"]//1024} KB • Şifreli kasa')
            item.setEditable(False); item.setData(b['path']); w.yedek_model.appendRow(item)
        w.yedek_sayi.setText(f'{len(rows)} yedek')
        w.yedek_sayi.setVisible(bool(rows))
        w.yedek_panel.setCurrentIndex(0 if rows else 1)
    job(w,'backups',lambda _:backup.list_backups(directory),ready)

def refresh_history(w):
    def ready(rows):
        if hasattr(w,'_list_cache'):
            if w._list_cache.get('history')==rows: return
            w._list_cache['history']=rows
        w.gecmis_model.clear()
        import json as _json
        for qid,q,f,p,t in rows:
            try:
                v=_json.loads(f)
            except (ValueError,TypeError):
                v=dict(x.split("=",1) for x in f.split(";") if "=" in x)
            parca=[]
            if v.get("yil"): parca.append(f"yıl:{v['yil']}")
            if v.get("tur") and v["tur"]!="tümü": parca.append(f"tür:{v['tur']}")
            if v.get("klasor"): parca.append(f"klasör:{v['klasor']}")
            if v.get("etiket"): parca.append(f"etiket:{v['etiket']}")
            ozet="  •  ".join(parca) or "Filtresiz arama"
            item=QStandardItem(q+'\n'+ozet); item.setEditable(False); item.setData(qid); item.setData((q,f),Qt.UserRole+1); w.gecmis_model.appendRow(item)
        w.gecmis_sayi.setText(f'{len(rows)} arama')
        w._gecmis_ayrinti()
    job(w,'history',history.list_all,ready)

def refresh_docs(w):
    def ready(rows):
        if hasattr(w,'_list_cache'):
            if w._list_cache.get('docs')==rows: return
            w._list_cache['docs']=rows
        old=w.ai_document.currentData(); w.ai_document.blockSignals(True); w.ai_document.clear()
        for fid,name,path in rows: w.ai_document.addItem(name+' • '+path,fid)
        w.ai_document.setCurrentIndex(max(0,w.ai_document.findData(old))); w.ai_document.blockSignals(False)
    offset=getattr(w,'ai_doc_offset',0); query=w.ai_doc_query.text() if hasattr(w,'ai_doc_query') else ''
    job(w,'ai_docs',lambda con:ai.list_documents(con,limit=100,offset=offset,query=query),ready)
