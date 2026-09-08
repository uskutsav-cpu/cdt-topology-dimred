"""Controlled-volume comparison from saved baseline measurements only."""
from pathlib import Path
import json,hashlib,csv,os,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1];T=ROOT/'results/tables'
rows=[];inputs={};curves=[]
parser=argparse.ArgumentParser();parser.add_argument('--include-60000',action='store_true');args=parser.parse_args()
jobs=[('4a40078dbf0e6b9a5f5c',10000,4),('dc0bd0d263f25696be2d',30000,8)]
if args.include_60000:jobs.append(('f045a528fac6359e9df4',60000,8))
name='finite_size_pilot_three_volumes' if args.include_60000 else 'finite_size_pilot'
for job,target,stride in jobs:
    p=T/f'{job}_n512_s256_stride{stride}_aggregate.csv';a=np.genfromtxt(p,names=True,delimiter=',');inputs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    vols=[];cond=[]
    for i in range(0,128,stride):
        q=T/f'{job}_{i}_condensate_exact_n512_s256.npz';b=np.load(q);inputs[q.name]=hashlib.sha256(q.read_bytes()).hexdigest();vols.append(len(b['mask']));cond.append(int(b['mask'].sum()))
    eligible=np.flatnonzero((a['sigma']>=10)&np.isfinite(a['Ds_of_mean_P']));peak=eligible[np.argmax(a['Ds_of_mean_P'][eligible])]
    rows.append({'job':job,'target_N3':target,'T':64,'k0':1.,'rho':.8,'measured_configurations':len(vols),'mean_total_N3':float(np.mean(vols)),'mean_condensate_N3':float(np.mean(cond)),'peak_Ds':float(a['Ds_of_mean_P'][peak]),'peak_sigma':int(a['sigma'][peak]),'Ds_sigma15':float(a['Ds_of_mean_P'][15]),'Ds_sigma25':float(a['Ds_of_mean_P'][25]),'equilibrium_certified':False});curves.append(a)
with (T/f'{name}.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(T/f'{name}.json').write_text(json.dumps({'status':'exploratory; pilot ensembles do not establish asymptotic scaling','rows':rows,'input_sha256':inputs},indent=2)+'\n')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/mpl'))
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
fig,ax=plt.subplots(1,2,figsize=(9,3.7),layout='constrained')
for row,a in zip(rows,curves):
    label=f"Mean condensate N₃ = {row['mean_condensate_N3']:,.0f}"
    use=a['sigma']>=10
    ax[0].loglog(a['sigma'][use],a['P_mean'][use],label=label)
    ax[1].semilogx(a['sigma'][use],a['Ds_of_mean_P'][use],label=label)
ax[0].set(xlabel='Diffusion steps σ',ylabel='Mean return probability')
ax[1].set(xlabel='Diffusion steps σ',ylabel='Spectral dimension',ylim=(2.3,3.1))
ax[1].axhline(3,color='gray',ls=':',lw=1)
for x in ax:x.legend(fontsize=8)
fig.suptitle('Fixed T = 64, k₀ = 1, ρ = 0.8 · pilot ensembles, convergence pending')
for ext in ['pdf','png']:fig.savefig(ROOT/'results/figures'/f'{name}.{ext}',dpi=160)
print(json.dumps(rows))
