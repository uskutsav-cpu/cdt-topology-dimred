from pathlib import Path
import subprocess,json
ROOT=Path(__file__).resolve().parents[1]; build=ROOT/'build/simulator'
objects=[str(p) for p in build.glob('*.o') if p.stem!='runner']
exe=build/'test-inverse'
subprocess.run(['c++','-std=c++14','-O2','-I'+str(build),str(ROOT/'tests/move_inverse.cpp'),*objects,'-o',str(exe)],check=True)
out=[]
for kind in ['26','44','23u','23d']:
    proc=subprocess.run([str(exe),str(ROOT/'data/raw/6e6f2fe5d7f4709d8982/geometry_0.dat'),kind],capture_output=True,text=True)
    out.append({'move_pair':kind,'returncode':proc.returncode,'output':proc.stdout[-160:],'error':proc.stderr})
(ROOT/'results/tables/move_inverse_tests.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
assert all(r['returncode']==0 for r in out)
