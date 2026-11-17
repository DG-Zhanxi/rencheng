import sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.engine import Engine
from fastapi.testclient import TestClient
from backend.app import app
import secrets
def test_auth_isolation():
 a=TestClient(app);b=TestClient(app);name='qa_'+secrets.token_hex(4)
 assert a.get('/api/scenarios').status_code==401
 r=a.post('/api/auth/register',json={'username':name,'password':'test-password-2026'});assert r.status_code==200
 assert 'HttpOnly' in r.headers['set-cookie']
 sid=a.post('/api/scenarios',json={'seed':77}).json()['id']
 assert 'truth_blocked' not in a.get('/api/scenarios').json()[0]
 assert b.post('/api/auth/register',json={'username':name+'b','password':'test-password-2026'}).status_code==200
 assert b.post(f'/api/scenarios/{sid}/plans',json={'policy':'balanced'}).status_code==404
 assert a.post('/api/auth/logout').status_code==200
 assert a.get('/api/auth/me').status_code==401
def test_determinism_and_capacity():
 e=Engine();s=e.scenario(99);assert s==e.scenario(99)
 for mode in ['efficiency','balanced','robust','active']:
  p=e.solve(s,mode);assert len({t['id'] for v in p['vehicles'] for t in v['tasks']})+len(p['unassigned'])==len(s['demands'])
  for v in p['vehicles']:
   load=v['capacity']
   for t in v['tasks']:
    if t['reload']:load=v['capacity']
    load-=t['quantity'];assert load>=0
    assert all(e.g[u][w]['road_id'] not in p['known_blocked'] for u,w in zip(t['path'],t['path'][1:]))
  r=e.simulate(s,p);assert 0<=r['metrics']['completion']<=100;assert r['metrics']['weighted_shortage']>=0
def test_no_hidden_truth_leak_in_planning():
 e=Engine();s=e.scenario(88);other=copy.deepcopy(s);other['truth_blocked']=[]
 for mode in ['efficiency','balanced','robust']:
  a=e.solve(s,mode);b=e.solve(other,mode);a.pop('compute_ms');b.pop('compute_ms');assert a==b
def test_no_closure_and_unreachable():
 e=Engine();s=e.scenario(76,severity=0);r=e.simulate(s,e.solve(s));assert r['metrics']['completion']==100
 s['known_blocked']=e.road_ids;s['truth_blocked']=e.road_ids;p=e.solve(s);assert len(p['unassigned'])==12
