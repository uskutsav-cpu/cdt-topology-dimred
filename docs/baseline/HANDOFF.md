# Native baseline: installation, review branch, and reproduction

## What is complete

The code, native build/replay fixes, tests, raw pilot, diagnostics, ordinary-diffusion measurements, plots, and independent evidence verification are delivered. The pilot does NOT establish equilibrium or the historical baseline reproduction. See RESEARCH_REPORT.md and EXECUTED_SUMMARY.json.

No GitHub changes were made by the assistant. The package targets a descendant of `6fafad81840ecb03cc858953352b227d242d5ee1`.

## 1. Extract the code ZIP once

Download `cdt-native-baseline-update.zip` into Downloads. This ZIP already contains its top-level directory. Do NOT supply another directory with the same name after `-d`.

```bash
cd "$HOME/Downloads" && unzip -n cdt-native-baseline-update.zip
```

The scripts should now be at:

```text
~/Downloads/cdt-native-baseline-update/VERIFY_BUNDLE.py
~/Downloads/cdt-native-baseline-update/APPLY_UPDATE.py
```

Verify:

```bash
python3 "$HOME/Downloads/cdt-native-baseline-update/VERIFY_BUNDLE.py"
```

## 2. Apply only on a review branch

The installer refuses `main`, `master`, detached HEAD, a dirty worktree, a wrong remote, a non-descendant commit, unsafe paths, modified payloads, and differing existing files. It never commits, pushes, resets, stashes, or changes an existing production gate.

Run this block. Its `&&` operators stop subsequent commands after an error.

```bash
cd "/Users/swethasunilkumar/Documents/Codex/2026-09-07/do-t/outputs/cdt-topology-dimred" &&
git fetch origin &&
git switch -c native-baseline-review origin/main &&
python3 "$HOME/Downloads/cdt-native-baseline-update/APPLY_UPDATE.py" "$PWD" --dry-run &&
python3 "$HOME/Downloads/cdt-native-baseline-update/APPLY_UPDATE.py" "$PWD"
```

An existing `native-baseline-review` branch is not overwritten. Inspect it rather than forcing branch replacement. An installer conflict is likewise a review stop, not permission to overwrite a newer file.

## 3. Test the installed code

Use an environment outside the Git checkout:

```bash
python3 -m venv "$HOME/.venvs/cdt-native-baseline" &&
"$HOME/.venvs/cdt-native-baseline/bin/python" -m pip install -r environment/baseline-requirements.txt &&
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/test_native_baseline.py
```

This runs the 139 new baseline tests, including native builds and a small end-to-end Monte Carlo study. The delivery's recorded 148-test combined run additionally included nine existing baseline tests, using a native-compatible T8 fixture. The old 601-test confirmation suite and the complete original test collection are not silently included in this number.

## 4. Review and push the code, not the multi-gigabyte pilot

```bash
git add .github/workflows/native-baseline.yml src/cdt_baseline configs/baseline environment/baseline-requirements.txt environment/baseline-tested.json tests/baseline_native workflows/baseline.py workflows/test_native_baseline.py workflows/fresh_baseline_checkout.py workflows/plot_native_baseline.py docs/baseline validation/baseline &&
git diff --cached --stat &&
git diff --cached --name-only
```

Review the staged filenames. The data archive directory must not appear in that list. Then:

```bash
git commit -m "Add audited native CDT baseline pipeline and executed pilot assessment" &&
git push --set-upstream origin native-baseline-review
```

The supplied GitHub Actions definition tests Linux and macOS. It has not run on GitHub yet. A green code check is not a physical reproduction certificate. Do not force-push `main` or merge blindly around a failed check.

## 5. Genuine clean-checkout workflow

After the review branch is pushed, create a new checkout with the delivered helper:

```bash
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/fresh_baseline_checkout.py "$HOME/Documents/cdt-native-baseline-clean" --branch native-baseline-review
```

This refuses an existing destination. It clones the pushed branch and pinned submodule without overlaying local files, verifies cleanliness, and writes its receipt inside `.git`. It does not run the large schedule unless explicitly asked with `--run`.

From that new checkout, inspect the long-run budget before launching it:

```bash
cd "$HOME/Documents/cdt-native-baseline-clean" &&
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/baseline.py plan --config configs/baseline/production.json
```

The production preset has a much larger proposal budget than the executed pilot. No runtime or convergence guarantee is attached to it. Start it explicitly:

```bash
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/baseline.py all --config configs/baseline/production.json --output "$HOME/Documents/cdt-native-baseline-production" --workers 2 --timeout-seconds 7200
```

The output is outside the checkout. The timeout is per native job, not a total campaign time limit. A checkpointed pause exits with code 75. Rerunning the same command resumes compatible paused work; it verifies completed artifacts rather than overwriting them. Ctrl+C requests a bounded shutdown and checkpoint. Do not delete a job folder to bypass a failure.

Read-only progress:

```bash
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/baseline.py status --output "$HOME/Documents/cdt-native-baseline-production"
```

A manifest marked running is not asserted to prove that a process is still live.

## 6. Explicit same-chain extension

On the SAME build/platform and study, increase total snapshots per chain rather than pretending restarted checkpoint forks are independent:

```bash
"$HOME/.venvs/cdt-native-baseline/bin/python" workflows/baseline.py extend --samples 2048 --output "$HOME/Documents/cdt-native-baseline-production" --workers 2 --timeout-seconds 7200
```

Only the sample count may increase within a study. Couplings, warmup, seeds, sampling stride, root policy, and other parameters remain fixed. A revised warmup or physical design requires a new study directory. All earlier samples and revision metadata remain preserved.

The archived pilot's Linux checkpoint is NOT a portable Mac checkpoint. Rebuild and start a new Mac study; do not force an incompatible resume.

## 7. Full delivered evidence

The raw pilot is separate from the code ZIP:

```text
cdt-native-evidence-common.zip
cdt-native-evidence-10000.zip
cdt-native-evidence-30000.zip
cdt-native-evidence-60000.zip
```

Extract all four into the same parent directory. They reconstruct one `cdt-native-baseline-evidence` directory; they do not overwrite your Git repository.

For example, after downloading all four into Downloads:

```bash
mkdir -p "$HOME/Documents/cdt-native-evidence"
for part in "$HOME"/Downloads/cdt-native-evidence-*.zip; do unzip -n "$part" -d "$HOME/Documents/cdt-native-evidence"; done
```

Verify archive contents without third-party packages:

```bash
python3 "$HOME/Documents/cdt-native-evidence/cdt-native-baseline-evidence/VERIFY_EVIDENCE.py"
```

Then verify scientific data and recompute the two primary statistics using the delivered exact source export:

```bash
"$HOME/.venvs/cdt-native-baseline/bin/python" "$HOME/Documents/cdt-native-evidence/cdt-native-baseline-evidence/source_export/workflows/baseline.py" verify --output "$HOME/Documents/cdt-native-evidence/cdt-native-baseline-evidence/native_pilot"
```

Expected distinction: `verified: true`, `REPRODUCTION_PASS: false`. The first is evidence integrity; the second is the scientific decision.

The original raw native and exact-propagation arrays are preserved. The code update carries compact summaries, plots, manifests, and logs. It does not automatically add these large data archives to Git history.
