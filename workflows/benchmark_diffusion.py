"""Measured estimator comparison on one actual pilot CDT geometry."""
import time,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator,exact_returns,hutchinson,walkers
raw=np.load(ROOT/'data/geometry/6e6f2fe5d7f4709d8982_0.npz'); nb=raw['neighbors'];M=operator(nb)
starts=np.random.default_rng(717).choice(len(nb),256,replace=False);mask=np.zeros(len(nb),bool);mask[starts]=True
records=[];begin=time.perf_counter();truth=exact_returns(M,128,starts).mean(axis=0)
records.append({'method':'exact_256_fixed_starts','seconds':time.perf_counter()-begin,'max_relative_error':0.})
for R in [4,8,16,32,64,128,256]:
    begin=time.perf_counter();H=hutchinson(M,128,R,5100,mask);mean=H.mean(axis=0);se=H.std(axis=0,ddof=1)/np.sqrt(R)
    records.append({'method':'hutchinson','probes':R,'seconds':time.perf_counter()-begin,'max_relative_error':float(np.max(abs(mean[9:65]-truth[9:65])/truth[9:65])),'max_relative_se':float(np.max(se[9:65]/truth[9:65])),'max_standardized_error':float(np.max(abs(mean[1:]-truth[1:])/np.maximum(se[1:],1e-15)))})
begin=time.perf_counter();W=walkers(nb,128,500000,731,starts=starts)
se=np.sqrt(truth*(1-truth)/500000)
records.append({'method':'walkers','walks':500000,'seconds':time.perf_counter()-begin,'max_relative_error':float(np.max(abs(W[9:65]-truth[9:65])/truth[9:65])),'max_standardized_error':float(np.max(abs(W[1:]-truth[1:])/np.maximum(se[1:],1e-15)))})
path=ROOT/'results/tables/diffusion_benchmark.json';path.write_text(json.dumps(records,indent=2)+'\n')
np.savez_compressed(ROOT/'results/tables/diffusion_benchmark_raw.npz',exact=truth,walker=W,last_hutchinson_probes=H,starts=starts)
print(json.dumps(records,indent=2))
assert records[-1]['max_standardized_error']<5
# Four-probe estimated SE can vanish accidentally and is not a reliable test.
assert records[-2]['max_standardized_error']<5
