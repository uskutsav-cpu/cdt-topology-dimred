"""Frozen, content-addressed numerical designs; no outcome-selected burn-in."""
from __future__ import annotations
from copy import deepcopy
import math
from .chain import validate_parameters
from .io import digest


def validate_design(cfg: dict) -> dict:
    cfg=deepcopy(cfg)
    expected={'schema','kind','name','time_extent','volumes','couplings','chains','seed','attempts_per_target',
              'tuning_sweeps','dispersal_sweeps','dispersal_factors','burn_sweeps','samples','sample_stride',
              'rho','rho_sensitivity','max_steps','roots','root_batch','diagnostic_sigmas','analysis_window',
              'bootstrap_replicates','bootstrap_seed','limits','notes'}
    if set(cfg)!=expected:raise ValueError(f'design keys differ: {set(cfg)^expected}')
    if cfg['schema']!=1 or cfg['kind'] not in ('native_pilot','production'):raise ValueError('unsupported design')
    for key in ('time_extent','chains','seed','attempts_per_target','tuning_sweeps','dispersal_sweeps','burn_sweeps','samples',
                'sample_stride','max_steps','roots','root_batch','bootstrap_replicates','bootstrap_seed'):
        if type(cfg[key]) is not int:raise ValueError(f'{key} must be an integer')
    if not 3<=cfg['time_extent']<=4096 or cfg['chains']<4 or cfg['samples']<16:raise ValueError('insufficient dimensions/chains/draws')
    if min(cfg[k] for k in ('seed','attempts_per_target','tuning_sweeps','dispersal_sweeps','burn_sweeps','sample_stride','roots','root_batch'))<1:
        raise ValueError('positive schedules required')
    if cfg['max_steps']<32 or cfg['bootstrap_replicates']<100:raise ValueError('insufficient diffusion/bootstrap budget')
    if len(cfg['volumes'])<2 or len(set(cfg['volumes']))!=len(cfg['volumes']):raise ValueError('need distinct multiple volumes')
    if any(type(v) is not int or v<18*cfg['time_extent'] for v in cfg['volumes']):raise ValueError('volume below native seed size')
    if len(set(cfg['couplings']))!=len(cfg['couplings']) or not cfg['couplings']:raise ValueError('duplicate/empty couplings')
    if any(type(k) not in (float,int) or not math.isfinite(k) for k in cfg['couplings']):raise ValueError('invalid coupling')
    rhos=[cfg['rho'],*cfg['rho_sensitivity']]
    if any(type(r) not in (int,float) or not 0<r<1 for r in rhos) or len(set(rhos))!=len(rhos):
        raise ValueError('use distinct lazy diffusion probabilities in (0,1)')
    if len(cfg['dispersal_factors'])!=cfg['chains'] or any(not .5<=v<=1.5 for v in cfg['dispersal_factors']):
        raise ValueError('one declared initial-volume factor per chain is required')
    if not cfg['diagnostic_sigmas'] or any(type(s) is not int or not 4<=s<cfg['max_steps']-3 for s in cfg['diagnostic_sigmas']):
        raise ValueError('invalid fixed diagnostic diffusion times')
    lo,hi=cfg['analysis_window']
    if type(lo) is not int or type(hi) is not int or not 4<=lo<hi<cfg['max_steps']-3:
        raise ValueError('invalid prespecified analysis window')
    limits=cfg['limits']
    keys={'rhat','bulk_ess','tail_ess','mean_mcse_sd','volume_relative_offset','ds_halfwidth','drift_ds','root_refinement_ds',
          'stationary_multiple','minimum_blocks','block_lengths','reference_reviewed'}
    if set(limits)!=keys:raise ValueError('invalid limits schema')
    if limits['reference_reviewed'] is not False:
        raise ValueError('this baseline implementation does not infer externally reviewed reproduction from a flag')
    for key in keys-{'reference_reviewed','block_lengths'}:
        if type(limits[key]) not in (int,float) or not math.isfinite(limits[key]) or limits[key]<=0:
            raise ValueError('invalid numerical limit')
    if not 1<limits['rhat']<=1.05 or min(limits['bulk_ess'],limits['tail_ess'])<100*cfg['chains']:
        raise ValueError('diagnostic limits weaker than declared baseline policy')
    if not limits['block_lengths'] or any(type(b) is not int or b<1 or b*limits['minimum_blocks']>cfg['samples'] for b in limits['block_lengths']):
        raise ValueError('too few blocks for declared block-length sensitivity')
    seeds=[]
    for v in cfg['volumes']:
        for k in cfg['couplings']:
            seeds.append(stage_seed(cfg,'tuning',v,k,0))
            for c in range(cfg['chains']):
                for stage in ('dispersal','production'):seeds.append(stage_seed(cfg,stage,v,k,c))
    if len(set(seeds))!=len(seeds):raise ValueError('seed collision')
    # Check initial states of both minstd-style streams used by the pinned builds.
    modulus=2147483647
    stream_pairs=[(s%modulus or 1,(s^0x9e3779b9)%modulus or 1) for s in seeds]
    if len(set(stream_pairs))!=len(stream_pairs):raise ValueError('effective native RNG seed collision')
    for v in cfg['volumes']:
        validate_parameters(native_parameters(cfg,v,1.,1.2,stage_seed(cfg,'production',v,1.,0)))
    return cfg


def stage_seed(cfg,stage,volume,coupling,chain):
    # Content-derived stage seeds do not change when a chain is extended.
    key={'seed':cfg['seed'],'stage':stage,'volume':volume,'coupling':float(coupling),'chain':chain}
    return int(digest(key)[:16],16)%2147483646+1


def native_parameters(cfg,volume,k0,k3,seed,*,stage='production',chain=0):
    p=dict(seed=seed,k0=float(k0),k3=float(k3),target=int(volume),tune=0,burn=cfg['burn_sweeps'],
           samples=cfg['samples'],attempts=int(volume)*cfg['attempts_per_target'],check_every_move=0,sample_stride=cfg['sample_stride'])
    if stage=='tuning':p.update(tune=cfg['tuning_sweeps'],burn=0,samples=1,sample_stride=1)
    elif stage=='dispersal':p.update(target=round(volume*cfg['dispersal_factors'][chain]),burn=cfg['dispersal_sweeps'],samples=1,sample_stride=1)
    validate_parameters(p)
    return p
