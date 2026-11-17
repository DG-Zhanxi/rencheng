import json,hashlib,re
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parents[1]
sources=json.loads((R/'data/sources.json').read_text(encoding='utf-8'))
for s in sources:
 p=R/f"data/raw/{s['id']}.html"
 if not p.exists():continue
 soup=BeautifulSoup(p.read_bytes(),'html.parser');txt=soup.get_text('\n',strip=True)
 if len(txt)<100:continue
 (R/f"data/raw/{s['id']}.txt").write_text(txt,encoding='utf-8')
 s.update(status='已获取',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),characters=len(txt));s.pop('error',None)
 if s['id']=='sz_flood':
  from urllib.parse import urljoin
  print([(a.get_text(strip=True),urljoin(s['url'],a['href'])) for a in soup.select('a[href]') if '2023' in a.get_text()])
(R/'data/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
events=[dict(id='EV-001',title='北环大道安托山路段北侧积水',source_id='sz_response',event_type='积水',location_text='北环大道安托山路段北侧',occurred_at='2023-09-08T10:23:00+08:00',available_at='2023-09-14T16:15:00+08:00',status='待复核',origin='真实记录',quote='10时23分',road_id=None),dict(id='EV-002',title='北环大道积水消退、恢复通行',source_id='sz_response',event_type='恢复',location_text='北环大道安托山路段北侧',occurred_at='2023-09-08T18:20:00+08:00',available_at='2023-09-14T16:15:00+08:00',status='待复核',origin='真实记录',quote='18时20分',road_id=None)]
for e in events:
 t=(R/f"data/raw/{e['source_id']}.txt").read_text(encoding='utf-8');i=t.find(e['quote']);e['excerpt']=t[max(0,i-60):i+180] if i>=0 else '';e['verified_in_download']=i>=0
(R/'data/events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf-8')
cfg=R/'config/model.json';c=json.loads(cfg.read_text());c['model']='kimi-k2.6';cfg.write_text(json.dumps(c),encoding='utf-8')
print('sources',sum(s['status']=='已获取' for s in sources),'events',len(events))
