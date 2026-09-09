"""Native-chain execution with same-binary continuation and append-only lineage."""
from __future__ import annotations
import csv
import io
import math
import os
from pathlib import Path
import signal
import subprocess
import time
from .io import atomic_bytes, atomic_json, digest, immutable_json, inventory, load_json, lock, now, sha256, verify_inventory

PARAMETERS = ('seed','k0','k3','target','tune','burn','samples','attempts','check_every_move','sample_stride')


def validate_parameters(p: dict):
    if set(p)!=set(PARAMETERS):
        raise ValueError(f'wrong native parameter keys: {set(p)^set(PARAMETERS)}')
    for key in ('seed','target','tune','burn','samples','attempts','check_every_move','sample_stride'):
        if type(p[key]) is not int:raise ValueError(f'{key} must be an integer, not a boolean/float')
    for key in ('k0','k3'):
        if type(p[key]) not in (float,int) or not math.isfinite(p[key]):raise ValueError(f'invalid {key}')
    if not 0<p['seed']<2147483647:raise ValueError('seed outside deliberately restricted native-engine range')
    if min(p['target'],p['attempts'],p['sample_stride'])<1 or min(p['tune'],p['burn'],p['samples'])<0:
        raise ValueError('invalid native schedule')
    if p['check_every_move'] not in (0,1):raise ValueError('check_every_move must be 0 or 1')
    if p['tune']+p['burn']+p['samples']*p['sample_stride']>2147483647:
        raise ValueError('native sweep counter would overflow')


def checkpoint_header(path: Path) -> dict:
    with path.open('rb') as handle:
        lines=[handle.readline(100000).decode('ascii').strip() for _ in range(6)]
    if lines[0]!='CDT_CHECKPOINT_V1':raise ValueError('unrecognized checkpoint')
    completed=int(lines[1]);k3=float(lines[2]);T=int(lines[3])
    if completed<0 or not math.isfinite(k3) or T<3 or not lines[4] or not lines[5]:
        raise ValueError('invalid checkpoint header')
    return dict(completed_sweeps=completed,k3=k3,time_extent=T,
                simulation_rng_state=lines[4],universe_rng_state=lines[5])


def repair_trace(out: Path, completed: int):
    """Keep only committed sweeps; retain crash tail as immutable evidence.

    A geometry written after the last committed checkpoint is not erased: the
    native driver's replay must reproduce it byte-for-byte or fail.
    """
    path=out/'diagnostics.csv'
    if not path.exists():
        if completed:raise ValueError('checkpoint exists without its diagnostics')
        return None
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    if not lines:raise ValueError('empty diagnostics')
    head=lines[0];fields=next(csv.reader([head.decode()]))
    expected={'sweep','phase','N0','N3','N31','k3','peak_slice','seconds'}
    if not expected<=set(fields):raise ValueError('wrong native CSV header')
    if len(lines)<completed+1:raise ValueError('checkpoint ahead of durable CSV trace')
    kept=[head]
    for k in range(completed):
        row=next(csv.reader([lines[k+1].decode()]))
        if len(row)!=len(fields) or int(row[0])!=k+1:raise ValueError('noncontiguous committed diagnostics')
        kept.append(lines[k+1])
    tail=b''.join(lines[completed+1:])
    if tail:
        tailpath=out/('recovered-tail-'+digest(tail.hex())[:16]+'.txt')
        if tailpath.exists() and tailpath.read_bytes()!=tail:raise ValueError('recovery-tail collision')
        if not tailpath.exists():atomic_bytes(tailpath,tail)
        atomic_bytes(path,b''.join(kept))
        return dict(path=tailpath.name,sha256=sha256(tailpath),discarded_bytes=len(tail),
                    note='uncommitted CSV tail retained, not analyzed; native state is replayed')
    return None


def native_environment(stop_after=None):
    env=os.environ.copy()
    env.pop('CDT_INITIAL_CHECKPOINT',None)
    env.pop('CDT_STOP_AFTER_SWEEP',None)
    if stop_after is not None:env['CDT_STOP_AFTER_SWEEP']=str(int(stop_after))
    return env


def read_trace(path: Path, parameters: dict, *, collect=True) -> dict:
    required=['sweep','phase','N0','N3','N31','k3','peak_slice','seconds']
    required += [x for j in range(1,6) for x in (f'attempt_{j}',f'accept_{j}')]
    rows=[];row_count=0
    with path.open() as handle:
        reader=csv.DictReader(handle)
        if reader.fieldnames!=required:raise ValueError('unexpected diagnostics schema')
        for index,row in enumerate(reader,1):
            if int(row['sweep'])!=index:raise ValueError('diagnostics have a gap/duplicate')
            expected='tune' if index<=parameters['tune'] else 'burn' if index<=parameters['tune']+parameters['burn'] else 'measure'
            if row['phase']!=expected:raise ValueError('phase disagrees with frozen schedule')
            for name in ('N0','N3','N31','peak_slice'):
                if int(row[name])<=0:raise ValueError('nonpositive native count')
            props=[int(row[f'attempt_{j}']) for j in range(1,6)]
            accepts=[int(row[f'accept_{j}']) for j in range(1,6)]
            if sum(props)!=parameters['attempts'] or any(a<0 or a>b for a,b in zip(accepts,props)):
                raise ValueError('invalid proposal/acceptance accounting')
            if not all(math.isfinite(float(row[k])) for k in ('k3','seconds')):raise ValueError('non-finite trace')
            if not parameters['tune'] and float(row['k3'])!=parameters['k3']:
                raise ValueError('frozen coupling changed')
            row_count=index
            if collect:rows.append(row)
    return dict(rows=rows,columns=required,row_count=row_count)


def run_native_job(root: Path, build: dict, study: Path, label: str, input_path: Path,
                   parameters: dict, *, stage='production', lineage=None,
                   timeout_seconds=900., stop_after=None, cancel_event=None) -> dict:
    """Rerunning is a verified resume; increasing samples is an explicit extension.

    No checkpoint from another job is used as an independent start. A geometry
    start is reseeded; resuming one's own checkpoint retains that chain's RNG.
    """
    root=Path(root).resolve();study=Path(study).resolve();input_path=Path(input_path).resolve()
    validate_parameters(parameters)
    if stage not in ('tuning','dispersal','production','debug'):raise ValueError('unknown native stage')
    if stage!='tuning' and parameters['tune']!=0:raise ValueError('coupling adaptation forbidden outside tuning')
    if not math.isfinite(timeout_seconds) or timeout_seconds<=0:raise ValueError('invalid timeout')
    binary=root/build['binary']
    if sha256(binary)!=build['binary_sha256']:raise ValueError('binary changed')
    contract=dict(parameters={k:v for k,v in parameters.items() if k!='samples'},
                  label=label,stage=stage,lineage=lineage or {},input_sha256=sha256(input_path),
                  binary_sha256=sha256(binary),runner_sha256=sha256(__file__),
                  rng_origin='fresh independent native seeds on initial geometry; own checkpoint on resume')
    job_id=digest(contract)[:20];out=study/'raw'/job_id
    out.mkdir(parents=True,exist_ok=True);mp=out/'manifest.json'
    with lock(out/'chain.lock') as lockfd:
        previous=None;history=[];base_elapsed=0.
        if mp.exists():
            old=load_json(mp)
            if old['contract']!=contract:raise ValueError('native job contract changed')
            if parameters['samples']<old['parameters']['samples']:raise ValueError('cannot shorten an existing chain')
            if old.get('outputs'):verify_inventory(out,old['outputs'])
            if old['status']=='complete' and parameters['samples']==old['parameters']['samples']:
                return old
            if old['status']=='complete' and parameters['samples']>old['parameters']['samples']:
                rev=out/'revisions'/f"through_{old['parameters']['samples']}.json"
                immutable_json(rev,old);previous={'path':str(rev.relative_to(out)),'sha256':sha256(rev)}
            else:previous=old.get('previous_revision')
            history=old.get('attempt_history',[])+[{k:old.get(k) for k in ('status','started_at','ended_at','exit_code','elapsed_seconds')}]
            base_elapsed=old.get('total_elapsed_seconds',0.)
        elif (out/'checkpoint.bin').exists() or (out/'diagnostics.csv').exists():
            raise ValueError('unregistered raw state; refusing to adopt it')
        cp=out/'checkpoint.bin';recovery=None
        if cp.exists():
            header=checkpoint_header(cp)
            if parameters['tune']==0 and header['k3']!=parameters['k3']:raise ValueError('checkpoint coupling mismatch')
            total=parameters['tune']+parameters['burn']+parameters['samples']*parameters['sample_stride']
            if header['completed_sweeps']>total:raise ValueError('checkpoint exceeds requested schedule')
            recovery=repair_trace(out,header['completed_sweeps'])
        source=out/'input.dat'
        if source.exists():
            if sha256(source)!=contract['input_sha256']:raise ValueError('saved initial geometry corrupted')
        else:
            atomic_bytes(source,input_path.read_bytes())
        rec=dict(schema=1,job_id=job_id,label=label,stage=stage,contract=contract,parameters=dict(parameters),
                 status='running',started_at=now(),attempt_history=history,previous_revision=previous,
                 initial_checkpoint_inherited=False,physical_monte_carlo=True,
                 equilibrium_established=False,reproduction_pass=False,recovery=recovery)
        command=[str(binary),str(source),str(out),*[str(parameters[k]) for k in PARAMETERS]]
        rec['command']=command;atomic_json(mp,rec);start=time.perf_counter();code=None;error=None
        try:
            with (out/'native.log').open('ab') as log:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
                                         env=native_environment(stop_after),start_new_session=True,pass_fds=(lockfd,))
                rec['pid']=process.pid;atomic_json(mp,rec)
                try:
                    deadline=time.monotonic()+timeout_seconds
                    while True:
                        if cancel_event is not None and cancel_event.is_set():
                            raise KeyboardInterrupt
                        remaining=deadline-time.monotonic()
                        if remaining<=0:raise subprocess.TimeoutExpired(command,timeout_seconds)
                        try:
                            code=process.wait(timeout=min(.5,remaining));break
                        except subprocess.TimeoutExpired:
                            continue
                except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
                    error=type(exc).__name__
                    os.killpg(process.pid,signal.SIGTERM)
                    try:code=process.wait(timeout=30.)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL);code=process.wait()
                    if isinstance(exc,KeyboardInterrupt):error='KeyboardInterrupt'
            if code not in (0,75):raise RuntimeError(f'native simulator exit {code}; inspect {out / "native.log"}')
            header=checkpoint_header(cp)
            total=parameters['tune']+parameters['burn']+parameters['samples']*parameters['sample_stride']
            rec['checkpoint']=header
            rec['completed_samples']=max(0,(header['completed_sweeps']-parameters['tune']-parameters['burn'])//parameters['sample_stride'])
            if code==0:
                if header['completed_sweeps']!=total:raise ValueError('native exit without all requested sweeps')
                trace=read_trace(out/'diagnostics.csv',parameters,collect=False)
                if trace['row_count']!=total:raise ValueError('wrong completed trace length')
                files=list(out.glob('geometry_*.dat'))
                expected={f'geometry_{i}.dat' for i in range(parameters['samples'])}
                if {p.name for p in files}!=expected:raise ValueError('snapshot census does not match schedule')
                rec['status']='complete'
            else:rec['status']='paused'
        except BaseException as exc:
            error=repr(exc);rec['status']='failed'
            raise
        finally:
            rec.update(exit_code=code,error=error,ended_at=now(),elapsed_seconds=time.perf_counter()-start)
            rec['total_elapsed_seconds']=base_elapsed+rec['elapsed_seconds']
            rec['outputs']=inventory(out,exclude=('manifest.json',))
            atomic_json(mp,rec)
        if error=='KeyboardInterrupt':raise KeyboardInterrupt
        return rec
