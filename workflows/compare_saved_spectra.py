"""Descriptive comparison of saved baseline spectra, not a convergence test."""
from pathlib import Path
import numpy as np,json,hashlib,argparse
root=Path(__file__).resolve().parents[1]/'results/tables'
ap=argparse.ArgumentParser();ap.add_argument('jobs',nargs=2)
ap.add_argument('--total',type=int,default=128);ap.add_argument('--stride',type=int,default=4);a=ap.parse_args()
if a.total<1 or a.stride<1 or a.jobs[0]==a.jobs[1]:raise ValueError('positive schedule and distinct chains required')
tables=[];inputs={}
for j in a.jobs:
 label=f'{j}_n512_s256_stride{a.stride}'
 report=json.loads((root/f'{label}_measurement.json').read_text())
 expected=[f'{j}_{ix}' for ix in range(0,a.total,a.stride)]
 if report['pending'] or report['total_requested_snapshots']!=a.total or [v['configuration'] for v in report['checks']]!=expected:
  raise RuntimeError('completed measurement set does not match requested schedule')
 p=root/f'{label}_aggregate.csv';tables.append(np.genfromtxt(p,names=True,delimiter=','));inputs[j]=hashlib.sha256(p.read_bytes()).hexdigest()
x,y=tables
assert np.array_equal(x['sigma'],y['sigma'])
delta=y['Ds_of_mean_P']-x['Ds_of_mean_P'];relative=y['P_mean']/x['P_mean']-1
name='independent_baseline_spectral_comparison'+('' if (a.total,a.stride)==(128,4) else f'_total{a.total}_stride{a.stride}')
np.savetxt(root/f'{name}.csv',np.column_stack((x['sigma'],x['P_mean'],y['P_mean'],x['Ds_of_mean_P'],y['Ds_of_mean_P'],delta,relative)),delimiter=',',header='sigma,P_chain1,P_chain2,Ds_chain1,Ds_chain2,Ds_chain2_minus_chain1,relative_P_difference',comments='')
r={'status':'descriptive comparison; slow-mode convergence not established','jobs':a.jobs,'configurations_per_chain':len(expected),'starts_per_configuration':512,'input_sha256':inputs,'maximum_absolute_Ds_difference_sigma_9_64':float(abs(delta[9:65]).max()),'maximum_relative_P_difference_sigma_9_64':float(abs(relative[9:65]).max()),'peak_Ds_sigma_ge_10':[float(np.nanmax(v['Ds_of_mean_P'][10:])) for v in tables]}
(root/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
