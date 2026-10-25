# Frozen computational settings

This execution map describes the retained code. It does not redefine the research protocol or select new parameters. Both frozen protocols are retained by the author; `Prespecified_Design.md` summarizes them and lists their freeze commits and SHA-256 digests. This English note supplies the settings required by an external reproducer.

| Stage | Retained implementation and settings |
|---|---|
| Data processing | `confirm_run.load_industries/load_index`; `study2.load_yen`; transformations and actual fields are listed in Data_Sources.pdf |
| Model estimation and VaR/ES forecasts | `quickcheck_d1.rebuild_pool`; 13-column storage with selected columns `[8,9,10,3,4,5,6,7,11,12]` for the ten-model pool |
| Base models | Empirical historical simulation with 125/250/500 returns; normal and t(5) EWMAs at rates .06/.006; GARCH-t; GJR-GARCH-t; GJR filtered historical simulation |
| Parametric estimation | Zero mean; 1,000 preceding returns; refit every 20 days; Student-t innovations; `rescale=False`; GJR maximum iterations 300; original failure/fallback behavior retained |
| Evaluation split | First 1,000 returns initialize base models; another 1,000 accumulate scores; calibration starts at return 2,001; common evaluation begins at return 3,001. The 2,000-day-window sensitivity is evaluated from return 5,001 |
| MCS | `confirm_run.mcs_combination` with `pilot.bstar/block_indices/means_from_indices/select`; selection every 20 days from preceding 1,000 days, level .25, 1,000 bootstrap draws, original automatic circular block-length procedure |
| Batch calibration | `quickcheck_d1.run_s1`; coefficient estimation excludes the current day; daily and 20-day refits; coefficients clipped to [.2,5]; initial availability after 250 calibration observations; main window 1,000 |
| DJC experts | `devcheck_round2.run_d1z1`; half-lives 125/250/500/1,000; log multiplier floor 0; exceedance-size cap 3; `gamma_e=log(2)/(alpha*H)`, `gamma_q=gamma_e/4`; ES constrained to be no greater than VaR (e <= q) |
| DJC aggregation | `devcheck_round3.run_aggregate`; rate 2, fixed-share rate 1/250, initial weights 1/4; the day-t weights are stored before the day-t loss update |
| Ye comparison | `devcheck_d1v2.run_ye`; steps .01 and .05; original radius/cap/gap-floor settings preserved |
| Tail levels | Lower-tail probabilities .025 and .01, corresponding to 97.5% and 99% levels |
| Backtesting | `confirm_run.metrics/kupiec/christoffersen`; FZ0, breach rate, Z2, unconditional coverage, independence, forecast magnitude/stability and original Basel-count descriptions |
| Inference | Decade-stratified centered stationary bootstrap; 9,999 draws; chunk size 200; seed 20261024; H1-H3 one-sided tests with Holm within the original primary family; historical-yen primary has no Holm adjustment |
| Bootstrap block inputs | Frozen H1/H2/H3 blocks .025: 3.26/2.80/2.88; .01: 5.05/3.33/5.05; sensitivities 20/60/250. Read `code/core/confirm/freeze_params.json`; do not rerun parameter selection on confirmation data |
| Study 1 per-series RNG | Seed 20261024 + zero-based input index: the 30 French columns in their input order, then TWII, KS11, FTSE, GDAXI, AXJO, GSPTSE |
| Study 2 RNG | Seed 20261024 for model/MCS processing; summary RNG reinitialized to 20261024; original test order retained |
| HAC descriptions | Bartlett/Newey-West covariance, lag 250, no finite-sample correction, normal critical value 1.96 |
| Results presentation | Original `build_tables_figures.py` and final `tables.py/figures.py` numerical logic retained; path changes and English-only plotting are recorded |

Unused historical tuning-grid constants remain in the original modules because their function definitions are preserved. The final drivers pass the fixed settings above; the presence of a development grid is not evidence that the package searches over it.

The historical protocol commit and data receipts are provenance records. No fresh Git repository, remote account or network connection is required by the supported reproduction commands once necessary inputs are present.
