"""Immutable independent-chain jobs; completed jobs are verified and skipped."""
import argparse, hashlib, json, subprocess, time, sys, platform
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from geometry import read_geometry,validate,export_npz

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('config'); ap.add_argument('--resume',action='store_true'); ap.add_argument('--extend-job'); args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text()); exe=ROOT/'build/simulator/cdt-run'; inp=ROOT/cfg['input']
    cfg.setdefault('sample_stride',1)
    contract={'parameters':cfg,'binary_sha256':sha(exe),'input_sha256':sha(inp),'driver_sha256':sha(__file__)}
    job=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()[:20]
    if args.extend_job:
        job=args.extend_job
        if not (len(job)==20 and all(c in '0123456789abcdef' for c in job)):raise ValueError('invalid job id')
    manifest=ROOT/'results/manifests'/f'{job}.json'
    previous=None
    history=[];base_elapsed=0.
    if manifest.exists():
        old=json.loads(manifest.read_text())
        if old['status']=='complete':
            for f,h in old['output_hashes'].items():
                if sha(ROOT/f)!=h: raise RuntimeError(f'completed output corrupted: {f}')
            if not args.extend_job:
                print(f'SKIP verified {job}'); return
            assert old['binary_sha256']==contract['binary_sha256'] and old['input_sha256']==contract['input_sha256']
            assert {k:v for k,v in old['parameters'].items() if k!='samples'}=={k:v for k,v in cfg.items() if k!='samples'}, 'extension may only increase samples'
            assert cfg['samples']>old['parameters']['samples'] and (ROOT/'data/raw'/job/'checkpoint.bin').exists()
            revision=manifest.with_name(job+f".through_{old['parameters']['samples']}.json")
            if not revision.exists():revision.write_bytes(manifest.read_bytes())
            previous={'manifest':str(revision.relative_to(ROOT)),'sha256':sha(revision),'completed_samples':old['parameters']['samples'],'elapsed_seconds':old.get('total_elapsed_seconds',old['elapsed_seconds'])}
        elif not (args.resume and old['status']=='failed' and (ROOT/'data/raw'/job/'checkpoint.bin').exists()):
            raise RuntimeError(f'Previous incomplete job {job}: --resume requires a failed job with a checkpoint.')
        if args.resume:
            previous=old.get('previous_revision')
        base_elapsed=old.get('total_elapsed_seconds',old.get('elapsed_seconds',0.))
        history=old.get('attempt_history',[])+[{k:old.get(k) for k in ['status','started_at','completed_at','elapsed_seconds','error']}]
    elif args.extend_job:raise ValueError('extension requires a completed job')
    out=ROOT/'data/raw'/job; out.mkdir(exist_ok=args.resume or bool(args.extend_job))
    rec={**contract,'experiment_id':cfg['name'],'configuration_id':job,'stage':'simulation','status':'running','seed':cfg['seed'],'started_at':now(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip(),'platform':platform.platform()}
    if previous:rec['previous_revision']=previous
    rec['attempt_history']=history
    manifest.write_text(json.dumps(rec,indent=2)+'\n')
    command=[str(exe),str(inp),str(out),*[str(cfg[k]) for k in ['seed','k0','k3','target','tune','burn','samples','attempts','check_every_move','sample_stride']]]
    rec['command']=command; start=time.perf_counter()
    try:
        with open(ROOT/'logs'/f'{job}.log','a' if args.resume or args.extend_job else 'x') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=cfg.get('timeout_seconds',3600))
        reports=[]
        for p in sorted(out.glob('geometry_*.dat')):
            idx=int(p.stem.split('_')[1]); dest=ROOT/'data/geometry'/f'{job}_{idx}.npz'
            if dest.exists():
                import numpy as np
                saved=json.loads(str(np.load(dest)['metadata']))
                assert saved['input_sha256']==sha(p)
                reports.append(saved['validation'])
            else:
                reports.append(export_npz(p,dest,{**cfg,'configuration_id':f'{job}_{idx}','sweep':cfg['tune']+cfg['burn']+(idx+1)*cfg['sample_stride'],'binary_sha256':sha(exe)}))
        assert len(reports)==cfg['samples']
        rec['geometry_validation']=reports
        rec['status']='complete'
    except Exception as e:
        rec['status']='failed'; rec['error']=repr(e); raise
    finally:
        rec['elapsed_seconds']=time.perf_counter()-start; rec['completed_at']=now()
        rec['total_elapsed_seconds']=rec['elapsed_seconds']+base_elapsed
        outputs=list(out.glob('*'))+list((ROOT/'data/geometry').glob(f'{job}_*.npz'))
        rec['output_hashes']={str(p.relative_to(ROOT)):sha(p) for p in outputs}
        manifest.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({'job':job,'elapsed':rec['elapsed_seconds'],'N3':[r['N3'] for r in reports]}))

if __name__=='__main__': main()
