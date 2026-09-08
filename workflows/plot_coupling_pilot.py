"""Plot the completed initial coupling scan from saved tables only."""
from pathlib import Path
import os, json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
record=json.loads((ROOT/'results/tables/coupling_pilot.json').read_text())
if record['pending_measurements']:raise RuntimeError('initial scan is incomplete')
data=np.genfromtxt(ROOT/'results/tables/coupling_pilot_curves.csv',names=True,delimiter=',')
plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(9.2,3.8),layout='constrained')
for k0 in np.unique(data['k0']):
    curve=data[(data['k0']==k0)&(data['sigma']>=10)&(data['sigma']<=240)]
    axes[0].loglog(curve['sigma'],curve['P_mean'],label=f'k₀ = {k0:g}')
    axes[1].semilogx(curve['sigma'],curve['Ds_of_mean_P'],label=f'k₀ = {k0:g}')
axes[0].set(xlabel='Diffusion steps σ',ylabel='Mean return probability')
axes[1].set(xlabel='Diffusion steps σ',ylabel='Spectral dimension Dₛ',ylim=(2.2,3.1))
axes[1].axhline(3,color='gray',linestyle=':',linewidth=1)
for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.15)
fig.suptitle('Initial coupling scan · N₃ target 30,000, T = 64, ρ = 0.8')
fig.supxlabel('16 configurations per coupling · convergence pending · descriptive curves',fontsize=9)
for suffix in ('pdf','png'):fig.savefig(ROOT/f'results/figures/coupling_pilot.{suffix}',dpi=180)
