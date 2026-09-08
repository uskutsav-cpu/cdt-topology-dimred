# Status

ACTIVE — baseline reproduction remains incomplete; tested synthetic topology
and conditioned-analysis components are now implemented.

| Component / gate | Saved status |
|---|---|
| Untouched upstream build / research patches | Prior build and explicit audit documented; unchanged in this update |
| Geometry / deterministic simulation / checkpoint recovery | Prior tested debug/pilot checks preserved; not rerun here |
| N10000 matched-chain diagnostic screens | PASS on saved 1536-snapshot comparisons; not proof of equilibrium |
| Full ordinary spectral reproduction | NOT ESTABLISHED; finite-volume/coupling/precision requirements remain |
| Finite-field global and local homology | IMPLEMENTED; exact synthetic checks over F2 and F11 |
| 2D sampling / Voronoi / incidence-preserving dual | IMPLEMENTED and synthetic-tested; CDT/EDT reproduction NOT ESTABLISHED |
| 3D coarse dual | EXPERIMENTAL; synthetic identity/incidence checks only |
| Integral canonical stratification | NOT IMPLEMENTED; local Betti vectors are not a substitute |
| Validated microscopic topology mapping | NOT ESTABLISHED |
| Conditioned diffusion / paired block uncertainty | IMPLEMENTED and synthetic-tested; production workflow gated |
| Primary conditioned result / controls / scaling | NOT COMPUTED |

## Latest saved baseline evidence

`results/tables/chain_comparison_4209d27d5996.json` compares 307200 measurement
sweeps in each N10000 chain. Peak-slice rank/folded split Rhat is
1.0072666345920425 and minimum split ESS is 73.0088209433157. The old 1.033
value described an earlier, shorter comparison and is superseded, not deleted.
The latest saved spectral comparison reports peaks 2.79156606 and 2.78553443.
See RESULTS.md for the underlying source filenames and remaining limitations.
Passing these configured screens is not REPRODUCTION_PASS.

## This implementation update

102 new Python tests passed locally; six topology fixtures, 16 2D and eight
experimental 3D coarse constructions were numerically checked. Evidence and
source/environment hashes are in `results/methods/`. This is not a rerun of
the legacy C++ suite or a new quantum-gravity ensemble. Existing raw results,
long-chain manifests, original driver and simulator patches were preserved.
Static running manifests do not establish current process liveness.

Read [methods and limits](docs/METHODS_IMPLEMENTED_2026-09-08.md) and
[continuation commands](docs/COMPUTATIONAL_HANDOFF.md). All four production
gates in `configs/methods/production_gates.json` remain NOT_ESTABLISHED.
No primary positive/null physics result or causal mechanism is claimed.
