# Reproduction log

1. Pinned upstream v1.0.1 builds unchanged. The repository's example script
   refers to a missing config.dat; generated initial geometries and explicit
   configurations are used instead.
2. Read the simulation paper and visually verified equations 26–27. Corrected
   the documented proposal factors and reverse volume penalty in a generated
   source copy. No unreported physics substitution.
3. Independent raw checks cover tetrahedron uniqueness, reciprocal face
   neighbors, two tetrahedra per face, periodic foliation, spherical slices,
   Euler characteristic and spherical vertex links.
4. Four move families including both oriented shifts restore the original
   simplices under inverse moves on an actual pilot configuration. The initial
   down-shift test passed its pair in the wrong orientation; correcting the
   test to the explicit upstream output ordering resolves that assertion.
5. Two same-seed debug chains produce identical snapshots. Twelve Python tests
   pass. Exact diffusion agrees with random walkers and stochastic traces.
6. A clean local clone with the pinned submodule builds from source; all 12
   Python tests and both interruption/restart checks pass. It uses the already
   installed pinned Python environment, not a second redundant installation.
7. The 3,000-volume pilot fails the effective-sample screen. The first
   10,000-volume chain passes its volume screen but fails the slower peak-slice
   screen. A longer continuation with explicit parent lineage is running.
8. Full-lattice returns are not treated as historical condensate-only results.
   Cos²/constant profile fitting and boundary/excision sensitivity are being
   measured. This individual-geometry fit is an explicit adaptation of the
   referenced averaged-profile prescription, with fit diagnostics saved.

REPRODUCTION_PASS: not issued. Finite-volume, rho and coupling trends remain
required before new effective-topology physics is computed.
