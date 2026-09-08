"""Build a documented, minimally patched copy; never modify pinned upstream."""
from pathlib import Path
import subprocess, shutil, json, hashlib

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT/'external/3d-cdt'
BUILD = ROOT/'build/simulator'
BUILD.mkdir(parents=True, exist_ok=True)
def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)

changes = {}
for p in list(UP.glob('*.cpp')) + list(UP.glob('*.hpp')):
    if p.name == 'main.cpp': continue
    text = original = p.read_text()
    if p.name == 'simulation.hpp':
        text = replace_once(text, 'private:', 'public:\n\tstatic void seed_rng(unsigned s) { rng.seed(s); }\n\tstatic void tune_once() { tune(); }\nprivate:')
    if p.name == 'universe.hpp':
        text = replace_once(text, 'private:', 'public:\n\tstatic void seed_rng(unsigned s) { rng.seed(s); }\nprivate:')
    if p.name == 'simulation.cpp':
        # Eq. 26/27 of arXiv:2310.16744, with the current (pre-move) counts.
        text = replace_once(text, 'double rg = n31 / (n31 + 2.0);', 'double rg = n31 / (Universe::verticesAll.size() + 1.0);')
        text = replace_once(text, 'double rg = n31/(n31-2.0);', 'double rg = Universe::verticesAll.size()/(n31-2.0);')
        # exp[-epsilon*((V+dV-target)^2-(V-target)^2)] for deletion.
        text = replace_once(text, 'exp(-4 * epsilon * (targetVolume - n31 - 1))', 'exp(-4 * epsilon * (targetVolume - n31 + 1))')
        text = replace_once(text, 'exp(-8 * epsilon * (targetVolume - n3 - 2))', 'exp(-8 * epsilon * (targetVolume - n3 + 2))')
        assert text.count('exp(-epsilon * (2 * targetVolume - 2 * n3 - 1))') == 2
        text = text.replace('exp(-epsilon * (2 * targetVolume - 2 * n3 - 1))', 'exp(-epsilon * (2 * targetVolume - 2 * n3 + 1))')
    dest = BUILD/p.name
    if not dest.exists() or dest.read_text() != text: dest.write_text(text)
    if text != original: changes[p.name] = {'upstream_sha256':hashlib.sha256(original.encode()).hexdigest(), 'patched_sha256':hashlib.sha256(text.encode()).hexdigest()}
shutil.copy2(ROOT/'src/cdt/runner.cpp', BUILD/'runner.cpp')
sources = list(BUILD.glob('*.cpp'))
objects = []
headers_mtime = max(p.stat().st_mtime for p in BUILD.glob('*.hpp'))
for p in sources:
    o = p.with_suffix('.o'); objects.append(str(o))
    if not o.exists() or o.stat().st_mtime < max(headers_mtime,p.stat().st_mtime):
        subprocess.run(['c++','-std=c++14','-O3','-Wno-format','-c',str(p),'-o',str(o)], check=True)
subprocess.run(['c++',*objects,'-o',str(BUILD/'cdt-run')],check=True)
(ROOT/'environment/simulator_patch.json').write_text(json.dumps(changes,indent=2)+'\n')
print(BUILD/'cdt-run')
