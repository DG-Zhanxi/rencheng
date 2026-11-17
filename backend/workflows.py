"""Persistent workflow endpoints; registered before the SPA catch-all."""
from datetime import datetime,timezone
from pathlib import Path
import json,secrets,hmac,hashlib
import base64,io
from concurrent.futures import ThreadPoolExecutor
from fastapi import Depends,HTTPException,Response
from pydantic import BaseModel,Field
class RoadClaim(BaseModel):
 road_id:str;state:str;event_time:datetime;available_at:datetime;expires_at:datetime
 origin_id:str=Field(min_length=1,max_length=100);reason:str=Field(min_length=1,max_length=500)
class ApplyClaims(BaseModel):as_of:datetime
class VehicleEdit(BaseModel):vehicle_id:str;capacity:int=Field(ge=1,le=100)
class PasswordEdit(BaseModel):current_password:str;new_password:str=Field(min_length=10,max_length=128)
class FileImport(BaseModel):filename:str=Field(max_length=200);content:str=Field(max_length=14000000);source_url:str=''
class LiveEvent(BaseModel):road_id:str;state:str;at:float=Field(ge=0,le=10000)
class ExperimentRequest(BaseModel):seeds:int=Field(default=3,ge=1,le=30);start_seed:int=100;severity:float=Field(default=.12,ge=0,le=.4)
class CheckInput(BaseModel):scenario_id:str;road_id:str
class CheckResult(BaseModel):state:str;note:str=Field(min_length=1,max_length=500)
pool=ThreadPoolExecutor(max_workers=1)
def register(app,ctx):
 user,connect,obj,save,log,engine,derive,pwd,public=[ctx[k] for k in ['user','connect','obj','save','log','get_engine','derive_state','pwd','public_scenario']]
 @app.post('/api/checks')
 def create_check(b:CheckInput,u=Depends(user)):
  obj(u['id'],b.scenario_id)
  if b.road_id not in engine().road_ids:raise HTTPException(422,'道路不在计算区域')
  body=dict(**b.model_dump(),status='待核查');cid=save(u['id'],'check',body);log(u['id'],'创建核查任务',cid);return dict(id=cid,**body)
 @app.get('/api/checks')
 def checks(u=Depends(user)):
  with connect() as c:rows=c.execute("SELECT id,body FROM objects WHERE owner=? AND kind='check' ORDER BY created DESC",(u['id'],)).fetchall()
  return [dict(id=r['id'],**json.loads(r['body'])) for r in rows]
 @app.post('/api/checks/{cid}/complete')
 def complete(cid:str,b:CheckResult,u=Depends(user)):
  task=obj(u['id'],cid)
  if task.get('status')!='待核查':raise HTTPException(409,'任务已完成')
  if b.state not in ['open','blocked','unknown']:raise HTTPException(422,'状态无效')
  s=obj(u['id'],task['scenario_id']);known=set(s['known_blocked'])
  if b.state=='blocked':known.add(task['road_id'])
  elif b.state=='open':known.discard(task['road_id'])
  s['known_blocked']=sorted(known);s['parent_id']=task['scenario_id'];sid=save(u['id'],'scenario',s)
  task.update(status='已完成',result=b.model_dump(),result_scenario_id=sid);save(u['id'],'check',task,cid);log(u['id'],'核查回报',cid)
  return dict(id=sid,**public(s))
 @app.post('/api/plans/{pid}/events')
 def live_event(pid:str,b:LiveEvent,u=Depends(user)):
  old=obj(u['id'],pid);s=obj(u['id'],old['scenario_id']);e=engine()
  if b.state not in ['open','blocked'] or b.road_id not in e.road_ids:raise HTTPException(422,'路段或状态无效')
  events=old['result'].get('events',[])+[b.model_dump()]
  body=dict(scenario_id=old['scenario_id'],parent_plan_id=pid,plan=old['plan'],result=e.simulate(s,old['plan'],events))
  nid=save(u['id'],'plan',body);log(u['id'],'推演事件与路径重规划',nid);return dict(id=nid,**body)
 @app.get('/api/plans/{pid}')
 def get_plan(pid:str,u=Depends(user)):
  p=obj(u['id'],pid);return dict(id=pid,**p,scenario=dict(id=p['scenario_id'],**public(obj(u['id'],p['scenario_id']))))
 @app.post('/api/experiments')
 def experiment(b:ExperimentRequest,u=Depends(user)):
  with connect() as c:
   running=c.execute("SELECT body FROM objects WHERE owner=? AND kind='experiment'",(u['id'],)).fetchall()
  if any(json.loads(r['body'])['status'] in ['排队中','运行中'] for r in running):raise HTTPException(409,'已有实验正在运行')
  body=dict(status='排队中',config=b.model_dump(),completed=0,total=b.seeds*4,runs=[])
  jid=save(u['id'],'experiment',body)
  def execute():
   try:
    body['status']='运行中';save(u['id'],'experiment',body,jid);e=engine()
    for seed in range(b.start_seed,b.start_seed+b.seeds):
     s=e.scenario(seed=seed,severity=b.severity)
     for policy in ['efficiency','robust','balanced','active']:
      p=e.solve(s,policy);r=e.simulate(s,p)
      body['runs'].append(dict(seed=seed,policy=policy,**r['metrics']));body['completed']+=1;save(u['id'],'experiment',body,jid)
    body['status']='已完成';save(u['id'],'experiment',body,jid)
   except Exception as exc:
    body.update(status='失败',error=type(exc).__name__);save(u['id'],'experiment',body,jid)
  pool.submit(execute);return {'id':jid,**body}
 @app.get('/api/experiments')
 def experiment_list(u=Depends(user)):
  with connect() as c:rows=c.execute("SELECT id,body FROM objects WHERE owner=? AND kind='experiment' ORDER BY created DESC LIMIT 30",(u['id'],)).fetchall()
  return [dict(id=r['id'],**json.loads(r['body'])) for r in rows]
 @app.post('/api/evidence/import-file')
 def import_file(b:FileImport,u=Depends(user)):
  try:raw=base64.b64decode(b.content,validate=True)
  except Exception:raise HTTPException(422,'文件编码错误')
  ext=Path(b.filename).suffix.lower()
  if ext in ['.txt','.csv','.json','.md']:
   try:text=raw.decode('utf-8-sig')
   except UnicodeDecodeError:raise HTTPException(422,'文本请使用UTF-8编码')
  elif ext=='.pdf':
   from pypdf import PdfReader
   try:
    pdf=PdfReader(io.BytesIO(raw))
    if len(pdf.pages)>100:raise ValueError('too many pages')
    text='\n'.join(p.extract_text() or '' for p in pdf.pages)
   except Exception:raise HTTPException(422,'PDF无法读取或超过100页')
  else:raise HTTPException(422,'支持PDF、TXT、CSV、JSON和Markdown')
  if not text.strip():raise HTTPException(422,'未提取到文字；扫描件请使用图片提取')
  if len(text)>200000:raise HTTPException(422,'正文超过20万字，请拆分文件')
  oid=save(u['id'],'evidence',dict(title=b.filename,text=text,source_url=b.source_url,origin='用户资料',status='待审核',sha256=hashlib.sha256(raw).hexdigest()))
  log(u['id'],'导入资料文件',oid);return {'id':oid,'characters':len(text)}
 @app.get('/api/plans')
 def plans(scenario_id:str|None=None,u=Depends(user)):
  with connect() as c:rows=c.execute("SELECT id,body,created FROM objects WHERE owner=? AND kind='plan' ORDER BY created DESC LIMIT 100",(u['id'],)).fetchall()
  result=[dict(id=r['id'],created=r['created'],**json.loads(r['body'])) for r in rows]
  return [r for r in result if not scenario_id or r['scenario_id']==scenario_id]
 @app.post('/api/evidence/{eid}/claim')
 def claim(eid:str,b:RoadClaim,u=Depends(user)):
  evidence=obj(u['id'],eid)
  if b.road_id not in engine().road_ids or b.state not in ['open','blocked','unknown']:raise HTTPException(400,'路段或状态无效')
  if any(t.tzinfo is None for t in [b.event_time,b.available_at,b.expires_at]):raise HTTPException(422,'时间需要时区')
  if b.expires_at<=b.event_time or b.available_at<b.event_time:raise HTTPException(422,'请检查发生、获知和有效截止时间')
  evidence.update(status='已采纳',claim=dict(road_id=b.road_id,state=b.state,event_time=b.event_time.isoformat(),available_at=b.available_at.isoformat(),expires_at=b.expires_at.isoformat(),origin_id=b.origin_id,source_id=eid,reviewed=True),review_reason=b.reason)
  save(u['id'],'evidence',evidence,eid);log(u['id'],'审核并匹配路段',eid);return evidence
 @app.post('/api/scenarios/{sid}/apply-evidence')
 def apply(sid:str,b:ApplyClaims,u=Depends(user)):
  s=obj(u['id'],sid)
  with connect() as c:rows=c.execute("SELECT body FROM objects WHERE owner=? AND kind='evidence'",(u['id'],)).fetchall()
  claims=[d['claim'] for d in (json.loads(r['body']) for r in rows) if d.get('status')=='已采纳' and d.get('claim')]
  states={rid:derive(claims,b.as_of,road_id=rid).as_dict() for rid in sorted({x['road_id'] for x in claims})}
  known=set(s['known_blocked'])
  for rid,r in states.items():
   if r['state'] in ['blocked','conflict']:known.add(rid)
   elif r['state']=='open':known.discard(rid)
  s['known_blocked']=sorted(known);s['evidence_states']=states;s['as_of']=b.as_of.isoformat();s['parent_id']=sid
  # Evidence changes planner knowledge only; do not rewrite simulator hidden ground truth.
  nid=save(u['id'],'scenario',s);log(u['id'],'证据更新场景',nid);return dict(id=nid,**public(s))
 @app.patch('/api/scenarios/{sid}/vehicles')
 def vehicles(sid:str,b:VehicleEdit,u=Depends(user)):
  s=obj(u['id'],sid);v=next((x for x in s['vehicles'] if x['id']==b.vehicle_id),None)
  if not v:raise HTTPException(404)
  v['capacity']=b.capacity;nid=save(u['id'],'scenario',s);log(u['id'],'修改车辆容量',nid);return dict(id=nid,**public(s))
 @app.post('/api/auth/password')
 def password(b:PasswordEdit,response:Response,u=Depends(user)):
  with connect() as c:
   r=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
   if not hmac.compare_digest(pwd(b.current_password,r['salt']),r['password']):raise HTTPException(400,'当前密码不正确')
   salt=secrets.token_hex(16);c.execute('UPDATE users SET password=?,salt=? WHERE id=?',(pwd(b.new_password,salt),salt,u['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
  response.delete_cookie('rc_session',path='/');log(u['id'],'修改密码并撤销会话');return {'ok':True}
 @app.get('/api/health')
 def health():return {'status':'ok','service':'rencheng'}
