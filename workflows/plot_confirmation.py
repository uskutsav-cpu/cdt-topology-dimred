#!/usr/bin/env python3
"""Regenerate every figure from the delivered numerical summaries and saved arrays."""
from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def make_figures(data_path,output):
    data=json.loads(Path(data_path).read_text());out=Path(output);out.mkdir(parents=True,exist_ok=True)
    primary=data['primary'];scatter=data['scatter'];test=[r for r in scatter if r['subset']=='confirmation']
    paths=[]
    def save(fig,name):
        fig.text(.10,.014,'Constructed triangulations — not equilibrated physical CDT ensembles',fontsize=9)
        fig.tight_layout(rect=(0,.055,1,1))
        for ext in ['png','svg']:fig.savefig(out/(name+'.'+ext),dpi=180,bbox_inches='tight')
        plt.close(fig);paths.append(str(out/(name+'.png')))
    fig=plt.figure(figsize=(8,5.7));ax=fig.add_subplot(111)
    for subset,mark,label in [('training','s','Training: 16 new geometries'),('confirmation','o','Confirmation: 32 new geometries')]:
        rows=[r for r in scatter if r['subset']==subset]
        ax.scatter([r['H1'] for r in rows],[r['Ds32'] for r in rows],marker=mark,label=label,s=42,alpha=.8)
    x=np.array([r['H1'] for r in test]);y=np.array([r['Ds32'] for r in test]);xx=np.linspace(x.min(),x.max(),100)
    ax.plot(xx,np.polyval(np.polyfit(x,y,1),xx),linestyle='--',label='Confirmation linear fit')
    a=primary['primary_confirmation']
    ax.set(xlabel='All-root mean finite H1 total persistence (horizon 8)',ylabel='Whole-geometry spectral dimension at step 32',
        title=f"Independent persistence replication\nr = {a['pearson_r']:.3f}; prespecified one-sided p = {a['permutation_p']:.3f}")
    ax.legend(fontsize=9);save(fig,'01_persistence_replication')
    fig=plt.figure(figsize=(8,4.8));ax=fig.add_subplot(111)
    w=primary['within']['H1_finite_total_persistence']['estimate'];b=primary['primary_confirmation']
    vals=np.array([b['slope'],w['coefficient']]);ci=np.array([b['slope_ci95'],w['ci95']])
    ax.errorbar(vals,[1,0],xerr=np.vstack((vals-ci[:,0],ci[:,1]-vals)),fmt='o',capsize=5)
    ax.axvline(0,linestyle=':',linewidth=1)
    ax.set(yticks=[1,0],yticklabels=['Between geometries\nFull-return-trace Ds','Within geometries\nControlled local Ds'],xlabel='Ds change per unit H1 total persistence (95% interval)',
        title='The persistence association changes sign\nDifferent estimands; not a causal effect')
    save(fig,'02_persistence_sign_reversal')
    fig=plt.figure(figsize=(8,4.8));ax=fig.add_subplot(111)
    w=primary['within']['conductance_r4'];est=w['estimate'];null=w['label_destroyed_estimate']
    vals=np.array([est['coefficient'],null['coefficient']]);ci=np.array([est['ci95'],null['ci95']])
    ax.errorbar(vals,[1,0],xerr=np.vstack((vals-ci[:,0],ci[:,1]-vals)),fmt='o',capsize=5)
    ax.axvline(0,linestyle=':',linewidth=1)
    ax.set(yticks=[1,0],yticklabels=['Controlled conductance','Label-destruction diagnostic'],xlabel='Local Ds16 change per unit conductance at radius 4',
        title='Weaker bottlenecks accompany higher local Ds\n32 independent geometry clusters; 95% intervals')
    save(fig,'03_conductance_control')
    fig=plt.figure(figsize=(8,5.7));ax=fig.add_subplot(111)
    x=np.array([r['branch_entropy'] for r in test]);y=np.array([r['Ds32'] for r in test])
    ax.scatter(x,y,s=40,alpha=.8);xx=np.linspace(x.min(),x.max(),100);ax.plot(xx,np.polyval(np.polyfit(x,y,1),xx),linestyle='--')
    b=primary['branch_descriptors']['branch_size_entropy']
    ax.set(xlabel='Entropy of separated-region sizes (regions may overlap)',ylabel='Whole-geometry Ds32',
        title=f"Secondary neck-size descriptor\nr = {b['pearson_r']:.3f}; within-family Holm p = {b['holm_adjusted_p']:.4f}")
    save(fig,'04_branch_descriptor')
    fig=plt.figure(figsize=(8,5.7));ax=fig.add_subplot(111)
    matrix=np.asarray(primary['scale_scan']['correlation']);im=ax.imshow(matrix,aspect='auto',origin='lower',vmin=-1,vmax=1)
    ax.set(xticks=range(5),xticklabels=[8,12,16,24,32],yticks=range(5),yticklabels=[2,3,4,6,8],
        xlabel='Diffusion steps',ylabel='Conductance neighborhood radius',title='Held-out conductance–Ds correlations\nGlobal max-statistic p = 0.0005; no demonstrated scaling band')
    fig.colorbar(im,ax=ax,label='Pearson correlation across confirmation geometries')
    save(fig,'05_scale_scan')
    fig=plt.figure(figsize=(8,5.4));ax=fig.add_subplot(111)
    rms=np.mean([r['rms'] for r in test],axis=0);sigma=np.arange(len(rms));mask=(sigma>=1)&(sigma<=40)
    ax.plot(sigma[mask],rms[mask],label='Measured RMS graph distance')
    ax.plot(sigma[mask],np.sqrt(sigma[mask])*rms[8]/np.sqrt(8),linestyle='--',label='Square-root benchmark anchored at step 8')
    ax.set(xlabel='Diffusion steps',ylabel='Dual-graph hop distance',title='Measured exploration scale, not an assumed square root')
    ax.legend();save(fig,'06_diffusion_distance')
    fig=plt.figure(figsize=(8.6,5.7));ax=fig.add_subplot(111)
    pairs=data['operators']['paired'];ix=np.arange(len(pairs));dual=np.array([p['dual_discrete_change'] for p in pairs]);fem=np.array([p['fem_refined_change'] for p in pairs]);ci=np.array([p['fem_change_interval'] for p in pairs])
    ax.plot(ix-.09,dual,'o',label='Exact dual-walk difference')
    ax.errorbar(ix+.09,fem,yerr=np.vstack((fem-ci[:,0],ci[:,1]-fem)),fmt='s',capsize=3,label='FEM difference + finite-matrix tail bounds')
    ax.axhline(0,linestyle=':',linewidth=1)
    ax.set(xticks=ix,xticklabels=[p['seed'] for p in pairs],xlabel='Independent paired construction seed',ylabel='After-minus-before Ds at the locked comparison scale',
        title='Dual graph vs metric-preserving FEM\nAll pairs remain unresolved by the refinement screen')
    ax.legend(fontsize=9);save(fig,'07_paired_operators')
    fig=plt.figure(figsize=(8,5.7));ax=fig.add_subplot(111)
    for row in data['operator_levels']:
        ax.plot([l['vertices'] for l in row['levels']],[l['ds32'] for l in row['levels']],marker='o',alpha=.55,linewidth=1)
    ax.set_xscale('log');ax.set(xlabel='FEM degrees of freedom',ylabel='FEM Ds at the frozen clock-matched time',
        title='Three-level FEM refinement has not converged\n16 before/after geometries; identical underlying metric')
    save(fig,'08_fem_refinement')
    fig=plt.figure(figsize=(8,5.4));ax=fig.add_subplot(111)
    rows=data['finite_size']['sizes'];x=np.arange(len(rows));y=np.array([q['H1_vs_Ds32']['pearson_r'] for q in rows]);ci=np.array([q['H1_vs_Ds32']['correlation_ci95'] for q in rows])
    ax.errorbar(x,y,yerr=np.vstack((y-ci[:,0],ci[:,1]-y)),fmt='o',capsize=5)
    ax.axhline(0,linestyle=':',linewidth=1)
    ax.set(xticks=x,xticklabels=[q['tetrahedra'] for q in rows],xlabel='Tetrahedron count',ylabel='Persistence–Ds32 correlation (95% bootstrap interval)',
        title='Finite-size robustness remains unestablished\nEight independent seeds paired across three sizes')
    save(fig,'09_finite_size')
    fig=plt.figure(figsize=(8,5.4));ax=fig.add_subplot(111)
    ax.hist(data['primary_null'],bins=45,density=True,alpha=.7,label='9,999 whole-geometry permutations')
    ax.axvline(primary['primary_confirmation']['pearson_r'],linestyle='--',linewidth=2,label='Observed confirmation correlation')
    ax.set(xlabel='Persistence–Ds32 correlation after label permutation',ylabel='Density',title='Prespecified primary permutation test')
    ax.legend(fontsize=9);save(fig,'10_primary_null')
    fig=plt.figure(figsize=(8,5.4));ax=fig.add_subplot(111)
    for subset in ['training','confirmation']:
        curves=np.array([[np.nan if v is None else v for v in r['full_ds']] for r in scatter if r['subset']==subset])
        mask=np.arange(4,41);mean=np.mean(curves[:,mask],axis=0)
        ax.plot(mask,mean,label=f'{subset.capitalize()} geometry mean')
    ax.set(xlabel='Diffusion steps',ylabel='Full-return-trace spectral dimension',title='Ordinary diffusion on constructed test geometries\nThis is not a physical CDT reproduction')
    ax.legend();save(fig,'11_constructed_spectral_flow')
    (out/'FIGURE_INDEX.json').write_text(json.dumps([Path(p).name for p in paths],indent=2)+'\n')
    return paths

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,default=ROOT/'docs/confirmation/COMPUTED_RESULTS.json')
    ap.add_argument('--output',type=Path,default=ROOT/'docs/confirmation/figures')
    args=ap.parse_args();print(json.dumps(make_figures(args.data,args.output),indent=2))
if __name__=='__main__':main()
