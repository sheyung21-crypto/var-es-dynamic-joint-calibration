# Verification Report

> Note (25 October 2026): after this verification, five module docstrings were edited (executable code unchanged, confirmed by syntax-tree comparison), the local path in two figure logs was replaced by `<package root>`, and the Study 2 protocol file was replaced by `provenance/Prespecified_Design.md`. The manuscript version of 25 October 2026 adds only the ORCID, code-availability and funding lines to the version identified below; its tables and numerical text are unchanged. See `provenance/Packaging_Changes.md`.

This report concerns reproducibility of the completed 26-page VaR/ES manuscript, identified by SHA-256 `86f29e6265870500ec6f4f653a1622fb0ba96dcc6512dffbba10b2f0104678d4`. The manuscript and original research files were not edited. Execution took place on 25 October 2026 using CPython 3.11.9 on 64-bit Windows. All model parameters, seeds and original estimator functions were retained.

## Execution and numerical agreement

The models in both studies were re-estimated from the original inputs using the fixed settings, including the 36-series Study 1 panel, the historical-yen models, calibration, backtests and 9,999-draw bootstrap inference. Study 1 completed in 1571.1 seconds; its ten numerical CSV outputs were compared with the archive. No parameters were changed. All checked values agree at the precision reported in the manuscript.

A new Python 3.11.9 virtual environment installed the 17 packages at the recorded versions and passed pip check. The package was copied outside the source repository and run with isolated Python imports. Study 2 was refitted and its inference, tables and figures were regenerated successfully. The full Study 1 pipeline also completed there in 1419.8 seconds after authorized inputs were imported and hash-verified. All commands in the isolated replay sequences returned exit status 0. The package therefore executed without imports from the original research checkout.

For the delivered replay files, the comparison covers **43 CSV files and 427 columns**: 415 columns are exactly equal after key-based row alignment, and all 427 satisfy absolute tolerance `1e-12` with zero relative tolerance. Both numeric and identifying text columns are checked. The maximum numeric discrepancy is **1.3322676295501878e-15**. The 12 nonexact columns concern panel aggregates or recomputed audit arithmetic; they are listed in `nonexact_columns.csv`. Per-series metrics, bootstrap means/intervals/p-values and paper display values agree exactly. Floating-point aggregate differences were not rounded away or used to replace the original reference files. Row-order differences from multiprocessing are aligned by saved identifiers; timing and Git metadata are not scientific equality criteria.

All **106 historical-yen arrays** agree exactly, including returns, dates, VaR/ES forecasts, scores and retained state/weight arrays. The original and regenerated NPZ files also have the same SHA-256. All **580 final-paper table cells**, covering 13 tables and 105 body rows, match the supplied PDF after whitespace and minus-sign normalization. The paper-to-output mapping contains 543 numeric tokens. All **49 additional numerical prose claims** agree at paper precision; the 72 decade-heatmap values are separately exported. Five final English figures were regenerated and visually inspected. Figure 4 now obtains the original coordinates directly from the selected per-series results, so it follows a completed replay when present.

## Checks requested by the research handoff

| Item | Evidence and result | Boundary |
|---|---|---|
| Data processing | All eight evaluation raw-file hashes matched acquisition receipts. The 37-series inventory records loader fields, counts and dates; 36 Study 1 split/date checks and the Study 2 9,043-return / 6,043-evaluation split passed. | French/Yahoo raw inputs remain external to the distribution. |
| VaR estimation and calibration | Both complete model pipelines were executed. Study 1 per-series outputs and saved panel score paths match; all Study 2 arrays are exactly equal. Original optimization failure counts are preserved and inspected. | Original Study 1 per-series daily q/e were not archived, preventing a direct original-versus-new comparison of those paths. |
| Backtest statistics | Per-series violation rates, Z2, unconditional-coverage and independence results, magnitude and stability statistics were compared across every available CSV column. Study 2 metrics were independently recalculated from arrays. | Reproducing a statistic does not validate all assumptions behind its test. |
| Model comparisons | Original 9,999-draw bootstrap, block settings, sensitivities and Holm families were rerun. All Study 1 test-table columns and Study 2 comparison outputs agree. | Secondary and retrospective analyses retain their original evidential status. |
| Tables and figures | Tables 1-9 and C1-C4; Figures 1-4 and C1 regenerated. Table cells and additional numerical claims match the final PDF. | PDF byte identity is not expected because rendering metadata may differ. |
| Information timing | Code inspection and 38 future-perturbation checks found no forecast change through the tested cutoffs. All checks passed exactly. | Finite tests do not prove every possible path or establish real-time provider vintages. |

## Main paper values

| Quantity | Original and replay value | Interpretation retained |
|---|---|---|
| Industry EW+DJC minus EW, 2.5% tail | Mean -0.00787722842361139; CI [-0.01968162833844695, 0.0018471487333845196]; Holm p .0861 | H1 is not supported. |
| Industry H2 / H3 | Holm p .0006 / .0478 | H2 and H3 are supported under the prespecified block lengths; H3 is sensitive to block length. Neither establishes an improvement over EW. |
| Industry EW+DJC violation rate | Approximately 2.1778% | Below the 2.25% lower tolerance bound; the prespecified risk calibration criterion is not met. |
| Historical-yen EW+DJC minus EW | Mean -0.007068039844322028; CI [-0.024251056119415783, 0.008931617155161671]; p .1973 | The score improvement is not statistically significant; no Holm adjustment was applied. |

The risk calibration criterion uses point estimates: the violation rate must lie between 2.25% and 2.75%, must not fall below the gross over-conservatism threshold of 2.0%, and the absolute Z2 must be smaller than for EW. EW+DJC also has a larger absolute Z2 than EW, although its violation rate remains above 2.0%. The historical code key `risk_cost_acceptable` is retained unchanged; it denotes this calibration criterion rather than a capital or profit-and-loss test.

`headline_comparison.csv` gives original and replay values separately, including all three industry primary tests. `numeric_comparison.csv`, `study2_array_comparison.csv`, `paper_cell_comparison.csv` and `paper_additional_claims.csv` provide the detailed checks. The small residuals in the independent HAC-library and summary-arithmetic checks are reported in their JSON records rather than suppressed.

## Timing assessment

Inspection covered trailing model-estimation windows, refit schedules, lagged model scores for MCS, batch-calibration samples, DJC expert updates and mixture weights, and Ye-type recursions. Forecast weights are saved before the current observation updates their state. The perturbation tests change current/future returns and compare forecasts through the cutoff; `leakage_checks.json` records all arrays and discrepancies.

The fixed algorithm and block settings were developed on later calendar periods, including 2010-onward yen and 2016-onward equity data. Study 2 is therefore the protocol's backward-in-time validation, not a prospective historical deployment. Study 1 separates series from development, but economic histories overlap in calendar time. The rolling forecast checks are conditional on the frozen design and do not certify chronological independence of method development.

The historical-yen appreciation state uses the current return in its sixty-day sum and a full-evaluation-sample threshold. Signal tertiles and related risk-state boundaries also use retrospective cutoffs. They are descriptive groups and do not enter the forecasting pipeline. They must not be interpreted as implementable ex-ante trading signals.

## Environment, provenance and portability

`requirements.txt` records 17 packages at the versions used for reproduction. A new virtual environment installed them and returned `No broken requirements found` from `pip check`. The relocated copy was outside the original repository; its supported commands used relative package paths and isolated Python imports. Authorized Study 1 files were imported only into private test workspaces and are excluded from the delivery. The importer validates all seven files before copying and supplies the original acquisition manifest. The Study 1 wrapper rejects an absent or different manifest before model fitting; this failure mode was tested.

Eight core files were byte-identical to their original counterparts at the time of this verification (see the note above). `provenance/code_changes.json` and `portability_changes.diff` identify relative-path and reporting changes. New wrappers verify inputs and outputs; they do not change model functions. The original Git/provenance fields remain historical records and are not runtime prerequisites. `study1_audit.json` and `study2_validation.json` describe independent audit routines, so their statements that they do not themselves refit models should be read alongside the separate successful refit records.

## Remaining unverified or unavailable items

1. Original Study 1 per-series daily VaR/ES paths are missing from the retained archive. Their exact pathwise identity cannot be established. The saved per-series metrics, daily panel scores and inference outputs were compared instead.
2. The distributed archive cannot perform a full Study 1 refit without lawful access to the exact French/Yahoo raw files. Their URLs, retrieval receipts, hashes and import instructions are included. A later download may have a different vintage; the verifier rejects such a substitution.
3. Point-in-time data availability, provider revisions, constituent-level survivorship cannot be established from these artifacts, and the order of events before each protocol freeze rests on commit records kept by the author. The retrospective state thresholds are not forecasting inputs.
4. Current development score files reproduce all six frozen block lengths, but their original freeze-date hashes were not recorded and those score files were absent from the handoff archive. This checks consistency, not historical byte identity. Development was not retuned.
5. Windows/Python 3.11.9 was tested; Linux/macOS, other package builds and cross-platform optimizer equivalence were not. Documentation includes portable commands without claiming those environments were validated.

The package supplies reproducibility evidence for academic review. It does not change the statistical findings.
