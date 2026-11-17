"""Collect public Shenzhen evidence and OSM geographical features; retain provenance."""
import json, hashlib, time, math
from pathlib import Path
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'; RAW.mkdir(parents=True,exist_ok=True)
SOURCES=[
 ('sz_transport','深圳市交通运输局','众志成城战暴雨 恢复秩序保运转','https://jtys.sz.gov.cn/jtzx/wycx/zjcx/zjcx_cxtx/content/post_10839773.html'),
 ('sz_response','深圳新闻网·部门正式回应','北环大道积水处置记录','https://www.sznews.com/zhuanti/content/mb/2023-09/14/content_30475114.htm'),
 ('sz_shelter','深圳市应急管理局','室内应急避难场所名录','https://yjgl.sz.gov.cn/gkmlpt/content/12/12905/post_12905910.html'),
 ('sz_flood','深圳市水务局','各区内涝点整治任务表','https://swj.sz.gov.cn/ztzl/ndmsss/yldzl/gqnldzl/'),
 ('sz_rain','深圳市政府','2023年9月暴雨情况','https://www.sz.gov.cn/cn/xxgk/zfxxgj/zwdt/content/mpost_10825070.html')]

def collect():
 manifest=[]
 for sid,publisher,title,url in SOURCES:
  row=dict(id=sid,publisher=publisher,title=title,url=url,retrieved_at=datetime.now(timezone.utc).isoformat(),kind='官方记录' if sid!='sz_response' else '部门回应',redistribution='仅保存来源与结构化事实；全文不随开源发布')
  try:
   r=requests.get(url,timeout=35); r.raise_for_status(); r.encoding=r.apparent_encoding
   text=BeautifulSoup(r.text,'html.parser').get_text('\n',strip=True)
   if len(text)<100: raise ValueError('正文过短')
   (RAW/f'{sid}.html').write_bytes(r.content); (RAW/f'{sid}.txt').write_text(text,encoding='utf-8')
   row.update(status='已获取',sha256=hashlib.sha256(r.content).hexdigest(),characters=len(text))
   if sid=='sz_shelter':
    from urllib.parse import urljoin
    row['attachments']=[urljoin(url,a['href']) for a in BeautifulSoup(r.text,'html.parser').select('a[href]') if '.pdf' in a['href'].lower() or '.xls' in a['href'].lower()]
  except Exception as e: row.update(status='待获取',error=type(e).__name__)
  manifest.append(row); print(sid,row['status'],flush=True)
 (ROOT/'data/sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

def osm():
 # Continuous central Shenzhen/Futian area. Coordinates are WGS84, not GCJ02.
 bbox='22.525,114.025,22.565,114.075'
 query=f'[out:json][timeout:120];(way["highway"]["highway"!~"footway|path|steps|cycleway|construction|proposed"]({bbox});way["building"]({bbox});node["amenity"~"school|hospital|community_centre|shelter"]({bbox}););out body;>;out skel qt;'
 raw=RAW/'osm.json'
 if not raw.exists():
  for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
   try:
    r=requests.post(endpoint,data={'data':query},timeout=170);r.raise_for_status(); payload=r.json()
    if not payload.get('elements'): raise ValueError('empty')
    raw.write_text(json.dumps(payload),encoding='utf-8');break
   except Exception as e: print('OSM',type(e).__name__,flush=True)
  else: raise RuntimeError('No geographical data obtained')
 payload=json.loads(raw.read_text()); nodes={e['id']:e for e in payload['elements'] if e['type']=='node'}
 roads=[]; buildings=[]; pois=[]
 for e in payload['elements']:
  t=e.get('tags',{})
  if e['type']=='way':
   coords=[[nodes[n]['lon'],nodes[n]['lat']] for n in e['nodes'] if n in nodes]
   if len(coords)<2: continue
   if 'highway' in t:
    roads.append(dict(type='Feature',geometry=dict(type='LineString',coordinates=coords),properties=dict(id=str(e['id']),name=t.get('name','未命名道路'),highway=t['highway'],oneway=t.get('oneway','no'),nodes=e['nodes'],origin='OSM',status='unknown')))
   elif 'building' in t and len(coords)>=4:
    height=None; basis='无高度记录'
    try:
     if 'height' in t: height=float(t['height'].replace('m','').strip());basis='OSM height'
     elif 'building:levels' in t: height=float(t['building:levels'])*3;basis='楼层数×3m估计'
    except ValueError: pass
    buildings.append(dict(type='Feature',geometry=dict(type='Polygon',coordinates=[coords]),properties=dict(id=str(e['id']),name=t.get('name','建筑'),height=height,basis=basis)))
  elif e['type']=='node' and t.get('amenity'):
   pois.append(dict(id=str(e['id']),name=t.get('name',t['amenity']),lon=e['lon'],lat=e['lat'],category=t['amenity'],origin='OSM设施点',shelter_status='未核验，不能视为已开放避难场所'))
 for name,features in [('roads',roads),('buildings',buildings)]:
  (ROOT/f'data/{name}.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features),ensure_ascii=False),encoding='utf-8')
 (ROOT/'data/pois.json').write_text(json.dumps(pois,ensure_ascii=False),encoding='utf-8')
 (ROOT/'data/geography_manifest.json').write_text(json.dumps(dict(source='OpenStreetMap contributors / Overpass API',license='ODbL 1.0',url='https://www.openstreetmap.org/copyright',bbox=bbox,crs='EPSG:4326',retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),roads=len(roads),buildings=len(buildings),pois=len(pois),historic_status='现状路网；不是2023年历史路网'),ensure_ascii=False,indent=2),encoding='utf-8')
 print('Geography',len(roads),len(buildings),len(pois),flush=True)

if __name__=='__main__':
 import sys
 if '--osm' in sys.argv: osm()
 else: collect()
