"""Descriptive comparison of saved baseline spectra, not a convergence test."""
from pathlib import Path
import numpy as np,json,hashlib,argparse
root=Path(__file__).resolve().parents[1]/'results/tables'
ap=argparse.ArgumentParser();ap.add_argument('jobs',nargs=2);a=ap.parse_args()
tables=[];inputs={}
for j in a.jobs:
 p=root/f'{j}_n512_s256_stride4_aggregate.csv';tables.append(np.genfromtxt(p,names=True,delimiter=','));inputs[j]=hashlib.sha256(p.read_bytes()).hexdigest()
x,y=tables
assert np.array_equal(x['sigma'],y['sigma'])
delta=y['Ds_of_mean_P']-x['Ds_of_mean_P'];relative=y['P_mean']/x['P_mean']-1
np.savetxt(root/'independent_baseline_spectral_comparison.csv',np.column_stack((x['sigma'],x['P_mean'],y['P_mean'],x['Ds_of_mean_P'],y['Ds_of_mean_P'],delta,relative)),delimiter=',',header='sigma,P_chain1,P_chain2,Ds_chain1,Ds_chain2,Ds_chain2_minus_chain1,relative_P_difference',comments='')
r={'status':'descriptive comparison; slow-mode convergence not established','jobs':a.jobs,'configurations_per_chain':32,'starts_per_configuration':512,'input_sha256':inputs,'maximum_absolute_Ds_difference_sigma_9_64':float(abs(delta[9:65]).max()),'maximum_relative_P_difference_sigma_9_64':float(abs(relative[9:65]).max()),'peak_Ds_sigma_ge_10':[float(np.nanmax(v['Ds_of_mean_P'][10:])) for v in tables]}
(root/'independent_baseline_spectral_comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
