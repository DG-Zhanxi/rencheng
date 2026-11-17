"""Reproducible routing and discrete-event delivery on measured OSM geometry.
Fleet/demand/hazard parameters are explicitly synthetic; no historical outcome claims.
"""
from pathlib import Path
import json,math,random,time,hashlib
import networkx as nx
ROOT=Path(__file__).resolve().parents[1]
def distance(a,b):
 x=(a[0]-b[0])*math.cos(math.radians((a[1]+b[1])/2))*111320
 y=(a[1]-b[1])*110540
 return math.hypot(x,y)
class Engine:
 def __init__(self):
  self.roads=json.loads((ROOT/'data/roads.geojson').read_text(encoding='utf-8'))
  self.g=nx.DiGraph();self.positions={}
  for f in self.roads['features']:
   p=f['properties']; coords=f['geometry']['coordinates'];ids=p['nodes']
   for node,xy in zip(ids,coords): self.positions[str(node)]=xy
   for i in range(len(coords)-1):
    u,v=str(ids[i]),str(ids[i+1]);length=distance(coords[i],coords[i+1]); minutes=max(length/1000/22*60,0.005)
    if p['oneway']!='-1':self.g.add_edge(u,v,length=length,minutes=minutes,road_id=p['id'])
    if p['oneway'] not in ['yes','1','true']:self.g.add_edge(v,u,length=length,minutes=minutes,road_id=p['id'])
  largest=max(nx.strongly_connected_components(self.g),key=len);self.g=self.g.subgraph(largest).copy()
  self.nodes=sorted(self.g.nodes); self.road_ids=sorted(set(d['road_id'] for _,_,d in self.g.edges(data=True)))
  self.depot=min(self.nodes,key=lambda n:distance(self.positions[n],[114.05,22.545]))
 def scenario(self,seed=42,demands=12,vehicles=3,severity=.12):
  rng=random.Random(seed); selected=rng.sample([n for n in self.nodes if distance(self.positions[n],self.positions[self.depot])>400],demands)
  risks={r:rng.uniform(.02,.32) for r in self.road_ids}
  # Spatially correlated latent hazard, independent from the planner's visibility.
  center=self.positions[rng.choice(selected)];truth=set()
  mids={}
  for u,v,d in self.g.edges(data=True):mids.setdefault(d['road_id'],self.positions[u])
  for r in self.road_ids:
   near=distance(mids[r],center)<850
   if rng.random()<severity*(2.4 if near else .45):truth.add(r)
   risks[r]=min(.65,risks[r]+(.2 if near else 0))
  known=set(rng.sample(sorted(truth),int(len(truth)*.3))) if truth else set()
  tasks=[dict(id=f'D{i+1:02}',node=n,name=f'需求点 {i+1:02}',lon=self.positions[n][0],lat=self.positions[n][1],quantity=rng.randint(2,7),priority=rng.choice([1,2,3]),deadline=rng.choice([45,60,90]),origin='演练参数') for i,n in enumerate(selected)]
  return dict(seed=seed,demands=tasks,vehicles=[dict(id=f'V{i+1:02}',name=f'车辆 {i+1:02}',capacity=15,node=self.depot,origin='演练参数') for i in range(vehicles)],depot=self.depot,severity=severity,known_blocked=sorted(known),truth_blocked=sorted(truth),risk=risks,origin='现状真实路网 + 合成灾情与资源',inventory=sum(t['quantity'] for t in tasks))
 def path(self,a,b,blocked,risk=None,penalty=0):
  def weight(u,v,d):
   if d['road_id'] in blocked:return None
   return d['minutes']*(1+penalty*(risk or {}).get(d['road_id'],0))
  try:return nx.shortest_path(self.g,a,b,weight=weight)
  except nx.NetworkXNoPath:return None
 def solve(self,scenario,policy='balanced'):
  t0=time.perf_counter();known=set(scenario['known_blocked']);risk=scenario['risk'];penalty={'efficiency':0,'robust':8,'balanced':4,'active':4,'oracle':0}.get(policy,4)
  # Planner never receives latent closure labels except paid verification/oracle reference.
  checks=[]
  if policy=='oracle':known=set(scenario['truth_blocked'])
  if policy=='active':
   counts={}
   for task in scenario['demands']:
    p=self.path(scenario['depot'],task['node'],known,risk,penalty) or []
    for u,v in zip(p,p[1:]):
     rid=self.g[u][v]['road_id'];counts[rid]=counts.get(rid,0)+task['priority']*self.g[u][v]['minutes']*risk[rid]
   for rid,value in sorted(counts.items(),key=lambda x:-x[1])[:3]:
    closed=rid in scenario['truth_blocked']
    if closed:known.add(rid)
    checks.append(dict(road_id=rid,score=round(value,4),state='blocked' if closed else 'open',cost_minutes=2))
  fleet=[dict(**v,time=len(checks)*2 if policy=='active' else 0,load=v['capacity'],route=[],tasks=[]) for v in scenario['vehicles']]
  pending=sorted(scenario['demands'],key=lambda d:(-d['priority'],d['deadline'],d['id']))
  unassigned=[]
  for task in pending:
   choices=[]
   for idx,v in enumerate(fleet):
    if task['quantity']>v['capacity']:continue
    reload=v['load']<task['quantity'];a=self.path(v['node'],scenario['depot'],known,risk,penalty) if reload else [v['node']]
    b=self.path(scenario['depot'] if reload else v['node'],task['node'],known,risk,penalty)
    if a is None or b is None:continue
    p=a+b[1:];duration=sum(self.g[u][w]['minutes'] for u,w in zip(p,p[1:]))+(5 if reload else 0)
    choices.append((v['time']+duration,idx,p,reload))
   if not choices:unassigned.append(task['id']);continue
   arrival,idx,p,reload=min(choices,key=lambda c:c[0]);v=fleet[idx]
   v['tasks'].append(dict(**task,planned_arrival=round(arrival,2),reload=reload,path=p))
   v['route']+=p if not v['route'] else p[1:];v['node']=task['node'];v['time']=arrival+3;v['load']=(v['capacity'] if reload else v['load'])-task['quantity']
  for v in fleet:v['coordinates']=[self.positions[n] for n in v['route']]
  return dict(policy=policy,vehicles=fleet,checks=checks,unassigned=unassigned,known_blocked=sorted(known),compute_ms=round((time.perf_counter()-t0)*1000,2),method='风险加权最短路＋优先级贪心分配；核查使用影响分数启发式，非精确VOI')
 def simulate(self,scenario,plan,events=None):
  truth=set(scenario['truth_blocked']);log=[];deliveries=[];travel=0;failures=0;all_paths=[]
  penalty={'efficiency':0,'robust':8,'balanced':4,'active':4,'oracle':0}.get(plan['policy'],4)
  for vehicle in plan['vehicles']:
   truth=set(scenario['truth_blocked']);applied=set()
   known=set(plan['known_blocked']) # No future observations leak between independently simulated vehicles.
   current=scenario['depot'];clock=len(plan['checks'])*2;load=vehicle['capacity'];trajectory=[dict(t=clock,coordinate=self.positions[current])]
   for task in vehicle['tasks']:
    targets=([scenario['depot']] if load<task['quantity'] else [])+[task['node']];success=True
    for target in targets:
     loops=0
     while current!=target and loops<5000:
      for event_index,event in enumerate(events or []):
       if event_index not in applied and event['at']<=clock:
        applied.add(event_index);rid=event['road_id']
        if event['state']=='blocked':truth.add(rid);known.add(rid)
        else:truth.discard(rid);known.discard(rid)
        log.append(dict(t=round(clock,2),vehicle=vehicle['id'],event='接收事件并重规划',road_id=rid))
      loops+=1;p=self.path(current,target,known,scenario['risk'],penalty)
      if p is None:success=False;break
      nxt=p[1];edge=self.g[current][nxt]
      if edge['road_id'] in truth:
       known.add(edge['road_id']);clock+=4;failures+=1
       log.append(dict(t=round(clock,2),vehicle=vehicle['id'],event='发现阻断并重规划',road_id=edge['road_id']))
       continue
      clock+=edge['minutes'];travel+=edge['length'];current=nxt
      trajectory.append(dict(t=round(clock,3),coordinate=self.positions[current]))
     if loops>=5000:success=False
     if not success:break
     if target==scenario['depot']:clock+=5;load=vehicle['capacity']
    if success:
     load-=task['quantity'];clock+=3
     deliveries.append(dict(id=task['id'],arrival=round(clock,2),deadline=task['deadline'],priority=task['priority'],quantity=task['quantity'],ontime=clock<=task['deadline']))
     log.append(dict(t=round(clock,2),vehicle=vehicle['id'],event='配送完成',demand_id=task['id']))
    else:log.append(dict(t=round(clock,2),vehicle=vehicle['id'],event='无可达路径',demand_id=task['id']))
   all_paths.append(dict(vehicle=vehicle['id'],trajectory=trajectory))
  total=sum(d['quantity']*d['priority'] for d in scenario['demands']);done=sum(d['quantity']*d['priority'] for d in deliveries)
  late=sum(max(0,d['arrival']-d['deadline'])*d['priority'] for d in deliveries)
  metrics=dict(completion=round(len(deliveries)/len(scenario['demands'])*100,2),ontime=round(sum(d['ontime'] for d in deliveries)/len(scenario['demands'])*100,2),weighted_shortage=total-done,weighted_delay=round(late,2),distance_km=round(travel/1000,3),block_encounters=failures,check_minutes=len(plan['checks'])*2,compute_ms=plan['compute_ms'])
  return dict(metrics=metrics,deliveries=deliveries,log=sorted(log,key=lambda x:x['t']),trajectories=all_paths,duration=max([p['trajectory'][-1]['t'] for p in all_paths]+[d['arrival'] for d in deliveries]+[1]),events=events or [],label='真实路网上的合成场景实验')
