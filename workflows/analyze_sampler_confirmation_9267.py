from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cdt_baseline.statistics import diagnostic

ROOT = REPO / "results/baseline/sampler_confirmation_9267_111_vs_211"

CFG = REPO / (
    "configs/baseline/"
    "native_reference_9267_18534_longburn_300k.json"
)

ARMS = ["control_111", "adddelete_211"]
METRICS = ["N0", "N3", "N31", "peak_slice"]

cfg = json.loads(CFG.read_text())
index = json.loads((ROOT / "index.json").read_text())

if index.get("complete") is not True:
    raise SystemExit("Confirmation run is not marked complete")

if index.get("jobs_complete") != 8:
    raise SystemExit(
        f"Expected 8 completed jobs; got {index.get('jobs_complete')}"
    )


def autocorr_fft(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    x -= np.mean(x)

    n = len(x)
    size = 1 << (2 * n - 1).bit_length()

    f = np.fft.rfft(x, size)
    acov = np.fft.irfft(
        f * np.conjugate(f), size
    )[:n]

    acov /= np.arange(n, 0, -1)

    if acov[0] <= 0:
        return np.asarray([1.0])

    return acov / acov[0]


def tau_initial_positive(x):
    acf = autocorr_fft(x)

    tau = 0.5
    positive_until = 0

    for lag in range(1, len(acf)):
        rho = float(acf[lag])

        if not np.isfinite(rho) or rho <= 0:
            break

        tau += rho
        positive_until = lag

    return {
        "tau_int_sweeps": float(tau),
        "approx_ess": float(len(x) / (2 * tau)),
        "positive_acf_until": int(positive_until),
        "acf_1000": (
            float(acf[1000])
            if len(acf) > 1000 else None
        ),
    }


def load_job(arm, chain):
    path = ROOT / arm / f"chain{chain}"

    manifest = json.loads(
        (path / "manifest.json").read_text()
    )

    with (path / "diagnostics.csv").open(newline="") as f:
        rows = [
            r for r in csv.DictReader(f)
            if r.get("phase") == "measure"
        ]

    if not rows:
        raise RuntimeError(
            f"No measurement rows for {arm} chain {chain}"
        )

    return rows, manifest


report = {
    "schema": "cdt-sampler-confirmation-analysis-v1",
    "arms": {},
}

chain_means = {}

for arm in ARMS:

    print("\n" + "=" * 90)
    print("ARM:", arm)
    print("=" * 90)

    loaded = [
        load_job(arm, chain)
        for chain in range(4)
    ]

    rows_by_chain = [x[0] for x in loaded]
    manifests = [x[1] for x in loaded]

    lengths = [len(x) for x in rows_by_chain]

    print("measurement rows/chain:", lengths)

    if len(set(lengths)) != 1:
        raise RuntimeError(
            f"Unequal confirmation chain lengths: {lengths}"
        )

    arm_report = {
        "diagnostics": {},
        "peak_tau": [],
        "move_acceptance": {},
        "proposal_fraction": {},
    }

    chain_means[arm] = {}

    for metric in METRICS:

        x = np.asarray([
            [float(r[metric]) for r in rows]
            for rows in rows_by_chain
        ])

        d = diagnostic(x, cfg["limits"])

        rec = {
            "rhat": float(d["rank_folded_rhat"]),
            "bulk_ess": float(d["bulk_ess"]),
            "tail_ess": float(d["tail_ess"]),
            "mcse_over_sd": float(
                d["mean_mcse_over_sd"]
            ),
            "chain_means": [
                float(v) for v in d["chain_means"]
            ],
            "pass": bool(d["pass_screen"]),
        }

        arm_report["diagnostics"][metric] = rec
        chain_means[arm][metric] = np.mean(x, axis=1)

        print("\n", metric)
        print(" Rhat:", rec["rhat"])
        print(" bulk ESS:", rec["bulk_ess"])
        print(" tail ESS:", rec["tail_ess"])
        print(" MCSE/SD:", rec["mcse_over_sd"])
        print(" means:", rec["chain_means"])
        print(" PASS:", rec["pass"])

    print("\nPEAK AUTOCORRELATION")

    taus = []
    tau_wall = []

    for chain in range(4):

        peak = np.asarray([
            float(r["peak_slice"])
            for r in rows_by_chain[chain]
        ])

        t = tau_initial_positive(peak)

        elapsed = float(
            manifests[chain]["elapsed_seconds"]
        )

        total_sweeps = (
            int(manifests[chain]["burn_sweeps"])
            + int(manifests[chain]["measurement_sweeps"])
        )

        sec_per_sweep = elapsed / total_sweeps

        t["chain"] = chain
        t["tau_wall_seconds"] = (
            t["tau_int_sweeps"] * sec_per_sweep
        )

        arm_report["peak_tau"].append(t)

        taus.append(t["tau_int_sweeps"])
        tau_wall.append(t["tau_wall_seconds"])

        print(
            f" chain {chain}: "
            f"tau={t['tau_int_sweeps']:.2f} sweeps "
            f"ESS≈{t['approx_ess']:.2f} "
            f"tau_wall≈{t['tau_wall_seconds']:.2f}s"
        )

    arm_report["median_tau"] = float(
        np.median(taus)
    )

    arm_report["median_tau_wall_seconds"] = float(
        np.median(tau_wall)
    )

    print(
        "\nMEDIAN tau:",
        arm_report["median_tau"]
    )

    print(
        "MEDIAN tau wall:",
        arm_report["median_tau_wall_seconds"]
    )

    attempt_totals = {}
    accept_totals = {}

    for move in range(1, 6):
        attempt_totals[move] = sum(
            float(r[f"attempt_{move}"])
            for rows in rows_by_chain
            for r in rows
        )

        accept_totals[move] = sum(
            float(r[f"accept_{move}"])
            for rows in rows_by_chain
            for r in rows
        )

    grand_attempts = sum(attempt_totals.values())

    print("\nMOVE MIX")

    for move in range(1, 6):

        proposal = (
            attempt_totals[move] / grand_attempts
        )

        acceptance = (
            accept_totals[move] / attempt_totals[move]
        )

        arm_report["proposal_fraction"][str(move)] = float(
            proposal
        )

        arm_report["move_acceptance"][str(move)] = float(
            acceptance
        )

        print(
            f" move {move}: "
            f"proposal={100*proposal:.3f}% "
            f"acceptance={100*acceptance:.3f}%"
        )

    report["arms"][arm] = arm_report


control = report["arms"]["control_111"]
candidate = report["arms"]["adddelete_211"]

tau_speedup = (
    control["median_tau"]
    / candidate["median_tau"]
)

wall_speedup = (
    control["median_tau_wall_seconds"]
    / candidate["median_tau_wall_seconds"]
)

candidate["tau_speedup_vs_control"] = float(
    tau_speedup
)

candidate["wall_speedup_vs_control"] = float(
    wall_speedup
)

print("\n" + "=" * 90)
print("HEAD TO HEAD")
print("=" * 90)

print("111 median tau:", control["median_tau"])
print("211 median tau:", candidate["median_tau"])
print("tau speedup:", tau_speedup)
print("wall speedup:", wall_speedup)


print("\nMATCHED MEAN SHIFTS")

matched = {}

for metric in METRICS:

    delta = (
        chain_means["adddelete_211"][metric]
        - chain_means["control_111"][metric]
    )

    matched[metric] = {
        "per_chain": [float(x) for x in delta],
        "mean_delta": float(np.mean(delta)),
        "median_delta": float(np.median(delta)),
    }

    print(
        metric,
        "mean delta=",
        matched[metric]["mean_delta"],
        "per-chain=",
        matched[metric]["per_chain"],
    )

candidate["matched_mean_deltas_vs_control"] = matched


counts_pass = all(
    candidate["diagnostics"][m]["pass"]
    for m in ("N0", "N3", "N31")
)

peak_pass = candidate["diagnostics"]["peak_slice"]["pass"]

speedup_confirmed = (
    tau_speedup >= 2.0
    and wall_speedup > 1.0
)

if speedup_confirmed and counts_pass and peak_pass:
    classification = "PRODUCTION_READY_211"

elif speedup_confirmed and counts_pass:
    classification = (
        "SPEEDUP_CONFIRMED_BUT_MIXING_GATE_NOT_CLOSED"
    )

else:
    classification = "211_NOT_CONFIRMED"

report["classification"] = classification

print("\n" + "=" * 90)
print("FINAL CLASSIFICATION")
print("=" * 90)
print(classification)

out = ROOT / "confirmation_analysis.json"

out.write_text(
    json.dumps(
        report,
        indent=2,
        sort_keys=True
    ) + "\n"
)

print("\nSAVED:", out)
