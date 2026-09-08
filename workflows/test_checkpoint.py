from pathlib import Path
import os,subprocess,tempfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1];exe=ROOT/'build/simulator/cdt-run'
def hashes(p):return {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('geometry_*.dat')}
with tempfile.TemporaryDirectory(dir=ROOT/'build') as tmp:
    root=Path(tmp);full=root/'full';full.mkdir()
    def command(out):return [str(exe),str(ROOT/'data/raw/initial_T8.dat'),str(out),'117','1','1','300','20','30','5','500','0','1']
    subprocess.run(command(full),check=True,stdout=subprocess.DEVNULL)
    results=[]
    for stop in [13,52]:
        part=root/f'stop{stop}';part.mkdir();env={**os.environ,'CDT_STOP_AFTER_SWEEP':str(stop)}
        first=subprocess.run(command(part),env=env,stdout=subprocess.DEVNULL)
        assert first.returncode==75
        subprocess.run(command(part),check=True,stdout=subprocess.DEVNULL)
        assert hashes(full)==hashes(part)
        results.append({'stop_after_sweep':stop,'identical_snapshots':len(hashes(full)),'pass':True,'checkpoint_bytes':(part/'checkpoint.bin').stat().st_size})
    (ROOT/'results/tables/checkpoint_tests.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results))
