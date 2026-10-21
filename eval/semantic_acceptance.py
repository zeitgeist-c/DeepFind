"""Offline acceptance of vector-only retrieval using the actual shipped model."""
from pathlib import Path
import sys,json,time,sqlite3
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evrakci import engine,embed,rank,migrate,index
from evrakci.extract import ExtractResult,Segment
from evrakci.scan import Entry

def main():
    docs=['elektrik faturası tüketim bedeli 1250 TL','kira sözleşmesi aylık 40000 TL',
          'personel maaş bordrosu çalışan ücreti','vergi levhası mükellef bilgileri',
          'araç bakım onarım servis faturası','iş sağlığı güvenliği denetim raporu',
          'banka hesap hareketleri havale dekontu','satın alma sipariş teslim tutanağı']
    queries=['ev kiralama anlaşması','çalışanlara yapılan aylık ödeme','otomobil tamir masrafı',
             'elektrik kullanım ücreti','işyerinde güvenlik incelemesi','para transferi belgesi']
    expected=[1,2,4,0,5,6];report={}
    for backend in ['cpu','vulkan']:
        session=engine.Oturum(backend=backend)
        con=sqlite3.connect(':memory:');migrate.ensure_current(con)
        try:
            started=time.perf_counter();vectors=session.encode(docs,gorev='belge');ids=[]
            for i,(text,vector) in enumerate(zip(docs,vectors)):
                name=f'scan_{i:04d}.txt'
                fid=index.index_entry(con,Entry(name,name,'.txt',1,1),ExtractResult([Segment('para',None,'Belge',text)],status='ok'))
                ids.append(fid)
                sid=con.execute("SELECT seg_id FROM segments WHERE file_id=? AND kind='para'",(fid,)).fetchone()[0]
                con.execute('INSERT INTO embeddings VALUES (?,?,?,?)',(sid,embed.MODEL_VER,embed.DIM,vector.tobytes()));con.commit()
            top=[];top3=[]
            for query in queries:
                out=rank.search_semantic(con,query,kodla=lambda texts:session.encode(texts,gorev='sorgu'))
                top.append(ids.index(out['results'][0]['file_id']))
                top3.append([ids.index(r['file_id']) for r in out['results'][:3]])
            report[backend]={'top':top,'expected':expected,'correct':sum(a==b for a,b in zip(top,expected)),
                'seconds':time.perf_counter()-started,'device':session.device,'filenames':'meaningless scan numbers','top3':top3,'recall3':sum(e in r for e,r in zip(expected,top3))}
            assert report[backend]["correct"]>=5 and report[backend]["recall3"]==6,report
            assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs_fts'").fetchone()
        finally:con.close();session.close()
    (ROOT/'build/semantic-acceptance-0.10.6.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
