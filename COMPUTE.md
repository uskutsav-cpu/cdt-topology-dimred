# Measured compute information

Host: Apple Silicon macOS, 8 logical CPU cores, 8 GiB physical RAM (read-only
hardware query). Python 3.13, pinned NumPy/SciPy and Apple C++14 toolchain.
No GPU acceleration has been measured or claimed. Keep large simulator jobs
sequential to preserve headroom for the desktop application and analysis.

Measured on the first 10,000-tetrahedron chain: 498 million attempted moves,
401.6 seconds for the C++ simulation, 717.7 seconds including independent
Python geometry validation and compressed export. This includes 128 saved
configurations; the cost is not exclusively Monte Carlo. Slice validation has
since been changed from repeated scans over every face to one grouping pass.
The speedup must be measured on subsequent completed jobs, not assumed.

The 3,000-tetrahedron pilot took 80.8 seconds including validation, for 39.84
million attempted moves and 128 snapshots. These two total runtimes must not
be fit as a pure volume scaling law: their move and output counts differ.

For one 2,786-tetrahedron geometry, exact propagation at 256 starts and 128
steps took 0.684 seconds; 256 stochastic-trace probes took 0.856 seconds;
500,000 walks took 3.747 seconds. See diffusion_benchmark.json for errors.
The exact 256-start calculation uses about N3*256*8 bytes per dense state
array (5.4 MiB at this size, excluding copies and sparse storage).

At N3=200,000, one 256-column float64 propagation state alone would use
409.6 MB; practical peak memory includes at least two state arrays and graph
storage. Basis starts must therefore be processed in batches. With CSR graph
degree four, work is approximately proportional to N3 * starts * sigma,
subject to memory bandwidth and cache changes. Do not extrapolate measured
small-size timings as validated large-size performance.

Upstream uses fixed-capacity pools for 3,000,000 vertices, 5,000,000 tetrahedra,
5,000,000 halfedges and 1,000,000 triangles. Their allocations and Bag arrays
have substantial fixed cost even at small N3. Checkpoint storage saves only
the used prefix and necessary free-list/order state: the 10,000-tetrahedron
continuation checkpoints observed so far are approximately 0.68 MB.

Current exact commands (from project root, with installed pinned environment):

```sh
.venv/bin/python workflows/run_chain.py configs/reproduction/extended_10000.json
.venv/bin/python workflows/run_chain.py configs/reproduction/extended_10000.json --resume
```

The second command resumes only a failed same-binary job with a checkpoint;
completed jobs are hash-verified and skipped. It is not an instruction to
start both commands concurrently. Numerical production remains gated on
baseline reproduction and validated topology, and has not yet been launched.
