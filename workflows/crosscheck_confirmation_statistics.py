#!/usr/bin/env python3
"""Secondary verification against an independent statsmodels least-squares fit.

This verifies arithmetic and clustering, not the causal adequacy of controls.
"""
from pathlib import Path
import argparse,json,sys
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cdt_confirmation.analysis import load_run,_controls
from cdt_confirmation.provenance import write_json
from cdt_mechanisms.inference import within_effect

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'results/confirmation/census')
    ap.add_argument('--output',type=Path,default=ROOT/'validation/confirmation/independent_statistics_check.json')
    args=ap.parse_args();protocol,index,items=load_run(args.run)
    selected=items[len(protocol['design']['training_seeds']):]
    rows=[r for item in selected for r in item['rows']]
    group=np.concatenate([np.repeat(j,len(item['rows'])) for j,item in enumerate(selected)])
    controls=_controls(rows);answers={}
    # Construct explicit configuration dummies rather than reuse the production demeaning routine.
    nuisance=np.column_stack([np.eye(len(selected))[group],controls])
    for feature,time in [('H1_finite_total_persistence',32),('conductance_r4',16)]:
        x=np.array([r[feature] for r in rows]);y=np.array([r[f'Ds_{time}'] for r in rows])
        # Statsmodels computes its own pseudoinverse and cluster score covariance.
        design=np.column_stack([x,nuisance]);fit=sm.OLS(y,design).fit()
        cov=cov_cluster(fit,group,use_correction=False)
        dof=len(y)-np.linalg.matrix_rank(design)
        factor=len(selected)/(len(selected)-1)*(len(y)-1)/dof
        standard_error=float(np.sqrt(cov[0,0]*factor))
        original=within_effect(x,y,controls,group,group)
        delta=abs(float(fit.params[0])-original['coefficient'])
        se_delta=abs(standard_error-original['cluster_standard_error'])
        if delta>1e-10 or se_delta>1e-10:raise ArithmeticError('independent regression check disagrees')
        answers[feature]=dict(statsmodels_beta=float(fit.params[0]),statsmodels_cluster_standard_error=standard_error,
            production_beta=original['coefficient'],production_cluster_standard_error=original['cluster_standard_error'],
            beta_absolute_difference=delta,standard_error_absolute_difference=se_delta,
            n_rows=len(y),n_geometry_clusters=len(selected),residual_dof=int(dof))
    write_json(args.output,dict(checked=answers,passed=True,scope='secondary independent arithmetic verification; not new hypothesis testing'))
    print(args.output)
if __name__=='__main__':main()
