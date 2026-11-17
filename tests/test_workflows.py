import sys,secrets
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app import app,get_engine
def test_evidence_to_scenario_and_history():
 c=TestClient(app);c.post('/api/auth/register',json={'username':'flow_'+secrets.token_hex(4),'password':'workflow-test-password'})
 sid=c.post('/api/scenarios',json={'seed':91}).json()['id']
 eid=c.post('/api/evidence',json={'title':'测试证据','text':'演练测试','origin':'演练参数'}).json()['id']
 rid=get_engine().road_ids[0]
 b={'road_id':rid,'state':'blocked','event_time':'2026-11-16T09:00:00+08:00','available_at':'2026-11-16T09:10:00+08:00','expires_at':'2026-11-16T12:00:00+08:00','origin_id':'test','reason':'独立测试'}
 assert c.post('/api/evidence/'+eid+'/claim',json=b).status_code==200
 r=c.post('/api/scenarios/'+sid+'/apply-evidence',json={'as_of':'2026-11-16T10:00:00+08:00'}).json()
 assert r['id']!=sid and rid in r['known_blocked']
 assert r['evidence_states'][rid]['state']=='blocked'
 before=c.post('/api/scenarios/'+sid+'/apply-evidence',json={'as_of':'2026-11-16T08:00:00+08:00'}).json()
 assert before['evidence_states'][rid]['state']=='unknown'
 assert c.get('/api/plans').status_code==200
 assert c.get('/api/audit').json()
 assert c.post('/api/auth/password',json={'current_password':'workflow-test-password','new_password':'workflow-new-password'}).status_code==200
 assert c.get('/api/auth/me').status_code==401
 assert c.post('/api/auth/login',json={'username':'nonexistent','password':'workflow-test-password'}).status_code==401
