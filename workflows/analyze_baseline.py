"""Pilot diagnostics and full-lattice spectral measurements (not a gate pass)."""
import argparse,json,sys,time,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/mpl'))
import numpy as np
from spectral import operator,exact_returns,hutchinson,walkers,dimension
from diagnostics import summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('job');ap.add_argument('--steps',type=int,default=256);ap.add_argument('--configurations',type=int,default=16);ap.add_argument('--starts',type=int,default=64);args=ap.parse_args()
    manifest=json.loads((ROOT/'results/manifests'/f'{args.job}.json').read_text()); assert manifest['status']=='complete'
    diag=np.genfromtxt(ROOT/'data/raw'/args.job/'diagnostics.csv',names=True,delimiter=',',dtype=None,encoding='utf8')
    # Recovery may replay a partial checkpoint interval; each sweep counts once.
    _,unique=np.unique(diag['sweep'],return_index=True);diag=diag[np.sort(unique)]
    measure=diag[diag['phase']=='measure']; reports={k:summary(measure[k]) for k in ['N0','N3','N31','peak_slice']}
    out=ROOT/'results/tables'/f'{args.job}_diagnostics.json';out.write_text(json.dumps(reports,indent=2)+'\n')
    paths=sorted((ROOT/'data/geometry').glob(f'{args.job}_*.npz'),key=lambda p:int(p.stem.split('_')[-1]))
    chosen=np.linspace(0,len(paths)-1,min(args.configurations,len(paths)),dtype=int)
    curves=[]; timings=[]
    codehash=hashlib.sha256((ROOT/'src/spectral/__init__.py').read_bytes()).hexdigest()
    for i in chosen:
        p=paths[i]; raw=np.load(p); nb=raw['neighbors']; M=operator(nb,.8)
        dest=ROOT/'results/tables'/f'{p.stem}_spectral_s{args.steps}_n{args.starts}.npz'
        key=hashlib.sha256(p.read_bytes()).hexdigest()
        if dest.exists():
            cached=np.load(dest); assert str(cached['input_sha256'])==key
            assert 'code_sha256' in cached and str(cached['code_sha256'])==codehash, 'stale spectral cache'
            P=cached['returns']
        else:
            starts=np.random.default_rng(88000+i).choice(len(nb),min(args.starts,len(nb)),replace=False)
            start=time.perf_counter(); P=exact_returns(M,args.steps,starts)
            seconds=time.perf_counter()-start
            np.savez_compressed(dest,returns=P,starts=starts,rho=.8,input_sha256=key,code_sha256=codehash,elapsed_seconds=seconds)
            timings.append({'configuration':p.stem,'N3':len(nb),'starts':len(starts),'steps':args.steps,'seconds':seconds})
        curves.append(P.mean(axis=0))
    curves=np.array(curves); sigma=np.arange(args.steps+1)
    table=np.column_stack((sigma,curves.mean(axis=0),dimension(curves.mean(axis=0)),dimension(curves).mean(axis=0)))
    np.savetxt(ROOT/'results/tables'/f'{args.job}_ordinary.csv',table,delimiter=',',header='sigma,P_mean,Ds_of_mean_P,mean_of_Ds',comments='')
    (ROOT/'results/tables'/f'{args.job}_spectral_timings.json').write_text(json.dumps(timings,indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
    fig,ax=plt.subplots(2,2,figsize=(9,6),layout='constrained')
    for a,k in zip(ax.ravel(),reports):
        a.plot(diag['sweep'],diag[k],lw=.65);a.axvline(manifest['parameters']['tune'],color='orange',ls='--');a.axvline(manifest['parameters']['tune']+manifest['parameters']['burn'],color='green',ls='--');a.set(xlabel='Sweep',ylabel=k)
    fig.suptitle('Pilot diagnostics — thermalization not certified')
    fig.savefig(ROOT/'results/figures'/f'{args.job}_diagnostics.pdf');fig.savefig(ROOT/'results/figures'/f'{args.job}_diagnostics.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(9,3.6),layout='constrained')
    ax[0].loglog(sigma[1:],table[1:,1]);ax[0].set(xlabel=r'$\sigma$',ylabel=r'$P(\sigma)$')
    ax[1].semilogx(sigma,table[:,2],label='Derivative of mean P');ax[1].semilogx(sigma,table[:,3],ls='--',label='Mean derivative');ax[1].axhline(3,color='gray',lw=.8);ax[1].set(xlabel=r'$\sigma$',ylabel=r'$D_s$',ylim=(0,4));ax[1].legend(fontsize=8)
    fig.suptitle('Pilot, full lattice — not a spectral reproduction pass')
    fig.savefig(ROOT/'results/figures'/f'{args.job}_ordinary.pdf');fig.savefig(ROOT/'results/figures'/f'{args.job}_ordinary.png',dpi=140);plt.close(fig)
    print(json.dumps({'diagnostics':reports,'peak_Ds_sigma_ge_10':float(np.nanmax(table[10:,2])),'measured_configurations':len(curves)}))

if __name__=='__main__': main()
