import sys,json,csv,time,platform,hashlib
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from backend.engine import Engine
e=Engine();runs=[];start=time.time();policies=['efficiency','robust','balanced','active','oracle']
for severity in [.04,.12,.24]:
 for seed in range(100,130):
  scenario=e.scenario(seed=seed,demands=12,vehicles=3,severity=severity)
  for policy in policies:
   plan=e.solve(scenario,policy);result=e.simulate(scenario,plan)
   runs.append(dict(seed=seed,severity=severity,policy=policy,**result['metrics']))
  print(f'{severity} seed={seed} runs={len(runs)}',flush=True)
summary=[]
for p in policies:
 records=[r for r in runs if r['policy']==p];row={'policy':p,'n':len(records)}
 for key in ['ontime','completion','weighted_shortage','weighted_delay','distance_km','block_encounters','compute_ms','check_minutes']:
  a=np.array([r[key] for r in records]);row[key+'_mean']=float(a.mean());row[key+'_std']=float(a.std(ddof=1));row[key+'_p95']=float(np.quantile(a,.95))
 summary.append(row)
# Paired bootstrap per independent seed, keeping all severities together.
rng=np.random.default_rng(20261116);comparisons=[]
for p in policies[1:]:
 differences=[]
 for seed in range(100,130):
  a=[r['ontime'] for r in runs if r['seed']==seed and r['policy']==p];b=[r['ontime'] for r in runs if r['seed']==seed and r['policy']=='efficiency'];differences.append(np.mean(a)-np.mean(b))
 a=np.array(differences);boot=np.mean(rng.choice(a,size=(2000,len(a)),replace=True),axis=1)
 comparisons.append(dict(policy=p,baseline='efficiency',metric='ontime_percentage_points',mean=float(a.mean()),ci95=[float(x) for x in np.quantile(boot,[.025,.975])]))
metadata=dict(runs=len(runs),seeds=30,severities=[.04,.12,.24],graph_nodes=len(e.nodes),graph_edges=e.g.number_of_edges(),summary=summary,comparisons=comparisons,elapsed_seconds=round(time.time()-start,2),python=platform.python_version(),roads_sha256=hashlib.sha256((R/'data/roads.geojson').read_bytes()).hexdigest(),scope='深圳现状OSM路网上的合成灾情实验；真实道路几何，合成需求、车辆与阻断。不能解释为真实救灾成效。主动核查为影响分数启发式；未训练预测模型。',limitations=['单片城区，尚无跨城外部验证','固定22km/h演练速度，非实测行程时间','核查结果假设可靠且每条耗时2分钟','各车辆只接收自身发现的路况，未模拟实时消息同步','图内不含全部车辆限行属性；非真实导航服务'])
(R/'data/experiment_runs.json').write_text(json.dumps(runs,ensure_ascii=False),encoding='utf-8')
(R/'data/experiment_summary.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
with (R/'data/experiment_runs.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(runs[0]));w.writeheader();w.writerows(runs)
print(json.dumps(metadata,ensure_ascii=False,indent=2),flush=True)
