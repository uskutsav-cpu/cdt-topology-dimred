from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]

BINARY = (
    REPO
    / "build/baseline/493aa38ae6ae5a3c456d/cdt-run"
)

SOURCE_STUDY = (
    REPO
    / "results/baseline/"
      "native_reference_9267_18534_longburn_300k"
)

OUTPUT = (
    REPO
    / "results/baseline/"
      "sampler_pilot_9267_abc"
)

ARMS = {
    "control_111": (1, 1, 1),
    "adddelete_211": (2, 1, 1),
    "shift_112": (1, 1, 2),
}

VOLUME = 9267

BURN_SWEEPS = 10_000

SAMPLES = 12
SAMPLE_STRIDE = 5_000

MEASUREMENT_SWEEPS = SAMPLES * SAMPLE_STRIDE

ATTEMPTS_PER_SWEEP = VOLUME

MAX_WORKERS = 4


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)

            if not b:
                break

            h.update(b)

    return h.hexdigest()


if not BINARY.is_file():
    raise SystemExit(f"MISSING BINARY: {BINARY}")

index_path = SOURCE_STUDY / "chain_index.json"

if not index_path.is_file():
    raise SystemExit(f"MISSING: {index_path}")

index = json.loads(index_path.read_text())

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
        f"Expected four completed V={VOLUME} chains; "
        f"found {len(entries)}"
    )


sources = []

for e in entries:

    chain = int(e["chain"])
    source_job = SOURCE_STUDY / "raw" / e["job"]

    geometry = source_job / "geometry_127.dat"
    manifest_path = source_job / "manifest.json"

    if not geometry.is_file():
        raise SystemExit(f"MISSING: {geometry}")

    if not manifest_path.is_file():
        raise SystemExit(f"MISSING: {manifest_path}")

    manifest = json.loads(manifest_path.read_text())
    p = manifest["parameters"]

    sources.append(
        {
            "chain": chain,
            "geometry": geometry,
            "geometry_sha256": sha256(geometry),
            "k0": float(p["k0"]),
            "k3": float(p["k3"]),
            "target": int(p["target"]),
            "source_job": e["job"],
        }
    )


k0s = {s["k0"] for s in sources}
k3s = {s["k3"] for s in sources}
targets = {s["target"] for s in sources}

if len(k0s) != 1:
    raise SystemExit(f"k0 mismatch: {k0s}")

if len(k3s) != 1:
    raise SystemExit(f"k3 mismatch: {k3s}")

if targets != {VOLUME}:
    raise SystemExit(f"target mismatch: {targets}")


OUTPUT.mkdir(parents=True, exist_ok=True)

binary_sha = sha256(BINARY)


protocol = {
    "schema": "cdt-sampler-pilot-v1",
    "volume": VOLUME,
    "arms": {
        name: list(weights)
        for name, weights in ARMS.items()
    },
    "starting_geometry": "geometry_127.dat",
    "matched_starting_geometries": True,
    "matched_seed_within_chain_across_arms": True,
    "burn_sweeps": BURN_SWEEPS,
    "measurement_sweeps": MEASUREMENT_SWEEPS,
    "samples": SAMPLES,
    "sample_stride": SAMPLE_STRIDE,
    "attempts_per_sweep": ATTEMPTS_PER_SWEEP,
    "binary": str(BINARY.relative_to(REPO)),
    "binary_sha256": binary_sha,
    "purpose": (
        "Compare slow-mode mixing under control, "
        "add/delete-heavy and shift-heavy proposal mixtures. "
        "No spectral/topology inference."
    ),
}

(OUTPUT / "protocol.json").write_text(
    json.dumps(protocol, indent=2, sort_keys=True) + "\n"
)


def run_one(arm, weights, src):

    chain = src["chain"]

    out = OUTPUT / arm / f"chain{chain}"
    manifest_path = out / "pilot_manifest.json"

    if manifest_path.is_file():

        old = json.loads(manifest_path.read_text())

        if (
            old.get("complete") is True
            and old.get("returncode") == 0
            and (out / "diagnostics.csv").is_file()
        ):
            print(
                f"REUSE {arm} chain={chain}",
                flush=True,
            )
            return old

    if out.exists() and any(out.iterdir()):
        raise RuntimeError(
            f"Incomplete/nonempty pilot directory exists: {out}"
        )

    out.mkdir(parents=True, exist_ok=True)

    geometry = src["geometry"]

    original_hash = sha256(geometry)

    if original_hash != src["geometry_sha256"]:
        raise RuntimeError(
            f"Source geometry changed before launch: {geometry}"
        )

    v1, v2, v3 = weights

    seed = 202609120 + chain

    env = os.environ.copy()

    env["CDT_MOVE_V1"] = str(v1)
    env["CDT_MOVE_V2"] = str(v2)
    env["CDT_MOVE_V3"] = str(v3)

    cmd = [
        str(BINARY),
        str(geometry),
        str(out),
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

    started = now()
    t0 = time.monotonic()

    log_path = out / "native.log"

    print(
        f"START {arm} chain={chain} "
        f"weights={weights}",
        flush=True,
    )

    with log_path.open("w") as log:

        proc = subprocess.run(
            cmd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )

    elapsed = time.monotonic() - t0

    source_after = sha256(geometry)

    marker = (
        f"CDT_SAMPLER_WEIGHTS "
        f"v1={v1} v2={v2} v3={v3}"
    )

    log_text = log_path.read_text(
        errors="replace"
    )

    marker_ok = marker in log_text
    input_unchanged = source_after == original_hash

    complete = (
        proc.returncode == 0
        and marker_ok
        and input_unchanged
        and (out / "diagnostics.csv").is_file()
    )

    result = {
        "schema": "cdt-sampler-pilot-job-v1",
        "complete": complete,
        "arm": arm,
        "weights": list(weights),
        "chain": chain,
        "seed": seed,
        "volume": VOLUME,
        "k0": src["k0"],
        "k3": src["k3"],
        "source_job": src["source_job"],
        "source_geometry": str(
            geometry.relative_to(REPO)
        ),
        "source_geometry_sha256": original_hash,
        "input_unchanged": input_unchanged,
        "binary": str(BINARY.relative_to(REPO)),
        "binary_sha256": binary_sha,
        "burn_sweeps": BURN_SWEEPS,
        "measurement_sweeps": MEASUREMENT_SWEEPS,
        "samples": SAMPLES,
        "sample_stride": SAMPLE_STRIDE,
        "attempts_per_sweep": ATTEMPTS_PER_SWEEP,
        "sampler_marker_found": marker_ok,
        "returncode": proc.returncode,
        "started_at": started,
        "finished_at": now(),
        "elapsed_seconds": elapsed,
    }

    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True)
        + "\n"
    )

    print(
        f"DONE  {arm} chain={chain} "
        f"return={proc.returncode} "
        f"marker={marker_ok} "
        f"unchanged={input_unchanged}",
        flush=True,
    )

    if not complete:
        raise RuntimeError(
            f"Pilot failed: {arm} chain={chain}. "
            f"See {log_path}"
        )

    return result


jobs = []

for arm, weights in ARMS.items():
    for src in sources:
        jobs.append(
            (arm, weights, src)
        )


results = []
errors = []

with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as pool:

    future_map = {
        pool.submit(
            run_one,
            arm,
            weights,
            src,
        ): (arm, src["chain"])
        for arm, weights, src in jobs
    }

    for future in as_completed(future_map):

        arm, chain = future_map[future]

        try:
            results.append(future.result())

        except Exception as exc:
            errors.append(
                {
                    "arm": arm,
                    "chain": chain,
                    "error": repr(exc),
                }
            )

            print(
                "ERROR",
                arm,
                "chain",
                repr(exc),
                flush=True,
            )


results.sort(
    key=lambda x: (
        x["arm"],
        x["chain"],
    )
)

index_out = {
    "schema": "cdt-sampler-pilot-index-v1",
    "complete": not errors and len(results) == 12,
    "jobs_expected": 12,
    "jobs_complete": len(results),
    "errors": errors,
    "results": results,
}

(OUTPUT / "pilot_index.json").write_text(
    json.dumps(index_out, indent=2, sort_keys=True)
    + "\n"
)


print()
print("=" * 80)
print("SAMPLER PILOT SUMMARY")
print("=" * 80)
print("output:", OUTPUT)
print("jobs complete:", len(results), "/ 12")
print("errors:", len(errors))
print(
    "measurement sweeps/job:",
    MEASUREMENT_SWEEPS,
)
print(
    "total sweeps/job:",
    BURN_SWEEPS + MEASUREMENT_SWEEPS,
)
print(
    "complete:",
    index_out["complete"],
)

if errors:
    raise SystemExit(1)
