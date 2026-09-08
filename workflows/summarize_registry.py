"""Tables from actual completed jobs only; never infer unrun stages."""
from pathlib import Path
import json,csv,sys,platform,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from diagnostics import summary
sim=[];acs=[];thermal=[]
for p in sorted((ROOT/'results/manifests').glob('*.json')):
    if '.through_' in p.name:continue
    m=json.loads(p.read_text())
    if m.get('status')!='complete' or 'parameters' not in m:continue
    c=m['parameters'];job=m['configuration_id']
    sim.append({'experiment':m['experiment_id'],'job':job,'seed':c['seed'],'k0':c['k0'],'initial_k3':c['k3'],'target_N3':c['target'],'tune_sweeps':c['tune'],'burn_sweeps':c['burn'],'saved_configurations':c['samples'],'sample_stride':c.get('sample_stride',1),'attempts_per_sweep':c['attempts'],'elapsed_seconds':m['elapsed_seconds'],'binary_sha256':m['binary_sha256'],'parent_chain':c.get('parent_chain','')})
    d=np.genfromtxt(ROOT/'data/raw'/job/'diagnostics.csv',names=True,delimiter=',',dtype=None,encoding='utf8');_,ix=np.unique(d['sweep'],return_index=True);d=d[np.sort(ix)];d=d[d['phase']=='measure']
    for key in ['N0','N3','N31','peak_slice']:
        if len(d)>=4:acs.append({'job':job,'observable':key,**summary(d[key])})
    thermal.append({'job':job,'measurement_k3_min':float(d['k3'].min()),'measurement_k3_max':float(d['k3'].max()),'frozen_k3':bool(np.ptp(d['k3'])==0),'retained_geometries_valid':len(m['geometry_validation']),'stationarity_certified':False})
def write(name,rows):
    if rows:
        with open(ROOT/'results/tables'/name,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write('simulation_parameters.csv',sim);write('autocorrelation_times.csv',acs);write('thermalization_diagnostics.csv',thermal)
print(f'{len(sim)} completed jobs summarized')
