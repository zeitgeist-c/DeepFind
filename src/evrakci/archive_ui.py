"""Archive workspace composition and asynchronous, paged UI operations."""
import os,time
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QStandardItem,QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QGridLayout,QScrollArea,QPushButton,QLineEdit,
    QComboBox,QListView,QDialog,QHBoxLayout,QProgressBar,QBoxLayout,QLabel)
from .ui import card,label
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
    results=QWidget(); result_layout=QVBoxLayout(results)
    search.layout().removeWidget(w.sonuc_panel); result_layout.addWidget(w.sonuc_panel,1)
    search.layout().removeWidget(w.oneri); result_layout.addWidget(w.oneri)
    w.search_progress=QProgressBar(); w.search_progress.setRange(0,0); w.search_progress.setTextVisible(False); w.search_progress.hide()
    search.layout().insertWidget(0,w.search_bar); search.layout().addWidget(w.search_progress)
    search.layout().addWidget(label('Dosyalar yeniden okunmaz; kayıtlı içerik aranır.','ikincil'))
    search.layout().addStretch()
    w.search_more=QPushButton('Sonraki sonuçlar'); result_layout.addWidget(w.search_more); w.search_more.hide()
    w.search_more.clicked.connect(w._search_next)
    w.sonuc_liste.clicked.disconnect(w._sec); w.sonuc_liste.doubleClicked.connect(w._sec)
    preview_result=QPushButton('Seçili evrakı ön izle'); preview_result.clicked.connect(lambda:w._sec(w.sonuc_liste.currentIndex())); result_layout.addWidget(preview_result)
    copy_result=QPushButton('Seçili evrakın yolunu kopyala'); copy_result.clicked.connect(w._copy_result_path); result_layout.addWidget(copy_result)
    w.gemini_card=QWidget(); gemini=QVBoxLayout(w.gemini_card)
    assistant.layout().removeWidget(w.ai_model); gemini.addWidget(w.ai_model)
    key_layout=assistant.layout().takeAt(1)
    if key_layout and key_layout.layout():
        key_layout.layout().removeWidget(w.ai_key_input)
        gemini.addWidget(w.ai_key_input)
        gemini.addLayout(key_layout.layout())
    old_heading=assistant.layout().takeAt(0)
    if old_heading and old_heading.widget(): old_heading.widget().deleteLater()
    # Explicitly move key controls if their row index changes in a later release.
    if w.ai_key_input.parent() is assistant:
        gemini.addWidget(w.ai_key_input)
    test=QPushButton('Bağlantıyı test et'); test.clicked.connect(w._ai_test); gemini.addWidget(test)
    w.ai_connection=label('Anahtar şifreli kasada saklanır.','ikincil'); w.ai_connection.setWordWrap(True); gemini.addWidget(w.ai_connection)
    gemini.addWidget(label('Word/Excel içine gömülü resimler OCR kapsamına dahil değildir.','ikincil')); gemini.addStretch()
    suggestions=QPushButton('Gemini ile sorgu önerileri üret (yalnız soru gönderilir)')
    suggestions.clicked.connect(w._ai_suggest)
    assistant.layout().insertWidget(0,suggestions)
    w.ai_retrieval=QLineEdit(); w.ai_retrieval.setPlaceholderText('İsteğe bağlı arama sözcükleri; asıl soru korunur')
    assistant.layout().insertWidget(1,w.ai_retrieval)
    w.ai_retrieval.textChanged.connect(w._ai_clear_preview)
    w.ai_doc_query=QLineEdit(); w.ai_doc_query.setPlaceholderText('Özetlenecek belgede ad veya yol ara')
    assistant.layout().insertWidget(2,w.ai_doc_query)
    w.ai_doc_offset=0
    doc_nav=QHBoxLayout()
    for caption,direction in [('Önceki belgeler',-1),('Sonraki belgeler',1)]:
        button=QPushButton(caption); button.clicked.connect(lambda _,d=direction:w._ai_doc_page(d)); doc_nav.addWidget(button)
    assistant.layout().insertLayout(3,doc_nav)
    w.ai_doc_timer=QTimer(w); w.ai_doc_timer.setSingleShot(True); w.ai_doc_timer.setInterval(300)
    w.ai_doc_timer.timeout.connect(lambda:w._ai_doc_page(0)); w.ai_doc_query.textChanged.connect(lambda:w.ai_doc_timer.start())
    w.yigin.removeWidget(search)
    page=QWidget(); outer=QVBoxLayout(page); outer.setContentsMargins(0,0,0,0)
    canvas=QWidget(); w.archive_grid=QGridLayout(canvas); w.archive_grid.setContentsMargins(0,0,0,0)
    w.archive_cards=[]
    for title,body in [('Arama',search),('Sonuçlar',results)]:
        frame,layout=card(); layout.addWidget(label(title,'baslik')); layout.addWidget(scroll(body),1)
        w.archive_cards.append(frame)
    outer.addWidget(scroll(canvas)); w.yigin.insertWidget(0,page)
    for body in (w.gemini_card,assistant):
        for text in body.findChildren(QLabel): text.setWordWrap(True)
    w.ai_page=QWidget(); ai_layout=QVBoxLayout(w.ai_page)
    ai_canvas=QWidget(); ai_row=QHBoxLayout(ai_canvas); w.ai_row=ai_row; w.ai_cards=[]
    for title,body in [('AI ayarları',w.gemini_card),('AI ile arama ve özetleme',assistant)]:
        frame,inner=card(); inner.addWidget(label(title,'baslik')); inner.addWidget(scroll(body),1)
        ai_row.addWidget(frame,1 if body is w.gemini_card else 2)
        w.ai_cards.append(frame)
    ai_layout.addWidget(scroll(ai_canvas),1)
    w.backup_card,backup_layout=card(); backup_layout.addWidget(label('Yedekler','baslik'))
    w.backup_card.setMinimumHeight(300)
    backup_layout.addWidget(backups)
    settings.layout().insertWidget(1,w.backup_card)
    settings_index=w.yigin.indexOf(settings); w.yigin.removeWidget(settings)
    w.settings_page=QWidget(); QVBoxLayout(w.settings_page).addWidget(scroll(settings))
    w.yigin.insertWidget(settings_index,w.settings_page)
    files=QWidget(); layout=QVBoxLayout(files)
    filters=QHBoxLayout(); w.file_filter=QLineEdit(); w.file_filter.setPlaceholderText('Dosya adı veya tam yol')
    w.file_status=QComboBox(); w.file_status.addItem('Tüm durumlar','')
    for value,caption in STATUS.items(): w.file_status.addItem(caption,value)
    filters.addWidget(w.file_filter,1); filters.addWidget(w.file_status); layout.addLayout(filters)
    from PySide6.QtGui import QStandardItemModel
    w.file_model=QStandardItemModel(); w.file_list=QListView(); w.file_list.setModel(w.file_model); w.file_list.setWordWrap(True)
    layout.addWidget(w.file_list,1); w.file_notice=label('Kayıtlar yükleniyor…','ikincil'); layout.addWidget(w.file_notice)
    controls=QHBoxLayout(); preview=QPushButton('Ön izle'); preview.clicked.connect(w._file_open)
    refresh=QPushButton('Yenile'); refresh.clicked.connect(lambda:w._files_refresh(reset=True))
    errors=QPushButton('Kapsam hatalarını göster'); errors.clicked.connect(w._coverage_report)
    prev=QPushButton('Önceki'); prev.clicked.connect(lambda:w._files_page(-1))
    w.file_next=QPushButton('Sonraki'); w.file_next.clicked.connect(lambda:w._files_page(1))
    for button in (preview,refresh,errors,prev,w.file_next): controls.addWidget(button)
    layout.addLayout(controls); w.yigin.insertWidget(4,files)
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
    if not hasattr(w,'archive_grid'): return
    width=w.yigin.width()-70; columns=2 if width>=850 else 1
    w.ai_row.setDirection(QBoxLayout.LeftToRight if columns==2 else QBoxLayout.TopToBottom)
    for i,frame in enumerate(w.ai_cards):
        frame.setMinimumHeight((300 if i==0 else 600) if columns==1 else 0)
    side=max(300,(width-20*(columns-1))//columns)
    if getattr(w,'_grid_geometry',None)==(columns,side): return
    w._grid_geometry=(columns,side)
    while w.archive_grid.count(): w.archive_grid.takeAt(0)
    for row in range(w.archive_grid.rowCount()):
        w.archive_grid.setRowMinimumHeight(row,0); w.archive_grid.setRowStretch(row,0)
    w.archive_grid.setAlignment(Qt.AlignTop|Qt.AlignLeft)
    for i,frame in enumerate(w.archive_cards):
        w.archive_grid.addWidget(frame,i//columns,i%columns); frame.setFixedSize(side,side)
    w.archive_grid.parentWidget().updateGeometry()

def files_refresh(w,reset=False):
    if reset: w.file_offset=0
    text=w.file_filter.text(); status=w.file_status.currentData(); offset=w.file_offset
    w.file_notice.setText('Kayıtlar yükleniyor…')
    def ready(rows):
        cache=(text,status,offset,rows)
        if w._list_cache.get('files')==cache:
            w.file_notice.setText(f'{offset+1}–{offset+len(w.file_rows)} kayıt' if rows else 'Kayıt bulunamadı.'); return
        w._list_cache['files']=cache
        w.file_rows=rows[:100]; w.file_model.clear()
        for fid,path,name,ext,state,error,source in w.file_rows:
            item=QStandardItem(f'{name}\n{path}\n{STATUS.get(state,state)} • {error or ""} • Kaynak: {source}')
            item.setEditable(False); item.setData(path,Qt.UserRole+1); w.file_model.appendRow(item)
        w.file_next.setEnabled(len(rows)>100); w.file_notice.setText(f'{offset+1}–{offset+len(w.file_rows)} kayıt' if rows else 'Kayıt bulunamadı.')
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
        w.yedek_panel.setCurrentIndex(0 if rows else 1)
    job(w,'backups',lambda _:backup.list_backups(directory),ready)

def refresh_history(w):
    def ready(rows):
        if hasattr(w,'_list_cache'):
            if w._list_cache.get('history')==rows: return
            w._list_cache['history']=rows
        w.gecmis_model.clear()
        for qid,q,f,p,t in rows:
            item=QStandardItem(q+'\n'+f); item.setEditable(False); item.setData(qid); item.setData((q,f),Qt.UserRole+1); w.gecmis_model.appendRow(item)
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
