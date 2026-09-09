#!/usr/bin/env python3
"""Plot saved native results, explicitly marked unequilibrated when screens fail."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import matplotlib.pyplot as plt


def make_figures(study,output):
    study=Path(study);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    idx=json.loads((study/'analysis_index.json').read_text())
    summary=json.loads((study/'analyses'/idx['analysis']/'summary.json').read_text())
    groups=summary['groups'];rho=summary['design']['rho']
    tag='UNEQUILIBRATED NATIVE PILOT' if not summary['decision']['diagnostic_screens_pass'] else 'DIAGNOSTIC SCREENS ONLY; REFERENCE PENDING'
    paths=[]
    def finish(fig,name):
        fig.text(.5,.015,tag,ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.04,1,1))
        for ext in ('png','svg'):
            p=output/f'{name}.{ext}';fig.savefig(p,dpi=170);paths.append(str(p))
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(9.5,5.8))
    for g in groups:
        c=g['curves'][f'full_uniform_rho_{rho:g}'];x=np.arange(len(c['mean_geometry_ds']));valid=np.asarray(c['valid_time_mask'])
        y=np.array(c['mean_geometry_ds'],float);ci=np.asarray(c['block_sensitivity'][-1]['conservative_pointwise_95'],float)
        ax.plot(x[valid],y[valid],label=f"Target N3 = {g['volume_target']:,}")
        ax.fill_between(x[valid],ci[0,valid],ci[1,valid],alpha=.15)
    ax.set(xlabel='Diffusion steps σ',ylabel='Mean per-geometry spectral dimension',title='Fresh native CDT: full-graph ordinary diffusion')
    ax.legend();ax.grid(alpha=.2)
    ax.text(.02,.03,'Bands are conditional pointwise estimates—not validated equilibrium intervals.',transform=ax.transAxes,fontsize=8)
    finish(fig,'01_native_spectral_curves')
    fig,ax=plt.subplots(figsize=(9,5.5));x=np.arange(len(groups));w=.35
    ax.bar(x-w/2,[g['native_diagnostics']['N3']['rank_folded_rhat'] for g in groups],w,label='Volume N3')
    ax.bar(x+w/2,[max(d['rank_folded_rhat'] for d in g['geometry_diagnostics'].values()) for g in groups],w,label='Worst sampled profile observable')
    ax.axhline(summary['design']['limits']['rhat'],linestyle='--',label='Declared threshold 1.01')
    ax.set(xticks=x,xticklabels=[f"{g['volume_target']:,}" for g in groups],xlabel='Target tetrahedra',ylabel='Rank/folded split R-hat',title='Volume agreement does not establish profile convergence')
    ax.legend();finish(fig,'02_convergence_rhat')
    fig,ax=plt.subplots(figsize=(9,5.5))
    ax.bar(x-w/2,[g['native_diagnostics']['N3']['bulk_ess'] for g in groups],w,label='Volume N3')
    ax.bar(x+w/2,[min(d['bulk_ess'] for d in g['geometry_diagnostics'].values()) for g in groups],w,label='Worst sampled profile observable')
    ax.axhline(summary['design']['limits']['bulk_ess'],linestyle='--',label='Declared minimum ESS 400')
    ax.set(xticks=x,xticklabels=[f"{g['volume_target']:,}" for g in groups],yscale='log',xlabel='Target tetrahedra',ylabel='Bulk effective sample size',title='Slow shape modes remain poorly sampled')
    ax.legend();finish(fig,'03_convergence_ess')
    chains=json.loads((study/'chain_index.json').read_text())
    for number,g in enumerate(groups,4):
        fig,ax=plt.subplots(figsize=(10,5.5))
        for chain in sorted((c for c in chains if c['volume']==g['volume_target'] and c['k0']==g['k0']),key=lambda c:c['chain']):
            with (study/'raw'/chain['job']/'diagnostics.csv').open() as f:
                rows=[r for r in csv.DictReader(f) if r['phase']=='measure']
            ax.plot(np.arange(1,len(rows)+1),[float(r['peak_slice']) for r in rows],linewidth=.7,label=f"Chain {chain['chain']+1}")
        ax.set(xlabel='Measurement sweep after declared warmup',ylabel='Maximum spatial-slice triangle count',title=f"Target N3 = {g['volume_target']:,}: native peak-slice traces")
        ax.legend();ax.grid(alpha=.2);finish(fig,f'{number:02d}_peak_trace_{g["volume_target"]}')
    g=groups[-1];c=g['curves'][f'full_uniform_rho_{rho:g}'];x=np.arange(len(c['mean_geometry_ds']));valid=np.asarray(c['valid_time_mask'])
    fig,ax=plt.subplots(figsize=(9,5.5))
    ax.plot(x[valid],np.array(c['mean_geometry_ds'],float)[valid],label='Mean of per-geometry Ds')
    ax.plot(x[valid],np.array(c['annealed_ds'],float)[valid],linestyle='--',label='Ds of ensemble-mean return probability')
    ax.set(xlabel='Diffusion steps σ',ylabel='Spectral dimension',title=f"Two distinct estimands: target N3 = {g['volume_target']:,}")
    ax.legend();ax.grid(alpha=.2);finish(fig,'07_distinct_estimands')
    fig,ax=plt.subplots(figsize=(9,5.5))
    for g in groups:
        a=g['curves'][f'full_uniform_rho_{rho:g}'];other=summary['design']['rho_sensitivity'][0]
        b=g['curves'][f'full_uniform_rho_{other:g}'];s=np.arange(len(a['mean_geometry_ds']));at=s*rho/other
        mask=np.asarray(a['valid_time_mask'])&(at<summary['design']['analysis_window'][1])
        mask&=np.interp(at,s,np.asarray(b['valid_time_mask'],float))>.999
        delta=np.array(a['mean_geometry_ds'],float)-np.interp(at,s,np.array(b['mean_geometry_ds'],float))
        ax.plot(s[mask]*rho,delta[mask],label=f"N3 = {g['volume_target']:,}")
    ax.axhline(0,linestyle='--');ax.set(xlabel='Matched diffusion coordinate ρσ',ylabel='Ds(ρ=0.8) − Ds(ρ=0.4)',title='Diffusion-rate sensitivity on the recorded trajectories')
    ax.legend();ax.grid(alpha=.2);finish(fig,'08_rho_sensitivity')
    (output/'FIGURE_INDEX.json').write_text(json.dumps({'analysis_id':idx['analysis'],'status':tag,'files':[Path(p).name for p in paths]},indent=2)+'\n')
    return paths

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('study',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    print(json.dumps(make_figures(a.study,a.output),indent=2))
