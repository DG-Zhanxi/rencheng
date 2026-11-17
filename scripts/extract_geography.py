import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages'))
import osmium
class Extract(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.elements=[];self.nodes={}
 def node(self,n):
  if n.location.valid() and 114.025<=n.location.lon<=114.075 and 22.525<=n.location.lat<=22.565 and n.tags.get('amenity') in ['school','hospital','community_centre','shelter']:
   self.nodes[n.id]=dict(type='node',id=n.id,lon=n.location.lon,lat=n.location.lat,tags=dict(n.tags))
 def way(self,w):
  t=dict(w.tags)
  if not ('highway' in t or 'building' in t):return
  if t.get('highway') in ['footway','path','steps','cycleway','construction','proposed']:return
  try: pts=[(n.ref,n.lon,n.lat) for n in w.nodes]
  except osmium.InvalidLocationError:return
  if not pts or not all(114.025<=x<=114.075 and 22.525<=y<=22.565 for _,x,y in pts):return
  self.elements.append(dict(type='way',id=w.id,tags=t,nodes=[p[0] for p in pts]))
  for nid,x,y in pts:
   if nid not in self.nodes:self.nodes[nid]=dict(type='node',id=nid,lon=x,lat=y)
h=Extract();h.apply_file(str(ROOT/'data/raw/shenzhen.osm'),locations=True)
(ROOT/'data/raw/osm.json').write_text(json.dumps({'elements':list(h.nodes.values())+h.elements}),encoding='utf-8')
from collect_data import osm
osm()
