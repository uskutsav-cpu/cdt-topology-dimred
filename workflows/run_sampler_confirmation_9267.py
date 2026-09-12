from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

BINARY = (
    REPO /
    "build/baseline/493aa38ae6ae5a3c456d/cdt-run"
)

SOURCE = (
    REPO /
    "results/baseline/"
    "native_reference_9267_18534_longburn_300k"
)

OUT = (
    REPO /
    "results/baseline/"
    "sampler_confirmation_9267_111_vs_211"
)

VOLUME = 9267

ARMS = {
    "control_111": (1, 1, 1),
    "adddelete_211": (2, 1, 1),
}

# Longer, independent confirmation.
BURN_SWEEPS = 20_000
SAMPLES = 40
SAMPLE_STRIDE = 5_000

MEASUREMENT_SWEEPS = SAMPLES * SAMPLE_STRIDE
ATTEMPTS_PER_SWEEP = VOLUME

MAX_WORKERS = 4


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


if not BINARY.is_file():
    raise SystemExit(f"Missing binary: {BINARY}")

index = json.loads(
    (SOURCE / "chain_index.json").read_text()
)

entries = sorted(
    [
        e for e in index
        if int(e["volume"]) == VOLUME
        and e.get("status") == "complete"
    ],
    key=lambda e: int(e["chain"]),
)

if len(entries) != 4:
    raise SystemExit(
        f"Expected four V={VOLUME} chains; "
        f"found {len(entries)}"
    )


sources = []

for e in entries:

    chain = int(e["chain"])

    root = SOURCE / "raw" / e["job"]

    geometry = root / "geometry_127.dat"

    manifest = json.loads(
        (root / "manifest.json").read_text()
    )

    if not geometry.is_file():
        raise SystemExit(f"Missing {geometry}")

    p = manifest["parameters"]

    sources.append({
        "chain": chain,
        "source_job": e["job"],
        "geometry": geometry,
        "geometry_sha256": sha256(geometry),
        "k0": float(p["k0"]),
        "k3": float(p["k3"]),
    })


if OUT.exists():
    print(
        "Output directory already exists; "
        "completed jobs will be reused."
    )

OUT.mkdir(parents=True, exist_ok=True)


protocol = {
    "schema":
        "cdt-sampler-confirmation-v1",

    "volume":
        VOLUME,

    "arms":
        {
            name: list(weights)
            for name, weights in ARMS.items()
        },

    "matched_starting_geometries":
        True,

    "independent_from_pilot_rng":
        True,

    "matched_seed_within_chain":
        True,

    "burn_sweeps":
        BURN_SWEEPS,

    "measurement_sweeps":
        MEASUREMENT_SWEEPS,

    "sample_stride":
        SAMPLE_STRIDE,

    "samples":
        SAMPLES,

    "attempts_per_sweep":
        ATTEMPTS_PER_SWEEP,

    "predeclared_primary_estimand":
        "median per-chain peak_slice tau_int",

    "success_rule": {
        "tau_speedup_vs_control":
            ">=2.0",
        "wall_efficiency_speedup":
            ">1.0",
        "basic_count_diagnostics":
            "stable",
        "no_obvious_systematic_target_shift":
            True,
    },
}

(OUT / "protocol.json").write_text(
    json.dumps(
        protocol,
        indent=2,
        sort_keys=True,
    ) + "\n"
)


def run_job(arm, weights, src):

    chain = src["chain"]

    job = OUT / arm / f"chain{chain}"
    meta_path = job / "manifest.json"

    if meta_path.exists():

        old = json.loads(
            meta_path.read_text()
        )

        if (
            old.get("complete") is True
            and
            (job / "diagnostics.csv").is_file()
        ):
            print(
                f"REUSE {arm} chain={chain}",
                flush=True,
            )
            return old

    if job.exists():
        shutil.rmtree(job)

    job.mkdir(parents=True)

    original_hash = sha256(
        src["geometry"]
    )

    if (
        original_hash
        != src["geometry_sha256"]
    ):
        raise RuntimeError(
            "Source geometry hash changed"
        )

    v1, v2, v3 = weights

    # Different RNG from pilot.
    # Same seed across arms for the
    # same starting chain.
    seed = 202609130 + chain

    env = os.environ.copy()

    env["CDT_MOVE_V1"] = str(v1)
    env["CDT_MOVE_V2"] = str(v2)
    env["CDT_MOVE_V3"] = str(v3)

    cmd = [
        str(BINARY),
        str(src["geometry"]),
        str(job),
        str(seed),
        str(src["k0"]),
        str(src["k3"]),
        str(VOLUME),

        "0",

        str(BURN_SWEEPS),

        str(SAMPLES),

        str(ATTEMPTS_PER_SWEEP),

        "0",

        str(SAMPLE_STRIDE),
    ]

    print(
        f"START {arm} "
        f"chain={chain}",
        flush=True,
    )

    started = now()
    t0 = time.monotonic()

    log_path = job / "native.log"

    with log_path.open("w") as log:

        proc = subprocess.run(
            cmd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )

    elapsed = (
        time.monotonic() - t0
    )

    marker = (
        f"CDT_SAMPLER_WEIGHTS "
        f"v1={v1} v2={v2} v3={v3}"
    )

    text = log_path.read_text(
        errors="replace"
    )

    input_unchanged = (
        sha256(src["geometry"])
        == original_hash
    )

    complete = (
        proc.returncode == 0
        and marker in text
        and input_unchanged
        and
        (job / "diagnostics.csv").is_file()
    )

    result = {
        "complete":
            complete,

        "arm":
            arm,

        "weights":
            list(weights),

        "chain":
            chain,

        "seed":
            seed,

        "source_job":
            src["source_job"],

        "source_geometry_sha256":
            original_hash,

        "input_unchanged":
            input_unchanged,

        "returncode":
            proc.returncode,

        "sampler_marker_found":
            marker in text,

        "burn_sweeps":
            BURN_SWEEPS,

        "measurement_sweeps":
            MEASUREMENT_SWEEPS,

        "sample_stride":
            SAMPLE_STRIDE,

        "samples":
            SAMPLES,

        "elapsed_seconds":
            elapsed,

        "started_at":
            started,

        "finished_at":
            now(),
    }

    meta_path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        ) + "\n"
    )

    print(
        f"DONE {arm} "
        f"chain={chain} "
        f"complete={complete}",
        flush=True,
    )

    if not complete:
        raise RuntimeError(
            f"Failed {arm} "
            f"chain={chain}"
        )

    return result


jobs = []

for arm, weights in ARMS.items():
    for source in sources:
        jobs.append(
            (arm, weights, source)
        )


results = []
errors = []

with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:

    futures = {
        executor.submit(
            run_job,
            arm,
            weights,
            source,
        ):
        (arm, source["chain"])

        for arm, weights, source
        in jobs
    }

    for future in as_completed(
        futures
    ):

        arm, chain = futures[future]

        try:
            results.append(
                future.result()
            )

        except Exception as exc:
            errors.append({
                "arm":
                    arm,
                "chain":
                    chain,
                "error":
                    repr(exc),
            })


results.sort(
    key=lambda x: (
        x["arm"],
        x["chain"],
    )
)

summary = {
    "schema":
        "cdt-sampler-confirmation-index-v1",

    "complete":
        len(results) == 8
        and not errors,

    "jobs_expected":
        8,

    "jobs_complete":
        len(results),

    "errors":
        errors,

    "results":
        results,
}

(OUT / "index.json").write_text(
    json.dumps(
        summary,
        indent=2,
        sort_keys=True,
    ) + "\n"
)

print()
print("=" * 80)
print("CONFIRMATION SUMMARY")
print("=" * 80)
print(
    "jobs:",
    len(results),
    "/ 8",
)
print(
    "errors:",
    len(errors),
)
print(
    "burn/job:",
    BURN_SWEEPS,
)
print(
    "measurement/job:",
    MEASUREMENT_SWEEPS,
)
print(
    "complete:",
    summary["complete"],
)

if errors:
    raise SystemExit(1)
