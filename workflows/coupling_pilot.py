"""Descriptive fixed-target-volume coupling comparison from saved curves."""
from pathlib import Path
import json,hashlib,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];T=ROOT/'results/tables'
rows=[];inputs={};pending=[];curves=[]
for job,k0 in [('590bcc4ae5515ad24761',.5),('dc0bd0d263f25696be2d',1.),('d98f6ba3a813c6c7f098',1.5),('029620366a1c017aaa4b',2.),('4f7a75be6ed25248ce1e',2.5)]:
    p=T/f'{job}_n512_s256_stride8_aggregate.csv'
    if not p.exists():pending.append(job);continue
    a=np.genfromtxt(p,names=True,delimiter=',');inputs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest();vols=[];cond=[]
    for i in range(0,128,8):
        q=T/f'{job}_{i}_condensate_exact_n512_s256.npz';b=np.load(q);inputs[q.name]=hashlib.sha256(q.read_bytes()).hexdigest();vols.append(len(b['mask']));cond.append(int(b['mask'].sum()))
    valid=np.flatnonzero((a['sigma']>=10)&np.isfinite(a['Ds_of_mean_P']));peak=valid[np.argmax(a['Ds_of_mean_P'][valid])]
    rows.append({'job':job,'k0':k0,'T':64,'target_N3':30000,'rho':.8,'configurations':16,'mean_total_N3':float(np.mean(vols)),'mean_condensate_N3':float(np.mean(cond)),'peak_Ds':float(a['Ds_of_mean_P'][peak]),'peak_sigma':int(a['sigma'][peak]),'Ds_sigma15':float(a['Ds_of_mean_P'][15]),'Ds_sigma25':float(a['Ds_of_mean_P'][25]),'convergence_established':False})
    curves.extend(zip(np.full(len(a),k0),a['sigma'],a['P_mean'],a['Ds_of_mean_P'],a['mean_Ds']))
with (T/'coupling_pilot.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
np.savetxt(T/'coupling_pilot_curves.csv',curves,delimiter=',',header='k0,sigma,P_mean,Ds_of_mean_P,mean_Ds',comments='')
r={'status':'descriptive pilot; not a coupling-reproduction pass','rows':rows,'pending_measurements':pending,'input_sha256':inputs}
(T/'coupling_pilot.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'rows':rows,'pending':pending}))
