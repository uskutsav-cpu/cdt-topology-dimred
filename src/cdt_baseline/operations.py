"""Read-only budget/status reporting and explicit same-chain extension."""
from pathlib import Path
from .chain import checkpoint_header
from .design import validate_design
from .io import load_json


def budget(cfg):
    cfg=validate_design(cfg);ensembles=[]
    for v in cfg['volumes']:
        for k in cfg['couplings']:
            a=v*cfg['attempts_per_target']
            ensembles.append(dict(volume=v,k0=k,chains=cfg['chains'],attempts_per_sweep=a,
                                  tuning_attempts=(cfg['tuning_sweeps']+1)*a,
                                  dispersal_attempts=cfg['chains']*(cfg['dispersal_sweeps']+1)*a,
                                  burn_attempts=cfg['chains']*cfg['burn_sweeps']*a,
                                  measurement_attempts=cfg['chains']*cfg['samples']*cfg['sample_stride']*a,
                                  saved_production_geometries=cfg['chains']*cfg['samples']))
    return dict(ensembles=ensembles,total_proposed_moves=sum(sum(x[k] for k in ('tuning_attempts','dispersal_attempts','burn_attempts','measurement_attempts')) for x in ensembles),
                time_estimate=None,warning='A scheduled number of sweeps does not establish equilibration. No automatic topology-conditioned production is launched.')


def status(study):
    study=Path(study).resolve();jobs=[]
    for p in sorted((study/'raw').glob('*/manifest.json')):
        m=load_json(p);cp=p.parent/'checkpoint.bin'
        try:h=checkpoint_header(cp) if cp.exists() else None
        except (ValueError,OSError,UnicodeError):h=None
        jobs.append(dict(label=m['label'],recorded_status=m['status'],job_id=m['job_id'],
                         latest_checkpoint_sweep=h['completed_sweeps'] if h else None,
                         saved_geometries=len(list(p.parent.glob('geometry_*.dat')))))
    return dict(jobs=jobs,process_liveness='not inferred from a PID or a static manifest',
                analysis=load_json(study/'analysis_index.json') if (study/'analysis_index.json').exists() else None)


def extension_design(study,new_samples):
    cfg=validate_design(load_json(Path(study)/'requested_schedule.json'))
    if type(new_samples) is not int or new_samples<=cfg['samples']:raise ValueError('extension must strictly increase samples')
    cfg['samples']=new_samples
    return validate_design(cfg)
