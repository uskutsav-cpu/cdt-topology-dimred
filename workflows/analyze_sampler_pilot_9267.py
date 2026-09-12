from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO / "src"))

from cdt_baseline.statistics import diagnostic


PILOT = (
    REPO
    / "results/baseline/"
      "sampler_pilot_9267_abc"
)

CFG = (
    REPO
    / "configs/baseline/"
      "native_reference_9267_18534_longburn_300k.json"
)

ARMS = [
    "control_111",
    "adddelete_211",
    "shift_112",
]

METRICS = [
    "N0",
    "N3",
    "N31",
    "peak_slice",
]

cfg = json.loads(CFG.read_text())

pilot_index = json.loads(
    (PILOT / "pilot_index.json").read_text()
)

if pilot_index.get("complete") is not True:
    raise SystemExit("Pilot is not marked complete")

if pilot_index.get("jobs_complete") != 12:
    raise SystemExit(
        f"Expected 12 jobs, got "
        f"{pilot_index.get('jobs_complete')}"
    )


def autocorr_fft(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]

    if len(x) < 4:
        return np.asarray([1.0])

    x = x - np.mean(x)

    variance = np.dot(x, x)

    if variance <= 0:
        return np.asarray([1.0])

    n = len(x)

    size = 1 << (2 * n - 1).bit_length()

    f = np.fft.rfft(x, size)

    acov = np.fft.irfft(
        f * np.conjugate(f),
        size,
    )[:n]

    acov /= np.arange(n, 0, -1)

    return acov / acov[0]


def tau_same_as_previous_audit(x, max_lag=30000):
    """
    Same convention used in the earlier sampler audit:

        tau = 0.5 + sum positive rho(lag)

    Therefore approximate ESS = N / (2*tau).

    We deliberately preserve this convention so the new pilot
    numbers are directly comparable with the old 2376..8398
    sweep values.
    """

    acf = autocorr_fft(x)

    upper = min(len(acf) - 1, max_lag)

    tau = 0.5
    positive_until = 0

    for lag in range(1, upper + 1):

        rho = float(acf[lag])

        if not np.isfinite(rho):
            break

        if rho <= 0:
            break

        tau += rho
        positive_until = lag

    return {
        "tau_int_sweeps": float(tau),
        "approx_ess": float(
            len(x) / (2 * tau)
        ),
        "positive_acf_until": int(
            positive_until
        ),
        "acf_1": (
            float(acf[1])
            if len(acf) > 1
            else None
        ),
        "acf_10": (
            float(acf[10])
            if len(acf) > 10
            else None
        ),
        "acf_100": (
            float(acf[100])
            if len(acf) > 100
            else None
        ),
        "acf_1000": (
            float(acf[1000])
            if len(acf) > 1000
            else None
        ),
    }


def load_chain(arm, chain):

    root = PILOT / arm / f"chain{chain}"

    diagnostics = root / "diagnostics.csv"
    manifest = root / "pilot_manifest.json"

    if not diagnostics.is_file():
        raise RuntimeError(
            f"Missing diagnostics: {diagnostics}"
        )

    if not manifest.is_file():
        raise RuntimeError(
            f"Missing manifest: {manifest}"
        )

    meta = json.loads(manifest.read_text())

    if meta.get("complete") is not True:
        raise RuntimeError(
            f"Incomplete job: {arm} chain {chain}"
        )

    with diagnostics.open(newline="") as f:

        rows = [
            row
            for row in csv.DictReader(f)
            if row.get("phase") == "measure"
        ]

    if not rows:
        raise RuntimeError(
            f"No measurement rows: "
            f"{arm} chain {chain}"
        )

    return rows, meta


report = {
    "schema": "cdt-sampler-pilot-analysis-v1",
    "arms": {},
}

chain_means = {}

for arm in ARMS:

    print()
    print("=" * 92)
    print("ARM:", arm)
    print("=" * 92)

    loaded = [
        load_chain(arm, chain)
        for chain in range(4)
    ]

    rows_by_chain = [
        item[0]
        for item in loaded
    ]

    manifests = [
        item[1]
        for item in loaded
    ]

    lengths = [
        len(rows)
        for rows in rows_by_chain
    ]

    print(
        "measurement rows/chain:",
        lengths,
    )

    if len(set(lengths)) != 1:
        raise RuntimeError(
            f"Unequal chain lengths: {lengths}"
        )

    arm_report = {
        "rows_per_chain": lengths,
        "diagnostics": {},
        "peak_tau": [],
        "move_acceptance": {},
        "proposal_fraction": {},
        "elapsed_seconds": [
            float(m["elapsed_seconds"])
            for m in manifests
        ],
    }

    chain_means[arm] = {}

    for metric in METRICS:

        x = np.asarray(
            [
                [
                    float(row[metric])
                    for row in rows
                ]
                for rows in rows_by_chain
            ],
            dtype=float,
        )

        d = diagnostic(
            x,
            cfg["limits"],
        )

        rec = {
            "rhat": float(
                d["rank_folded_rhat"]
            ),
            "bulk_ess": float(
                d["bulk_ess"]
            ),
            "tail_ess": float(
                d["tail_ess"]
            ),
            "mcse_over_sd": float(
                d["mean_mcse_over_sd"]
            ),
            "chain_means": [
                float(v)
                for v in d["chain_means"]
            ],
            "pass": bool(
                d["pass_screen"]
            ),
        }

        arm_report["diagnostics"][metric] = rec

        chain_means[arm][metric] = np.mean(
            x,
            axis=1,
        )

        print()
        print(metric)
        print("  Rhat:", rec["rhat"])
        print(
            "  bulk ESS:",
            rec["bulk_ess"],
        )
        print(
            "  tail ESS:",
            rec["tail_ess"],
        )
        print(
            "  MCSE/SD:",
            rec["mcse_over_sd"],
        )
        print(
            "  chain means:",
            rec["chain_means"],
        )
        print(
            "  PASS:",
            rec["pass"],
        )

    print()
    print("PEAK_SLICE AUTOCORRELATION")

    tau_wall = []

    for chain in range(4):

        peak = np.asarray(
            [
                float(r["peak_slice"])
                for r in rows_by_chain[chain]
            ],
            dtype=float,
        )

        t = tau_same_as_previous_audit(
            peak
        )

        elapsed = float(
            manifests[chain]["elapsed_seconds"]
        )

        total_sweeps = (
            int(
                manifests[chain][
                    "burn_sweeps"
                ]
            )
            +
            int(
                manifests[chain][
                    "measurement_sweeps"
                ]
            )
        )

        sec_per_sweep = (
            elapsed / total_sweeps
        )

        t["chain"] = chain

        t["elapsed_seconds"] = elapsed

        t["seconds_per_sweep"] = (
            sec_per_sweep
        )

        t["tau_wall_seconds"] = (
            t["tau_int_sweeps"]
            * sec_per_sweep
        )

        arm_report["peak_tau"].append(t)

        tau_wall.append(
            t["tau_wall_seconds"]
        )

        print(
            f"  chain {chain}: "
            f"tau={t['tau_int_sweeps']:.2f} sweeps "
            f"ESS≈{t['approx_ess']:.2f} "
            f"ACF1000={t['acf_1000']} "
            f"tau_wall≈{t['tau_wall_seconds']:.2f}s"
        )

    taus = np.asarray(
        [
            x["tau_int_sweeps"]
            for x in arm_report["peak_tau"]
        ]
    )

    arm_report["median_tau"] = float(
        np.median(taus)
    )

    arm_report["mean_tau"] = float(
        np.mean(taus)
    )

    arm_report["min_tau"] = float(
        np.min(taus)
    )

    arm_report["max_tau"] = float(
        np.max(taus)
    )

    arm_report[
        "median_tau_wall_seconds"
    ] = float(
        np.median(tau_wall)
    )

    print()
    print(
        "MEDIAN tau:",
        arm_report["median_tau"],
    )

    print(
        "MEDIAN tau wall seconds:",
        arm_report[
            "median_tau_wall_seconds"
        ],
    )

    print()
    print("MOVE MIX")

    for move in range(1, 6):

        total_attempt = 0.0
        total_accept = 0.0

        for rows in rows_by_chain:

            total_attempt += sum(
                float(r[f"attempt_{move}"])
                for r in rows
            )

            total_accept += sum(
                float(r[f"accept_{move}"])
                for r in rows
            )

        rate = (
            total_accept / total_attempt
            if total_attempt > 0
            else float("nan")
        )

        arm_report[
            "move_acceptance"
        ][str(move)] = float(rate)

    attempt_totals = {
        move: 0.0
        for move in range(1, 6)
    }

    for rows in rows_by_chain:

        for move in range(1, 6):

            attempt_totals[move] += sum(
                float(r[f"attempt_{move}"])
                for r in rows
            )

    grand_attempts = sum(
        attempt_totals.values()
    )

    for move in range(1, 6):

        frac = (
            attempt_totals[move]
            / grand_attempts
        )

        arm_report[
            "proposal_fraction"
        ][str(move)] = float(frac)

        print(
            f"  move {move}: "
            f"proposal={100*frac:.3f}% "
            f"acceptance="
            f"{100*arm_report['move_acceptance'][str(move)]:.3f}%"
        )

    report["arms"][arm] = arm_report


control_tau = report["arms"][
    "control_111"
]["median_tau"]

control_wall = report["arms"][
    "control_111"
]["median_tau_wall_seconds"]


print()
print("=" * 92)
print("HEAD-TO-HEAD")
print("=" * 92)

for arm in ARMS:

    a = report["arms"][arm]

    tau_speedup = (
        control_tau
        / a["median_tau"]
    )

    wall_speedup = (
        control_wall
        / a["median_tau_wall_seconds"]
    )

    a[
        "tau_speedup_vs_control"
    ] = float(tau_speedup)

    a[
        "wall_efficiency_speedup_vs_control"
    ] = float(wall_speedup)

    print()
    print(arm)

    print(
        "  median tau:",
        a["median_tau"],
    )

    print(
        "  tau speedup vs 111:",
        tau_speedup,
    )

    print(
        "  wall-efficiency speedup vs 111:",
        wall_speedup,
    )


print()
print("=" * 92)
print("MATCHED CHAIN-MEAN SHIFTS VS CONTROL")
print("=" * 92)

for arm in (
    "adddelete_211",
    "shift_112",
):

    print()
    print(arm)

    report["arms"][arm][
        "matched_mean_deltas_vs_control"
    ] = {}

    for metric in METRICS:

        delta = (
            chain_means[arm][metric]
            -
            chain_means[
                "control_111"
            ][metric]
        )

        rec = {
            "per_chain": [
                float(v)
                for v in delta
            ],
            "mean_delta": float(
                np.mean(delta)
            ),
            "median_delta": float(
                np.median(delta)
            ),
        }

        report["arms"][arm][
            "matched_mean_deltas_vs_control"
        ][metric] = rec

        print(
            f"  {metric}: "
            f"mean delta={rec['mean_delta']:+.6g} "
            f"per-chain={rec['per_chain']}"
        )


candidate_rows = []

for arm in (
    "adddelete_211",
    "shift_112",
):

    a = report["arms"][arm]

    candidate_rows.append(
        (
            arm,
            a[
                "tau_speedup_vs_control"
            ],
            a[
                "wall_efficiency_speedup_vs_control"
            ],
        )
    )

candidate_rows.sort(
    key=lambda x: (
        x[1],
        x[2],
    ),
    reverse=True,
)

best_arm, best_tau_speedup, best_wall_speedup = (
    candidate_rows[0]
)

if (
    best_tau_speedup >= 2.0
    and best_wall_speedup > 1.0
):
    classification = (
        f"STRONG_CANDIDATE:{best_arm}"
    )

elif (
    best_tau_speedup >= 1.5
    and best_wall_speedup > 1.0
):
    classification = (
        f"MODEST_CANDIDATE:{best_arm}"
    )

else:
    classification = (
        "NO_SIMPLE_WEIGHT_WINNER"
    )

report["classification"] = classification

print()
print("=" * 92)
print("PILOT CLASSIFICATION")
print("=" * 92)
print(classification)

out = PILOT / "sampler_pilot_analysis.json"

out.write_text(
    json.dumps(
        report,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print()
print("SAVED:", out)
