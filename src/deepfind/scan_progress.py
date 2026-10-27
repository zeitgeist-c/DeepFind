"""Distinct document completion, independent of extraction/OCR job counts."""

class DocumentProgress:
    def __init__(self, con, run_id, embeddings):
        self.con = con
        self.condition = """f.index_status IN ('ok','excluded') AND NOT EXISTS(
            SELECT 1 FROM jobs j WHERE j.file_id=f.file_id
            AND j.status IN ('pending','running','dead'))"""
        self.params = ()
        if embeddings:
            from .embed import MODEL_VER
            self.condition += """ AND NOT EXISTS(SELECT 1 FROM segments s
                LEFT JOIN embeddings e ON e.seg_id=s.seg_id AND e.model_ver=? AND e.dim=256
                WHERE s.file_id=f.file_id AND s.kind NOT IN ('name_only','context')
                AND e.seg_id IS NULL)"""
            self.params = (MODEL_VER,)
        con.execute('CREATE TEMP TABLE IF NOT EXISTS document_progress(file_id INTEGER PRIMARY KEY, ready INTEGER)')
        con.execute('DELETE FROM document_progress')
        con.execute(f'INSERT INTO document_progress SELECT f.file_id, CASE WHEN {self.condition} THEN 1 ELSE 0 END '
                    'FROM files f JOIN scan_manifest m ON m.file_id=f.file_id WHERE m.run_id=?', (*self.params, run_id))
        self.total, self.done = con.execute('SELECT count(*),coalesce(sum(ready),0) FROM document_progress').fetchone()
        con.commit()

    def refresh(self, file_id):
        row = self.con.execute('SELECT ready FROM document_progress WHERE file_id=?', (file_id,)).fetchone()
        if row is None: return
        ready = self.con.execute(f'SELECT CASE WHEN {self.condition} THEN 1 ELSE 0 END FROM files f WHERE file_id=?',
                                 (*self.params, file_id)).fetchone()[0]
        self.done += ready - row[0]
        self.con.execute('UPDATE document_progress SET ready=? WHERE file_id=?', (ready, file_id))
        self.con.commit()
