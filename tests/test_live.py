import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine
def test_live_event_preserves_completed_deliveries():
 e=Engine();s=e.scenario(seed=123,severity=0);p=e.solve(s);before=e.simulate(s,p);cut=10
 rid=p['vehicles'][0]['tasks'][-1]['path'];road=e.g[rid[-2]][rid[-1]]['road_id'] if len(rid)>1 else e.road_ids[0]
 after=e.simulate(s,p,[{'at':cut,'road_id':road,'state':'blocked'}])
 assert [d for d in before['deliveries'] if d['arrival']<=cut]==[d for d in after['deliveries'] if d['arrival']<=cut]
 assert after['duration']>=max([d['arrival'] for d in after['deliveries']]+[0])
def test_capacity_too_small_unassigned():
 e=Engine();s=e.scenario(seed=9,severity=0)
 for v in s['vehicles']:v['capacity']=1
 p=e.solve(s);assert len(p['unassigned'])==len(s['demands'])
