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
    ap=argparse.ArgumentParser(); ap.add_argument('config'); args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text()); exe=ROOT/'build/simulator/cdt-run'; inp=ROOT/cfg['input']
    contract={'parameters':cfg,'binary_sha256':sha(exe),'input_sha256':sha(inp),'driver_sha256':sha(__file__)}
    job=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()[:20]
    manifest=ROOT/'results/manifests'/f'{job}.json'
    if manifest.exists():
        old=json.loads(manifest.read_text())
        if old['status']=='complete':
            for f,h in old['output_hashes'].items():
                if sha(ROOT/f)!=h: raise RuntimeError(f'completed output corrupted: {f}')
            print(f'SKIP verified {job}'); return
        raise RuntimeError(f'Previous incomplete job {job}: preserve raw files; inspect failure before a new chain.')
    out=ROOT/'data/raw'/job; out.mkdir()
    rec={**contract,'experiment_id':cfg['name'],'configuration_id':job,'stage':'simulation','status':'running','seed':cfg['seed'],'started_at':now(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip(),'platform':platform.platform()}
    manifest.write_text(json.dumps(rec,indent=2)+'\n')
    command=[str(exe),str(inp),str(out),*[str(cfg[k]) for k in ['seed','k0','k3','target','tune','burn','samples','attempts','check_every_move']]]
    rec['command']=command; start=time.perf_counter()
    try:
        with open(ROOT/'logs'/f'{job}.log','x') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=cfg.get('timeout_seconds',3600))
        reports=[]
        for p in sorted(out.glob('geometry_*.dat')):
            idx=int(p.stem.split('_')[1]); dest=ROOT/'data/geometry'/f'{job}_{idx}.npz'
            reports.append(export_npz(p,dest,{**cfg,'configuration_id':f'{job}_{idx}','sweep':cfg['tune']+cfg['burn']+idx+1,'binary_sha256':sha(exe)}))
        assert len(reports)==cfg['samples']
        rec['geometry_validation']=reports
        rec['status']='complete'
    except Exception as e:
        rec['status']='failed'; rec['error']=repr(e); raise
    finally:
        rec['elapsed_seconds']=time.perf_counter()-start; rec['completed_at']=now()
        outputs=list(out.glob('*'))+list((ROOT/'data/geometry').glob(f'{job}_*.npz'))
        rec['output_hashes']={str(p.relative_to(ROOT)):sha(p) for p in outputs}
        manifest.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({'job':job,'elapsed':rec['elapsed_seconds'],'N3':[r['N3'] for r in reports]}))

if __name__=='__main__': main()
