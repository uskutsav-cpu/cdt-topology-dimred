"""Compare completed baseline chains without re-running any simulation."""
from pathlib import Path
import sys,argparse,json,hashlib,io
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from diagnostics import summary,rank_split_rhat
ap=argparse.ArgumentParser();ap.add_argument('jobs',nargs='+');a=ap.parse_args()
if len(a.jobs)<2 or len(set(a.jobs))!=len(a.jobs):raise ValueError('distinct independent jobs required')
chains=[];inputs={};parameters=[];lineage=[];physical_ids=[]
for job in a.jobs:
    m=json.loads((ROOT/'results/manifests'/f'{job}.json').read_text())
    if m['status']!='complete':raise RuntimeError(f'{job} is not complete; leave its process running')
    c=m['parameters'];parameters.append((c['k0'],c['target'],c['attempts']))
    physical_ids.append(m['configuration_id'])
    p=ROOT/'data/raw'/m['configuration_id']/'diagnostics.csv'
    cutoff=c['tune']+c['burn']+c['samples']*c.get('sample_stride',1)
    # Extensions append sweeps; verify the completed revision's exact prefix.
    lines=p.read_bytes().splitlines(keepends=True);selected=[lines[0]]
    for line in lines[1:]:
        if int(line.split(b',',1)[0])>cutoff:break
        selected.append(line)
    payload=b''.join(selected);inputs[job]=hashlib.sha256(payload).hexdigest()
    assert inputs[job]==m['output_hashes'][str(p.relative_to(ROOT))], 'completed diagnostic prefix changed'
    d=np.genfromtxt(io.StringIO(payload.decode()),names=True,delimiter=',',dtype=None,encoding='utf8')
    _,ix=np.unique(d['sweep'],return_index=True);d=d[np.sort(ix)];d=d[d['phase']=='measure']
    chains.append(d);lineage.append({k:m.get(k) for k in ['configuration_id','seed','rng_origin','initial_checkpoint_sha256']})
if len(set(physical_ids))!=len(physical_ids):raise ValueError('two revisions of one physical chain are not independent')
if len(set(parameters))!=1:raise ValueError('compare identical k0, target volume and attempted moves per sweep')
n=min(map(len,chains));rows={}
for key in ['N0','N3','N31','peak_slice']:
    # Compare common prefixes, preserving initial post-burn measurements.
    x=np.array([d[key][:n] for d in chains]);half=n//2
    split_ess=[summary(v)['effective_samples'] for row in x for v in [row[:half],row[-half:]]]
    rhat=rank_split_rhat(x)
    rows[key]={'rank_folded_split_rhat':rhat,'rhat_below_1p01':bool(np.isfinite(rhat) and rhat<1.01),'minimum_split_single_chain_ess':min(split_ess),'split_ess_at_least_50':min(split_ess)>=50,'full_chain_summaries':[summary(d[key]) for d in chains]}
record={'status':'diagnostic comparison, not automatic equilibrium certification','jobs':a.jobs,'common_prefix_sweeps':n,'input_sha256':inputs,'lineage':lineage,'observables':rows,'notes':'Two chains provide a first check; four overdispersed chains are recommended by the Rhat reference. Single-chain ESS is not multichain bulk/tail ESS. Confirm same model/time extent and genuinely independent RNGs from manifests before interpretation.'}
key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:12]
out=ROOT/'results/tables'/f'chain_comparison_{key}.json'
if out.exists():assert json.loads(out.read_text())==record
else:out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
