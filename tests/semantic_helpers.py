"""Controlled vectors for UI/metadata tests; real-model acceptance is separate."""
import numpy as np
from deepfind import embed

def indexed_content(con,text):
    """Inspect stored extraction for lifecycle tests, independently of retrieval.

    Search quality is covered by controlled-vector and real-model acceptance.
    """
    cur=con.execute("SELECT f.file_id,f.path,f.name,s.page,s.label,s.raw_text AS snippet FROM segments s JOIN files f USING(file_id) WHERE instr(lower(s.raw_text),lower(?))>0 AND f.index_status NOT IN ('excluded','pending','missing') AND f.source_status='ok'",(text,))
    names=[d[0] for d in cur.description]
    return [dict(zip(names,row)) for row in cur]

class FixedSession:
    def encode(self,texts,**kwargs):
        return np.ones((len(texts),embed.DIM),dtype=np.float32)/16

def seed_vectors(con):
    vec=FixedSession().encode(['fixture'])[0].tobytes()
    con.execute("INSERT OR REPLACE INTO embeddings SELECT seg_id,?,?,? FROM segments WHERE kind NOT IN ('name_only','context')",(embed.MODEL_VER,embed.DIM,vec))
    con.commit()
