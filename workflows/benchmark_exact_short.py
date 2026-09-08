from pathlib import Path
import sys,time,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator
from spectral_exact_short import diagonal_returns
p=ROOT/'data/geometry/99188cc153094acfc0b4_0.npz';g=np.load(p)
t=time.perf_counter();P,report=diagonal_returns(operator(g['neighbors']),64)
report['seconds']=time.perf_counter()-t;report['N3']=len(g['neighbors'])
old=np.load(ROOT/'results/tables/99188cc153094acfc0b4_0_condensate_exact_n512_s256.npz')
assert np.allclose(P[old['starts']],old['returns'][:,:P.shape[1]],rtol=1e-11,atol=1e-13)
report['crosscheck_512_basis_starts']=True
np.savez_compressed(ROOT/'results/tables/99188cc153094acfc0b4_0_exact_short.npz',returns=P,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),metadata=json.dumps(report))
(ROOT/'results/tables/exact_short_benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
