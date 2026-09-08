"""Verify V1 checkpoint transfer into a new phase preserves the trajectory."""
from pathlib import Path
import sys,os,subprocess,tempfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1];new=ROOT/'build/simulator/cdt-run';old=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else new
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(dir=ROOT/'build') as tmp:
    p=Path(tmp);full=p/'full';partial=p/'partial';stage=p/'stage'
    for d in [full,partial,stage]:d.mkdir()
    def cmd(exe,out,tune,burn,samples,k3='1'):
        return [str(exe),str(ROOT/'data/raw/initial_T8.dat'),str(out),'117','1',k3,'300',str(tune),str(burn),str(samples),'500','0','1']
    subprocess.run(cmd(old,full,20,30,5),check=True,stdout=subprocess.DEVNULL)
    r=subprocess.run(cmd(old,partial,20,30,5),env={**os.environ,'CDT_STOP_AFTER_SWEEP':'52'},stdout=subprocess.DEVNULL);assert r.returncode==75
    checkpoint=partial/'checkpoint.bin'
    with open(checkpoint,'rb') as f:magic=f.readline();counter=f.readline();k3=f.readline().decode().strip()
    subprocess.run(cmd(new,stage,0,0,3,k3),env={**os.environ,'CDT_INITIAL_CHECKPOINT':str(checkpoint)},check=True,stdout=subprocess.DEVNULL)
    for i in range(3):assert digest(stage/f'geometry_{i}.dat')==digest(full/f'geometry_{i+2}.dat')
    record={'format':'CDT_CHECKPOINT_V1','old_binary_sha256':digest(old),'new_binary_sha256':digest(new),'identical_continuation_snapshots':3,'pass':True}
    (ROOT/'results/tables/stage_transfer_test.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
