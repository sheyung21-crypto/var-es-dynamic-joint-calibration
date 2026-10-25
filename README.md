# Research Reproducibility Package

Documentation dated 25 October 2026. Changes made in preparing this package are listed in `provenance/Packaging_Changes.md`.

## Research Overview

Companion manuscript: *Dynamic Joint Calibration of Combined VaR and ES Forecasts: Evidence from US Industries and the Yen*, Shih-Yung Yang, version of 25 October 2026.

This package accompanies the paper on dynamic joint calibration of value-at-risk (VaR) and expected shortfall (ES). It preserves the forecasting algorithms, fixed settings, input identities and empirical results reported in the 26-page English manuscript (version of 25 October 2026, PDF SHA-256 `423d38790bed708398852b53f91c45a213ba2c34017b9e49d7560e8d0abbdbf9`). The verification records in `outputs/verification/` refer to the version of 24 October 2026 (SHA-256 `86f29e6265870500ec6f4f653a1622fb0ba96dcc6512dffbba10b2f0104678d4`); the later version adds only the ORCID, code-availability and funding lines, and its tables and numerical text are identical.

Study 1 evaluates 30 US industry portfolios and six international equity indices. Study 2 applies the frozen procedure to an earlier Japanese-yen sample. The central comparison is EW+DJC versus the uncalibrated equal-weight combination (EW), using the FZ0 score at the 97.5% level (alpha = 0.025). The industry comparisons with daily batch calibration and the adapted Ye-type controller are also primary; the 99% level and the remaining comparisons are secondary. Code labels A0, A2, F and R0 correspond to EW, EW+DJC, EW+DJC-FIX and GJR. The complete mapping appears in `outputs/reproduced/tables/Table_1.csv`.

## Prespecified Design

The analysis plans were frozen before the evaluation data were analysed (Study 1) or downloaded (Study 2). `provenance/Prespecified_Design.md` summarizes both plans and lists the freeze commits (Study 1: `c429d8e`, 24 October 2026 06:40 +08:00; Study 2: `54a4ce2`, 24 October 2026 08:59 +08:00) and the SHA-256 digests of the original protocol files, which are retained by the author. `code/core/confirm/freeze_params.json` holds the frozen numerical settings.

## Data

`Data_Sources.pdf` documents the providers, requested URLs, sample periods, actual input fields, transformations and distribution boundaries. `data/sample_inventory.csv` lists the 37 evaluation series individually.

- **Industries:** Kenneth R. French Data Library, daily value-weighted 30-industry returns, 1 July 1963-31 August 2026. Main evaluation contains 12,897 dates per industry, beginning 3 July 1975. Percentage simple returns are transformed by `100*log1p(r/100)`.
- **Equity indices:** Yahoo Finance archived close fields for ^TWII, ^KS11, ^FTSE, ^GDAXI, ^AXJO and ^GSPTSE. Market-specific sample dates and missing-value counts are in the inventory. Returns are `100*log(P[t]/P[t-1])` after invalid closes are removed. Adjusted close is not used.
- **Historical yen:** Federal Reserve Board H.10 through FRED, DEXJPUS, yen per US dollar. The supplied public-domain CSV contains the original 24 October 2026 download for 1974-2009. Removing 348 missing levels leaves 9,044 levels and 9,043 returns; evaluation covers 24 December 1985-31 December 2009 (6,043 dates).

Only the FRED raw input is bundled. Redistribution permission for the French and Yahoo originals was not established, so their raw files and reversible return copies are omitted. Study 1 can be rerun with lawfully obtained files matching the seven hashes in `data/study1/expected_fetch_manifest.json`. See `data/ACCESS.md` for the required directory structure and access procedure. A new provider download is not necessarily the same historical vintage. The archived results remain available for numerical inspection and figure/table reconstruction without these external inputs.

The frozen development settings are retained; this package does not retune the method. Development provenance is distinguished from the evaluation datasets in the data-source documentation.

## Requirements

The numerical replay was run with 64-bit CPython **3.11.9 on Windows**. `requirements.txt` pins all 17 numerical, plotting and transitive dependencies observed in the replay environment: NumPy 2.4.3, pandas 3.0.1, SciPy 1.17.1, arch 8.0.0, Matplotlib 3.11.0 and statsmodels 0.14.6, among others. The clean-environment installation and relocated-package test are recorded in `outputs/verification/`. Neither R, Microsoft Word nor LaTeX is required to reproduce the results. PDF documentation is supplied already rendered.

For Windows PowerShell, from the extracted package directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -I -B code/validation/check_integrity.py
```

On Linux/macOS, use `python3.11 -m venv .venv` followed by `.venv/bin/python -m pip install -r requirements.txt`; use `.venv/bin/python` in place of the Windows interpreter in the commands below. Those operating systems were not tested. Optimizer/build differences must be reported, not silently accepted as exact agreement.

## File Structure

| Location | Purpose |
|---|---|
| `code/reproduce.py` | Supported entry point; creates fresh workspaces, invokes original routines and records logs |
| `code/data/` | Verify/import lawful input files; preserved historical downloader for provenance |
| `code/core/quickcheck_d1/` | Return loading, ten-model pool construction, FZ0 scoring and batch calibration |
| `code/core/devcheck_d1v2/`, `devcheck_round2/`, `devcheck_round3/` | Reused controller, DJC expert and aggregation functions; original filenames retained to preserve imports |
| `code/core/pilot5/pilot.py` | Python MCS/bootstrap implementation imported by the final estimator |
| `code/core/confirm/` | Frozen Study 1 driver, backtests/inference and parameter file |
| `code/pipeline/study2.py` | Historical-yen loader, original forecasting wrapper, saved-array inference |
| `code/validation/` | Independent arithmetic checks, exhaustive numeric comparisons and future-perturbation checks |
| `code/reporting/` | Original result-table generator and final-paper table/figure builders with portable paths |
| `data/` | Redistributable FRED input, input hashes, inventory and access instructions |
| `outputs/reference/` | Immutable archived numerical results and presentation values |
| `outputs/reproduced/` | Outputs from this package's executed replay and regenerated tables/figures |
| `outputs/verification/` | Comparisons, run records, timing checks and stated limitations |
| `provenance/` | Summary of the prespecified design, frozen settings, paper-value map, code hashes and documented packaging changes |

The numerical core retains its original directory names because those modules import each other. Historical `main()` functions in development modules are not supported entry points for this package; the functions they supply to the final estimator are preserved unchanged. `freeze_params.json` is an input, not an instruction to tune on evaluation data.

## Reproduction Instructions

### 1. Create a fresh output workspace

Delivered outputs are retained as evidence. Each new replay uses an empty workspace and refuses to overwrite an existing run:

```powershell
.\.venv\Scripts\python.exe -I -B -X utf8 code/reproduce.py prepare --destination runs/review1
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py inputs
```

The second command checks the bundled FRED hash and reports `EXTERNAL_INPUT_REQUIRED` for Study 1 until authorized originals are supplied. A full Study 1 rerun requires these input files.

### 2. Refit the historical-yen models and reproduce inference

```powershell
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py study2
```

This reads the supplied FRED CSV, rebuilds the model pool, re-estimates all comparison methods at the 97.5% and 99% levels, saves forecasts/backtests, repeats the 9,999-draw bootstrap and descriptive analyses, and checks scores, violation rates, Z2, time alignment and HAC estimates. Allow several minutes, with longer runtimes under CPU contention. The original seed is **20261024**. Study 2 uses that seed directly; Study 1 uses `seed + series_index` in the original input order. No seeds or inference settings are selected from new results.

### 3. Reproduce Study 1 with authorized original inputs

Prepare a directory containing `french/30_Industry_Portfolios_daily_CSV.zip` and the six `yahoo/yahoo_SYMBOL.json` files, as specified in `data/ACCESS.md`. For example, if that directory is `authorized_inputs` next to the extracted package, import its seven verified files into the fresh workspace. The importer also writes the required acquisition manifest:

```powershell
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/data/manage_inputs.py import-study1 ../authorized_inputs
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py study1
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py audit-study1
```

The import checks every historical hash; the Study 1 entry point checks the required manifest and input hashes again before fitting. It preserves the original multiprocessing rule (up to CPU count minus two workers) and the complete model/backtest/bootstrap pipeline. It can take tens of minutes. Input verification rejects mismatched vintages. If exact inputs cannot be obtained, record Study 1 full replay as unavailable; do not substitute a newly downloaded dataset and describe it as exact reproduction.

### 4. Generate the final-paper tables and figures and compare results

```powershell
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py review
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py leakage
.\.venv\Scripts\python.exe -I -B -X utf8 runs/review1/code/reproduce.py compare
```

`review` can also run directly after step 1 for a lower-cost reconstruction from archived forecasts and summaries. If Study 2 has not been refitted, it explicitly copies its archived forecasts before recomputing inference. If Study 1 has not completed, its tables/figures use archived Study 1 results. These paths reconstruct retained analyses and are not a new model replay. Completed fresh Study 1 results are used for table generation when available. Consult the logs and comparison coverage before describing any stage as re-estimated.

The leakage command changes future returns only in temporary arrays and checks whether earlier predictions change. It does not alter empirical inputs or results. Each command logs its output under the new workspace's `outputs/verification/logs/`; an error or numerical mismatch returns a nonzero exit status. Use another new workspace name for a subsequent attempt. Do not overwrite `outputs/reference/`.

## Expected Outputs

There are **13 final-paper tables** (1-9 and C1-C4) in CSV with structured JSON specifications, and **five final-paper figures** (1-4 and C1) in PDF/PNG. The CSV files contain table body rows in the paper's order; the accompanying JSON files retain headers, captions and notes. Values retain the paper's rounding and method labels. The original builder may also emit TeX tables and intermediate plots; these are presentation intermediates and do not modify the manuscript.

The figure filenames correspond to the manuscript as follows (each stem has `.pdf`, `.png` and `.svg` versions):

| Paper figure | File stem | Content |
|---|---|---|
| 1 | `fig_tradeoff_en` | Industry score and violation rate |
| 2 | `fig_cumulative_industries_en` | Cumulative industry score differences |
| 3 | `fig_cumulative_yen_en` | Cumulative historical-yen score differences |
| 4 | `fig_miscalibration_gain_en` | Calibration of EW and the mean score difference of DJC across 36 series |
| C1 | `fig_decades_en` | Industry score differences by decade |

Full Study 1 replay produces 10 CSV files plus `confirm_meta.json`, including per-series backtests, daily panel scores, primary/secondary bootstrap tests, H4/H5 summaries, crises and risk-state diagnostics. Full Study 2 replay produces `forecasts.npz`, daily forecasts, metrics/refit records and six summary outputs. The comparison report checks every available numeric CSV column and every saved Study 2 array, and separately checks final-paper cells against the supplied PDF.

`code/core/confirm/freeze_params.json` records the default blocks: H1/H2/H3 = 3.26/2.80/2.88 at alpha .025 and 5.05/3.33/5.05 at alpha .01. Sensitivities use 20, 60 and 250. The model pool, 1,000-return initialization, 20-day GARCH refits, calibration warm-up, half-lives 125/250/500/1,000, aggregation rate 2, fixed-share rate 1/250, original projections and all comparison arms remain unchanged.

## Verification

Read `outputs/verification/Verification_Report.md` and `comparison_summary.json` for the completed execution and coverage. The report distinguishes original archived evidence, full replay, recomputed inference and display-only comparisons. Exact equality is recorded separately from the explicit absolute tolerance of `1e-12` (zero relative tolerance); the tolerance is never substituted for the paper's displayed precision.

The main archived results are H1 mean -0.00787722842361139 with Holm p .0861; H2/H3 Holm p .0006/.0478; industry EW+DJC violation rate about 2.1778%; and historical-yen mean -0.007068039844322028 with one-sided p .1973. H1 is not supported, whereas H2 and H3 are supported under the prespecified block lengths. The conclusion on H3 is sensitive to the block length. The yen test does not confirm a score improvement. These conclusions are unchanged by reproduction.

Timing checks condition on the frozen design. Study 2 is a backward-in-time validation of later-developed settings; Study 1 holds out series while development/evaluation economic histories overlap in calendar time. These designs do not establish prospective historical deployment.

Limits remain even after numerical agreement: original Study 1 per-series daily VaR/ES paths were not archived, so their pathwise equality cannot be checked; raw Study 1 data require authorized external access; later-vintage histories do not establish real-time data availability; appreciation-state and tertile thresholds are retrospective descriptions; and the order of events before each protocol freeze is documented only by the author's commit records summarized in `provenance/Prespecified_Design.md`. The package grants no rights to third-party data.

## License

The code and documentation in this package are released under the MIT License (see `LICENSE`). Third-party data remain subject to their providers' terms: the bundled FRED DEXJPUS series is marked by FRED as public domain with citation requested, and the French and Yahoo Finance inputs are not distributed.
