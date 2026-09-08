"""Render saved baseline tables; performs no new diffusion or simulation."""
from pathlib import Path
import os,argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/mpl'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ap=argparse.ArgumentParser();ap.add_argument('job');a=ap.parse_args()
t=ROOT/'results/tables';f=ROOT/'results/figures'
exact=np.genfromtxt(t/f'{a.job}_exact_uv_s26_total128_stride4.csv',names=True,delimiter=',')
sampled=np.genfromtxt(t/f'{a.job}_n512_s256_stride4_aggregate.csv',names=True,delimiter=',')
rho=np.genfromtxt(t/f'{a.job}_rho_thinning_total128_stride4.csv',names=True,delimiter=',')
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
fig,ax=plt.subplots(1,2,figsize=(10,4),layout='constrained')
use=(exact['sigma']>=5)&np.isfinite(exact['Ds_of_mean_P'])
ax[0].plot(exact['sigma'][use],exact['Ds_of_mean_P'][use],label='All starting sites (exact)',lw=2)
ax[0].plot(sampled['sigma'][5:26],sampled['Ds_of_mean_P'][5:26],ls='--',label='512 sampled starts',lw=1.5)
ax[0].set(xlabel='Diffusion steps σ',ylabel='Spectral dimension',title='Short-time sampling precision')
ax[0].legend(fontsize=8)
for value in [.2,.4,.6,.8]:
    use=(rho['rho']==value)&(rho['rho_sigma']>=8)&(rho['rho_sigma']<=80)
    ax[1].plot(rho['rho_sigma'][use],rho['Ds_of_mean_P'][use],label=f'ρ = {value}')
ax[1].set(xlabel='Rescaled diffusion time ρσ',ylabel='Spectral dimension',title='Rate scaling from saved returns')
ax[1].legend(fontsize=8)
fig.suptitle('Baseline pilot · 32 geometries · equilibrium not certified',fontsize=12)
for ext in ['pdf','png']:fig.savefig(f/f'{a.job}_precision_and_rho.{ext}',dpi=160)
