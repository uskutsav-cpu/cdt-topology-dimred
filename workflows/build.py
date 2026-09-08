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
        text = replace_once(text, 'private:', 'public:\n\tstatic void seed_rng(unsigned s) { rng.seed(s); }\n\tstatic void tune_once() { tune(); }\n\tstatic void save_rng(std::ostream& o) { o << rng << "\\n"; }\n\tstatic void load_rng(std::istream& i) { i >> rng; }\nprivate:')
    if p.name == 'universe.hpp':
        text = replace_once(text, 'private:', 'public:\n\tstatic void seed_rng(unsigned s) { rng.seed(s); }\n\tstatic void save_rng(std::ostream& o) { o << rng << "\\n"; }\n\tstatic void load_rng(std::istream& i) { i >> rng; }\nprivate:')
    if p.name == 'pool.hpp':
        text = text.replace('#include <cstdio>','#include <cstdio>\n#include <iostream>\n#include <type_traits>\n#include <algorithm>')
        text = replace_once(text,'static int capacity;','static int capacity;\n\tstatic int high_water;')
        text = replace_once(text,'auto tmp = first;','auto tmp = first;\n\t\thigh_water=std::max(high_water,tmp+1);')
        methods='''
    static void save_pool(std::ostream& o) {
        static_assert(std::is_trivially_copyable<T>::value,"checkpoint needs trivial storage");
        o.write((char*)&high_water,sizeof(int)); o.write((char*)&first,sizeof(int));
        o.write((char*)&total,sizeof(int)); o.write((char*)elements,sizeof(T)*high_water);
    }
    static void load_pool(std::istream& i) {
        i.read((char*)&high_water,sizeof(int)); i.read((char*)&first,sizeof(int));
        i.read((char*)&total,sizeof(int));
        if(high_water<0 || high_water>capacity || first<0 || first>=capacity || total<0 || total>high_water) throw std::runtime_error("invalid checkpoint pool");
        i.read((char*)elements,sizeof(T)*high_water);
    }
'''
        text=replace_once(text,'static int size() noexcept { return total; }',methods+'\n\tstatic int size() noexcept { return total; }')
        text+='\ntemplate<class T> int Pool<T>::high_water{0};\n'
    if p.name == 'bag.hpp':
        text=text.replace('#include <random>','#include <random>\n#include <iostream>')
        methods='''
    void save_bag(std::ostream& o) {
        o.write((char*)&size_,sizeof(size_)); o.write((char*)elements.data(),sizeof(Label)*size_);
    }
    void load_bag(std::istream& i) {
        i.read((char*)&size_,sizeof(size_)); if(size_>N) throw std::runtime_error("invalid checkpoint bag");
        i.read((char*)elements.data(),sizeof(Label)*size_); indices.fill(EMPTY);
        for(unsigned j=0;j<size_;j++) { if(elements[j]<0 || elements[j]>=N) throw std::runtime_error("invalid bag label"); indices[elements[j]]=j; }
    }
'''
        text=replace_once(text,'int size() const noexcept {',methods+'\n\t   int size() const noexcept {')
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
for name in ['runner.cpp','checkpoint.hpp']:
    source=ROOT/'src/cdt'/name;dest=BUILD/name
    if not dest.exists() or dest.read_bytes()!=source.read_bytes(): shutil.copy2(source,dest)
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
