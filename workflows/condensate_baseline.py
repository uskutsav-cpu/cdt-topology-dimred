"""Baseline stalk/boundary sensitivity, with raw curves and frozen definitions."""
from pathlib import Path
import sys,json,hashlib,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/mpl'))
import numpy as np
from condensate import fit_profile,tetra_mask,excised_operator
from spectral import operator,exact_returns,dimension
job=sys.argv[1]
assert json.loads((ROOT/'results/manifests'/f'{job}.json').read_text())['status']=='complete'
paths=sorted((ROOT/'data/geometry').glob(f'{job}_*.npz'),key=lambda p:int(p.stem.split('_')[-1]))
indices=np.linspace(0,len(paths)-1,8,dtype=int)
all_curves=[];reports=[]
names=['condensate_starts_full_operator','excised_renormalize','excised_hold','excised_radius_minus1','excised_radius_plus1','excised_rho0.4']
sourcehash=hashlib.sha256(b''.join((ROOT/'src'/p).read_bytes() for p in ['spectral/__init__.py','condensate.py'])).hexdigest()
for ix in indices:
    p=paths[ix];g=np.load(p);meta=json.loads(str(g['metadata']));nb=g['neighbors'];profile=meta['validation']['spatial_volume'];fit=fit_profile(profile)
    mask=tetra_mask(g['time'],g['tetra'],fit)
    record={'configuration':p.stem,**{k:v for k,v in fit.items() if k not in ['slice_mask','fitted_profile']},'fraction_condensate':float(mask.mean())}
    reports.append(record)
    if not fit['resolved_stalk']: raise RuntimeError(f'unresolved stalk: {p.stem}')
    dest=ROOT/'results/tables'/f'{p.stem}_condensate_sensitivity.npz'
    inputhash=hashlib.sha256(p.read_bytes()).hexdigest()
    if dest.exists():
        old=np.load(dest);assert str(old['input_sha256'])==inputhash and str(old['source_sha256'])==sourcehash
        curves=old['curves']
    else:
        curves=[]
        rng=np.random.default_rng(12000+ix)
        for name in names:
            rho=.4 if name.endswith('rho0.4') else .8
            shift=-1 if name.endswith('minus1') else 1 if name.endswith('plus1') else 0
            current=tetra_mask(g['time'],g['tetra'],fit,shift)
            if name=='condensate_starts_full_operator':
                M=operator(nb,rho);ids=np.flatnonzero(current)
            else:
                M,oldids=excised_operator(nb,current,rho,'hold' if name=='excised_hold' else 'renormalize');ids=np.arange(len(oldids))
            starts=rng.choice(ids,min(128,len(ids)),replace=False)
            curves.append(exact_returns(M,512,starts).mean(axis=0))
        curves=np.array(curves)
        np.savez_compressed(dest,curves=curves,names=names,mask=mask,profile=profile,fitted=fit['fitted_profile'],fit=json.dumps(record),input_sha256=inputhash,source_sha256=sourcehash)
    all_curves.append(curves)
all_curves=np.array(all_curves);means=all_curves.mean(axis=0);Ds=dimension(means)
(ROOT/'results/tables'/f'{job}_condensate_fits.json').write_text(json.dumps(reports,indent=2)+'\n')
np.savetxt(ROOT/'results/tables'/f'{job}_condensate_sensitivity.csv',np.column_stack((np.arange(513),Ds.T)),delimiter=',',header='sigma,'+','.join(names),comments='')
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,ax=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
for i,name in enumerate(names):
    x=np.arange(513)*(.5 if name.endswith('rho0.4') else 1)
    ax[0].semilogx(x,Ds[i],label=name.replace('_',' '),lw=1)
ax[0].set(xlabel=r'$\sigma\rho/0.8$',ylabel=r'$D_s$',ylim=(1,3.5));ax[0].legend(fontsize=6.5);ax[0].axhline(3,color='gray',ls=':')
sample=np.load(ROOT/'results/tables'/f'{paths[indices[0]].stem}_condensate_sensitivity.npz')
ax[1].plot(sample['profile'],'o',ms=3,label='Measured spatial volume');ax[1].plot(sample['fitted'],label='Cos²/constant fit');ax[1].set(xlabel='Time slice (periodic)',ylabel='Spatial triangles');ax[1].legend(fontsize=8)
fig.suptitle('Exploratory baseline: explicit stalk and boundary conventions')
fig.savefig(ROOT/'results/figures'/f'{job}_condensate_sensitivity.pdf');fig.savefig(ROOT/'results/figures'/f'{job}_condensate_sensitivity.png',dpi=150)
print(json.dumps({'peak_Ds_sigma_ge_10':dict(zip(names,np.nanmax(Ds[:,10:],axis=1))),'fit_RMSE':[r['relative_rmse'] for r in reports]}))
