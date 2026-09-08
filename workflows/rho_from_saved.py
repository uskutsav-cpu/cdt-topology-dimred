"""Diffusion-rate sensitivity using cached returns and binomial thinning."""
from pathlib import Path
import sys,argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import dimension
from spectral_thinning import thin_returns
ap=argparse.ArgumentParser();ap.add_argument('job');ap.add_argument('--total',required=True,type=int);ap.add_argument('--stride',type=int,default=4);a=ap.parse_args()
curves=[];inputs={}
for ix in range(0,a.total,a.stride):
    p=ROOT/'results/tables'/f'{a.job}_{ix}_condensate_exact_n512_s256.npz'
    data=np.load(p);meta=json.loads(str(data['metadata']))
    assert meta['rho']==.8 and meta['operator']=='full microscopic graph'
    curves.append(data['returns'].mean(axis=0));inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
P=np.array(curves);result={};rows=[];records=[];ref=dimension(P.mean(axis=0));grid=np.linspace(8,80,145)
for rho in [.2,.4,.6,.8]:
    steps=int(np.ceil(128*.8/rho));out,tail=thin_returns(P,rho/.8,steps)
    sigma=np.arange(steps+1);ds=dimension(out.mean(axis=0));historical=dimension(out).mean(axis=0)
    result[f'P_rho_{rho}']=out;eligible=np.flatnonzero((rho*sigma>=8)&np.isfinite(ds));peak=eligible[np.argmax(ds[eligible])]
    valid=np.isfinite(ds);basevalid=np.isfinite(ref)
    delta=np.interp(grid,sigma[valid]*rho,ds[valid])-np.interp(grid,np.arange(len(ref))[basevalid]*.8,ref[basevalid])
    records.append({'rho':rho,'maximum_absolute_truncation_bound':float(tail.max()),'peak_Ds_scaled_time_ge_8':float(ds[peak]),'peak_sigma':int(peak),'peak_scaled_sigma':float(rho*peak),'rms_Ds_difference_vs_rho0p8_scaled_time_8_80':float(np.sqrt(np.mean(delta**2)))})
    rows.extend(zip(np.full(steps+1,rho),sigma,rho*sigma,out.mean(axis=0),ds,historical,tail))
label=f'{a.job}_rho_thinning_total{a.total}_stride{a.stride}'
np.savetxt(ROOT/'results/tables'/f'{label}.csv',rows,delimiter=',',header='rho,sigma,rho_sigma,P_mean,Ds_of_mean_P,mean_Ds,absolute_truncation_bound',comments='')
np.savez_compressed(ROOT/'results/tables'/f'{label}.npz',**result)
record={'status':'baseline sensitivity on non-certified ensemble','method':'binomial thinning of rho=.8 full-graph returns; shared starting points','configurations':len(P),'source_sha256':hashlib.sha256((ROOT/'src/spectral_thinning.py').read_bytes()).hexdigest(),'inputs':inputs,'comparisons':records}
(ROOT/'results/tables'/f'{label}.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'configurations':len(P),'comparisons':records}))
