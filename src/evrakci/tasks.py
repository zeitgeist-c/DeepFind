"""Cancelable database jobs; connection ownership stays in the worker."""
import threading
from PySide6.QtCore import QThread, Signal
from . import vault

class DatabaseTask(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, path, password, operation, parent=None, writable=False):
        super().__init__(parent)
        self.path, self.password, self.operation = path, password, operation
        self.stop = threading.Event()
        self.writable = writable

    def run(self):
        con = None
        try:
            con = vault.open_vault(self.path, self.password)
            con.execute('PRAGMA busy_timeout=500')
            if not self.writable:
                con.execute('PRAGMA query_only=ON')
            con.set_progress_handler(lambda: int(self.stop.is_set()), 1000)
            value = self.operation(con)
            if not self.stop.is_set():
                self.ready.emit(value)
        except Exception as error:
            if not self.stop.is_set():
                self.failed.emit(type(error).__name__ + ': ' + str(error))
        finally:
            if con is not None:
                try: con.close()
                except Exception: pass
            self.password = ''
            self.operation = None

def list_files(con, text='', status='', offset=0, limit=100):
    where = "WHERE (instr(lower(name),lower(?))>0 OR instr(lower(path),lower(?))>0)"
    args=[text,text]
    if status:
        where += ' AND index_status=?'; args.append(status)
    return con.execute('SELECT file_id,path,name,ext,index_status,error_code,source_status FROM files '+where+' ORDER BY path LIMIT ? OFFSET ?', args+[limit+1,offset]).fetchall()

def indexed_text(con, path, offset=0, limit=20):
    return con.execute("SELECT seg_id,label,raw_text,page FROM segments WHERE file_id=(SELECT file_id FROM files WHERE path=?) AND kind NOT IN ('name_only','context') ORDER BY seg_id LIMIT ? OFFSET ?", (path,limit+1,offset)).fetchall()
