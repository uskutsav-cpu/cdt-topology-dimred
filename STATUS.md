# Status

ACTIVE — baseline spectral reproduction and longer chain diagnostics.

| Gate | Status |
|---|---|
| Untouched upstream builds | PASS |
| Detailed-balance audit | Explicit corrections derived and tested; upstream differs |
| Geometry and deterministic simulation | PASS on tested debug/pilot configurations |
| Exact local checkpoint recovery | PASS for tuning and measurement interruptions |
| Thermalized phase-C ensembles | Not established |
| Ordinary spectral reproduction | Not established |
| 2D effective topology | Not started: prerequisite gate |
| 3D coarse-graining / stratification | Not started: prerequisite gates |
| Conditioned result / controls / scaling | Not computed |

No primary scientific result has been obtained. See DECISIONS.md for the
upstream discrepancies and results/manifests for actual completed jobs.

One independent N10000 chain now passes the single-chain screens, but the
slow-mode cross-chain Rhat remains1.033; the reproduction gate stays closed.
