from pathlib import Path
import sys,json,time,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator
from condensate import fit_profile,tetra_mask
from return_sampling import precision_pilot
job='99188cc153094acfc0b4'
reports=[]
for ix in [0,64,127]:
    rawpath=ROOT/'data/geometry'/f'{job}_{ix}.npz';g=np.load(rawpath);meta=json.loads(str(g['metadata']))
    fit=fit_profile(meta['validation']['spatial_volume']);mask=tetra_mask(g['time'],g['tetra'],fit)
    start=time.perf_counter();r=precision_pilot(operator(g['neighbors']),256,np.flatnonzero(mask),55000+ix,(9,64))
    rec={'configuration':f'{job}_{ix}','window':[9,64],'relative_se_target':.02,'history':r['history'],'precision_pass':r['precision_pass'],'seconds':time.perf_counter()-start}
    reports.append(rec)
    np.savez_compressed(ROOT/'results/tables'/f'{job}_{ix}_precision_pilot.npz',returns=r['returns'],starts=r['starts'],metadata=json.dumps(rec),input_sha256=hashlib.sha256(rawpath.read_bytes()).hexdigest())
(ROOT/'results/tables/exact_start_precision.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
