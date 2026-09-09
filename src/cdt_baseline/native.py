"""Fresh isolated builds from hash-pinned native sources, never editing upstream."""
from __future__ import annotations
from pathlib import Path
import os
import platform
import shutil
import subprocess
import sys
from .io import atomic_json, blob_sha, digest, inventory, load_json, lock, now, sha256, verify_inventory

BASE_COMMIT = '6fafad81840ecb03cc858953352b227d242d5ee1'
UPSTREAM_COMMIT = '5720c0b98d809b35974d5c6fe067a828fe6b1267'


def check_sources(root: Path):
    record=load_json(root/'configs/baseline/source_lock.json')
    for relative,expected in record['git_blobs'].items():
        p=root/relative
        if not p.is_file() or p.is_symlink() or blob_sha(p)!=expected:
            raise ValueError(f'pinned source missing or changed: {relative}')
    checkout={'kind':'hash_verified_source_export','clean_git_checkout':False,'expected_base':BASE_COMMIT}
    if (root/'.git').exists():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=root,text=True)
        ancestry=subprocess.run(['git','merge-base','--is-ancestor',BASE_COMMIT,'HEAD'],cwd=root,capture_output=True).returncode==0
        checkout.update(kind='git_checkout',head=head,clean_git_checkout=not bool(dirty),base_is_ancestor=ancestry,
                        dirty_status=dirty)
        if not ancestry:
            raise ValueError('checkout does not descend from the audited merged baseline')
    return record,checkout


def replace_one(text,old,new):
    if text.count(old)!=1:
        raise ValueError(f'native patch anchor not unique: {old[:80]}')
    return text.replace(old,new)


def build_native(root: Path, *, capacity: int | None = None, sanitizer: bool = False) -> dict:
    """First compile the original research driver; then compile the audited adapter.

    Capacity overrides change storage limits only and are included in the binary
    contract. Exhaustion throws; it is never treated as rejection of a Monte Carlo
    move. Thus no capacity-truncated stationary ensemble is silently sampled.
    """
    root=Path(root).resolve();sources,checkout=check_sources(root)
    if capacity is not None and (type(capacity) is not int or not 10000<=capacity<=5_000_000):
        raise ValueError('capacity must be None or an integer in [10000,5000000]')
    compiler=shutil.which('c++')
    if not compiler:raise RuntimeError('C++ compiler missing')
    version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    contract=dict(sources=sources,adapter_sha256=sha256(__file__),compiler=compiler,compiler_version=version,
                  platform=platform.platform(),capacity=capacity,sanitizer=sanitizer)
    key=digest(contract)[:20];out=root/'build/baseline'/key;manifest=out/'build.json'
    with lock(root/'build/baseline'/f'{key}.lock'):
        if manifest.exists():
            m=load_json(manifest)
            if m['contract']!=contract:raise ValueError('build contract mismatch')
            verify_inventory(out,m['outputs'])
            return m
        if out.exists():
            raise RuntimeError(f'incomplete build retained at {out}; inspect and choose a new build root')
        out.mkdir(parents=True)
        staging=out/'source';(staging/'environment').mkdir(parents=True)
        for relative in sources['git_blobs']:
            dest=staging/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,dest)
        with (out/'original-build.log').open('wb') as log:
            subprocess.run([sys.executable,str(staging/'workflows/build.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
        generated=staging/'build/simulator'
        original=generated/'cdt-run';shutil.copy2(original,out/'cdt-run-original')
        patches=[]
        for name in ('simulation.hpp','universe.hpp'):
            p=generated/name
            p.write_text(replace_one(p.read_text(),'static void load_rng(std::istream& i) { i >> rng; }',
                'static void load_rng(std::istream& i) { i >> std::ws >> rng; if(!i) throw std::runtime_error("checkpoint RNG parse failed"); }'))
        patches.append('explicit whitespace handling for RNG deserialization; fixes GNU libstdc++ checkpoint restart')
        p=generated/'checkpoint.hpp';text=p.read_text()
        text=replace_one(text,'int n;i.read((char*)&n,sizeof(n));if(n<0 || n>10000000)',
                              'int n=0;i.read((char*)&n,sizeof(n));if(!i || n<0 || n>10000000)')
        text=replace_one(text,'Simulation::load_rng(i);Universe::load_rng(i);i.get();',
                              'Simulation::load_rng(i);Universe::load_rng(i);if(i.get()!=\'\\n\') throw std::runtime_error("checkpoint RNG terminator");')
        p.write_text(text);patches.append('reject truncated checkpoint vectors before allocation and enforce text/binary delimiter')
        p=generated/'pool.hpp';text=p.read_text()
        text=replace_one(text,'auto tmp = first;',
                         'if(first<0 || first>=capacity) throw std::runtime_error("pool capacity exhausted; stop, do not reject a move");\n\t\tauto tmp = first;')
        p.write_text(text);patches.append('fail-fast pool capacity bounds before access')
        p=generated/'simulation.cpp';text=p.read_text()
        text=replace_one(text,'Universe::move62(v);\n\n\treturn true;', 'return Universe::move62(v);')
        p.write_text(text);patches.append('report rejected move62 accurately; transition kernel and RNG draw sequence unchanged')
        p=generated/'runner.cpp';text=p.read_text()
        text=replace_one(text,'#include <map>', '#include <map>\n#include <csignal>\n#include <cmath>\nstatic volatile std::sig_atomic_t stop_requested=0;\nextern "C" void baseline_signal(int) { stop_requested=1; }')
        text=replace_one(text,'int main(int argc,char** argv) {','int native_main(int argc,char** argv) {\n    std::signal(SIGTERM,baseline_signal); std::signal(SIGINT,baseline_signal);')
        text=replace_one(text,'if(target<=0 || tune<0 || burn<0 || samples<0 || attempts<=0 || stride<1) return 2;',
                         'if(target<=0 || tune<0 || burn<0 || samples<0 || attempts<=0 || stride<1 || !std::isfinite(k0) || !std::isfinite(k3) || (long long)tune+burn+(long long)samples*stride>2147483647LL) return 2;')
        text=replace_one(text,'long proposed[6]={},accepted[6]={};',
                         'if(stop_requested) { save_checkpoint(checkpoint,i); return 75; }\n        long proposed[6]={},accepted[6]={};')
        text+='\nint main(int argc,char** argv) { try { return native_main(argc,argv); } catch(const std::exception& e) { std::cerr<<"BASELINE_NATIVE_ERROR: "<<e.what()<<"\\n"; return 70; } }\n'
        p.write_text(text);patches.append('finite/overflow argument checks and signal-safe sweep-boundary checkpoint exit')
        if capacity:
            originals={'tetra.hpp':5000000,'halfedge.hpp':5000000,'vertex.hpp':3000000,'triangle.hpp':1000000}
            for name,old in originals.items():
                p=generated/name
                p.write_text(replace_one(p.read_text(),f'pool_size = {old};',f'pool_size = {capacity};'))
            patches.append(f'all pool capacities explicitly set to {capacity}; capacity exhaustion aborts the job')
        flags=['-std=c++14','-O3','-Wno-format']
        if sanitizer:flags=['-std=c++14','-O1','-g','-Wno-format','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        cpp=sorted(generated.glob('*.cpp'))
        command=[compiler,*flags,*map(str,cpp),'-o',str(out/'cdt-run')]
        with (out/'adapter-build.log').open('wb') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        outputs=inventory(out)
        m=dict(schema=1,build_id=key,contract=contract,source_checkout=checkout,created_at=now(),
               binary=str((out/'cdt-run').relative_to(root)),binary_sha256=sha256(out/'cdt-run'),
               original_binary=str((out/'cdt-run-original').relative_to(root)),command=command,
               patches=patches,original_research_build_succeeded=True,outputs=outputs)
        atomic_json(manifest,m)
        return m
