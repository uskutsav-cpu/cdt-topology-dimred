"""Remove start-sampling noise from a bounded baseline variance pilot."""
from pathlib import Path
import sys,json,hashlib,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator
from spectral_exact_short import diagonal_returns,batched_diagonal_returns
job='99188cc153094acfc0b4';exact=[];sampled=[];sampling_variance=[]
record_path=ROOT/'results/tables/precision_variance.json'
runs=json.loads(record_path.read_text()).get('new_computations',[]) if record_path.exists() else []
for ix in [0,5,50,100,150,200,250,300]:
    source=ROOT/'data/geometry'/f'{job}_{ix}.npz';inp=hashlib.sha256(source.read_bytes()).hexdigest()
    out=ROOT/'results/tables'/f'{job}_{ix}_exact_short.npz';P=None
    if out.exists():
        old=np.load(out)
        if str(old['input_sha256'])==inp and old['returns'].shape[1]>=27:P=old['returns'][:,:27]
    if P is None:
        g=np.load(source);M=operator(g['neighbors']);t=time.perf_counter()
        P,report=diagonal_returns(M,26,32_000_000)
        if report['computed_steps']!=26:P,report=batched_diagonal_returns(M,26)
        report['seconds']=time.perf_counter()-t
        np.savez_compressed(out,returns=P,input_sha256=inp,metadata=json.dumps(report),source_sha256=hashlib.sha256((ROOT/'src/spectral_exact_short.py').read_bytes()).hexdigest())
        runs.append({'configuration':ix,'seconds':report['seconds']})
    sample=np.load(ROOT/'results/tables'/f'{job}_{ix}_condensate_exact_n512_s256.npz')
    assert np.allclose(P[sample['starts']],sample['returns'][:,:27],rtol=1e-11,atol=1e-13)
    mask=sample['mask'];v=sample['returns'][:,:27];N=mask.sum();n=len(v)
    exact.append(P[mask].mean(axis=0));sampled.append(v.mean(axis=0));sampling_variance.append(v.var(axis=0,ddof=1)/n*(N-n)/N)
exact=np.array(exact);sampled=np.array(sampled);sv=np.array(sampling_variance)
rows=[]
for s in [9,15,17,20,25]:
    var=exact[:,s].var(ddof=1)
    rows.append({'sigma':s,'exact_between_configuration_sd':float(np.sqrt(var)),'mean_sampling_se_512':float(np.sqrt(sv[:,s].mean())),'sampling_variance_over_exact_geometry_variance':float(sv[:,s].mean()/var)})
record={'status':'precision pilot, nonthermalized geometries','configurations':8,'exact_steps':26,'comparison':rows,'new_computations':runs}
(ROOT/'results/tables/precision_variance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
