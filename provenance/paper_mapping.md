# Final-paper result mapping and bounded timing audit

## Scope

- Purpose: link every number in the final paper to the retained numerical results; the manuscript was not revised.
- Evidence: the final PDF, the manuscript sources, the frozen research code, archived raw inputs and result files.
- Method: read-only inspection of the source files; working files of the audit were kept outside the package.
- Status: display-to-archive consistency verified; additional descriptive arithmetic recomputed. The complete model replay is reported separately in the execution logs.
- Audit date: 25 October 2026.

## Manuscript build

The audit used the manuscript build `VaR_ES_Dynamic_Joint_Calibration.pdf` (26 pages, SHA-256 `86f29e6265870500ec6f4f653a1622fb0ba96dcc6512dffbba10b2f0104678d4`). The final manuscript differs from it only in its title page (ORCID and code-availability lines added, date line removed), the wording of the Introduction (Section 1), one added funding sentence in the declarations, two end-of-proof marks and layout; its other wording, tables and numbers are identical.

The earlier `publication_20261024` directory is the numerical research source. The final PDF was produced by `revised_manuscript_20261024` using presentation-stage copies of those results in `publication_zh_20261024`. These copies are not a new estimation run.

## Complete table mapping

All 105 displayed body rows of the 13 final-PDF tables match the English output of `revised_manuscript_20261024/scripts/tables.py`. The check requires each complete row, in its original column order, to occur within its own PDF table block; only whitespace, typesetting dollar markers, and typographic minus signs are normalized. The table contains 543 numeric tokens, including dates, sample sizes, and levels. This establishes consistency with the archived presentation values; it does not itself establish successful re-estimation.

`paper_expected_values.csv` contains every body cell, keyed by `table`, `row`, and `field` (`c1`, `c2`, ...). `displayed_text` preserves the final rendering text. `builder` gives the exact function key needed to call `tables.table(builder, 'en')`. `paper_table_rows.csv` retains whole-row checks. `paper_numeric_reference.csv` provides a token-level supplement.

| Final table | PDF page | Builder key | Archived presentation CSV | Numerical origin |
|---|---:|---|---|---|
| 1: Comparison methods | 10 | `arms` | Static definitions in `tables.py` | Definitions and method labels, not an empirical result |
| 2: Primary industry tests | 11 | `primary` | `study1_primary.csv` | `confirm/results/confirm_tests.csv`, industries, alpha .025, primary, default blocks |
| 3: Other industry comparisons | 13 | `secondary` | `study1_secondary.csv` | `confirm_tests.csv`, industries, alpha .025, secondary, default blocks |
| 4: Industry crisis scores | 14 | `crisis_us` | `study1_crisis.csv` | `confirm_crisis.csv`, industries, alpha .025; A0 and A2 |
| 5: Yen primary and block tests | 15 | `yen_tests` | `study2_tests.csv` | `results/study2_summary/tests.csv`, A2 versus A0 |
| 6: Yen comparator differences | 15 | `yen_comparators` | `study2_comparators.csv` | `study2_summary/tests.csv`, A2 versus other comparators |
| 7: Yen appreciation states | 16 | `yen_appreciation` | `study2_appreciation.csv` | `study2_summary/appreciation.csv` |
| 8: Yen lagged-signal groups | 17 | `yen_tertiles` | `study2_tertiles.csv` | `study2_summary/signal_tertiles.csv` |
| 9: Industry block sensitivity | 19 | `robustness` | `study1_robustness.csv` | `confirm_tests.csv`, primary, blocks 20, 60 and 250 |
| C1: Industry scores and risk metrics | 24 | `metrics_us` | `study1_metrics.csv` | Industry means of `confirm_series_metrics.csv`, main period |
| C2: Secondary level and indices | 24 | `secondary99` | `study1_secondary99.csv` | `confirm_tests.csv`, industries at alpha .01 and indices at both levels |
| C3: Yen scores and risk metrics | 25 | `metrics_yen` | `study2_allarms.csv` | `results/study2_run1/series_metrics.csv`, main period |
| C4: Yen crisis scores | 25 | `crisis_yen` | `study2_crisis.csv` | `results/study2_run1/crisis.csv`; A0 and A2 |

Here `confirm/results` means `publication_20261024/source_archive/research_run/confirm/results`; presentation CSVs are under `publication_20261024/paper/tables`. The final table builder reads identical copies under `publication_zh_20261024/source_en/paper/tables`.

The original publication builder also writes `study2_regression.csv`; its slope estimates appear as prose in final Section 5.2.4 rather than as a numbered table. The main 2,000-day-window sensitivity and the MCS/DJC interaction are also prose results, from `confirm_tests.csv` and `confirm_h4.csv` respectively. They must be retained even though they are not separate final tables.

## Complete figure mapping

| Final figure | PDF page | Function in revised `figures.py` | Input |
|---|---:|---|---|
| 1: Score versus violation rate | 11 | `tradeoff` | `study1_metrics.csv`; same rounded values as Table C1 |
| 2: Industry cumulative score differences | 14 | `cumulative_industries` | `confirm_daily_means.csv`; A2 minus A0; seven fixed 60-trading-day crisis windows |
| 3: Yen cumulative score differences | 16 | `cumulative_yen` | `study2_summary/descriptive_daily.csv`; A2 minus A0; ex post appreciation-state shading |
| 4: Calibration and gains across 36 series | 18 | `miscalibration` | `results/study1_exploratory_series.csv` derived from archived per-series metrics |
| C1: Decade heatmap | 26 | `decades` | `confirm_daily_means.csv`; industry alpha .025; method-minus-A0 means by displayed decade |

The revised plot filenames are `fig_tradeoff_en`, `fig_cumulative_industries_en`, `fig_cumulative_yen_en`, `fig_miscalibration_gain_en`, and `fig_decades_en`. The source builder produces PNG, PDF, and SVG versions. The final Word/PDF renderer downsampled the PNG images; pixel identity to a fresh Matplotlib rendering is therefore not a numerical reproducibility criterion.

The numerical inputs of all five figures are available. The package should use the revised figure builder, adapted only for paths, to reproduce the actual final-paper figures. Running only `publication_20261024/scripts/build_tables_figures.py` produces the earlier publication's figures and omits the final tradeoff plot and decade heatmap.

## Main numerical findings and prose claims

The final paper's central results match the archived numerical sources:

- Industry primary H1: mean A2 minus A0 `-0.00787722842361139`, interval `[-0.01968162833844695, 0.0018471487333845196]`, one-sided and Holm p `.0861`. Displayed as `-0.0079`, `[-0.0197, 0.0018]`.
- Industry H2 and H3: displayed means `-0.0208` and `-0.0080`; Holm p `.0006` and `.0478`. These are comparisons with other calibration methods and do not establish H1.
- Industry A2 violation rate is about `2.1778%`, below the prespecified `2.25%` lower tolerance bound but above the `2.0%` gross-conservatism bound. A0 and A2 Z2 are displayed approximately as `-0.090` and `0.121`. The risk criterion fails.
- GJR has the lowest industry average score, displayed `1.1179`. A2 minus GJR is displayed `0.0156`, interval `[0.0041, 0.0265]`.
- Yen primary A2 minus A0: `-0.007068039844322028`, interval `[-0.024251056119415783, 0.008931617155161671]`, one-sided p `.1973`, no Holm adjustment.
- Main evaluation periods are 3 July 1975–31 August 2026, 12,897 common industry dates; a union of 9,119 international-index dates from 25 June 1991–23 October 2026; and 24 December 1985–31 December 2009, 6,043 yen dates. These are stated sample descriptions; fresh raw-data processing checks should additionally confirm them.

`paper_additional_claims.csv` covers 49 numerical prose claims outside the ordinary table cells, with their source values and comparison at the paper's displayed precision: crisis and appreciation sums, cross-series correlations, decade means, yen signal-regression slope and interval, appreciation threshold, MCS/DJC interaction, and 2,000-day-window comparisons. All match the printed rounding. This supplements the complete table audit rather than substituting for fresh inference.

The descriptive recomputation gives the following values:

| Sample and level | Selected state sum | Other-day sum | Full sum |
|---|---:|---:|---:|
| Industries, 97.5% | -157.06271737285908 (420 crisis days) | 55.47010239354297 (12,477 days) | -101.59261497931611 |
| Industries, 99% | -295.899981803447 | 117.89526424634182 | -178.0047175571052 |
| Yen, 97.5% | -91.74776059211943 (605 appreciation days) | 49.03559581288115 (5,438 days) | -42.71216477923825 |
| Yen, 99% | -123.4898939663628 | 104.06129597004767 | -19.428597996315084 |

The 72 Figure C1 cells (12 methods by six periods) were recomputed from daily means and saved as `paper_figure_C1_recomputed.csv`. The nine decade values stated in prose agree at three decimals. Both daily and monthly batch calibration of EW have positive method-minus-EW decade means in every displayed period.

## Differences between the final paper and earlier publication output

No numerical input change was found: the twelve empirical table input CSVs and three plot-data CSVs read by the final builders are byte-identical to their original publication counterparts (`final_vs_publication_inputs.csv`). Final presentation changes include method labels (A0 → EW, A2 → EW+DJC, F → EW+DJC-FIX, R0 → GJR), four-decimal displayed differences, typographic minus signs, row ordering, and English plot styling. The revised presentation adds the tradeoff figure, crisis shading, cross-series scatter, decade heatmap, and descriptive sums described above. It does not estimate new forecasts or change the primary results.

The earlier publication's limitations remain relevant: original Study 1 per-series daily q/e arrays were not saved, although daily cross-sectional score means, per-series backtest metrics, bootstrap summaries, raw inputs, and core forecast code were saved. A fresh replay can regenerate results and forecast arrays, but the original missing q/e arrays cannot be retrospectively byte-verified. The package must distinguish an archived-summary comparison from comparison against an original per-series forecast path.

## Bounded information-timing audit

This is a code-path inspection, not a formal proof of every execution path or a complete independent reimplementation.

| Component | Evidence | Finding |
|---|---|---|
| Return transformation | `confirm_run.py:55–91`; `study2.py` loader | Industry returns use `100*log1p(r/100)` after missing-code removal. Prices become `100*log(P[t]/P[t-1])` after missing/invalid observation removal. Yahoo retains the last duplicate date; no future fill is used. |
| Base GARCH/GJR estimation | `quickcheck_d1.py:73–140` | Fits at return index i use `y[i-1000:i]`, excluding current return. Historical simulation uses `y[i-w:i]`. EWMA starts from the first 1,000 squared returns and updates after producing the current prediction. GJR residual and variance updates using `y[i]` occur after all current forecasts are stored. |
| MCS selection | `confirm_run.py:113–128` | Although the full score matrix is precomputed, model selection at t reads only `L[t-window:t]`. The full matrix's existence alone is not future-data use. |
| Batch calibration | `quickcheck_d1.py:172–182` | Coefficient estimation reads `y[lo:t]`, `q[lo:t]`, `e[lo:t]`, excluding t. |
| DJC experts | `devcheck_round2.py:28–43` | Forecasts use u[t], v[t]; current-return breach and tail-size updates write u[t+1], v[t+1]. |
| Learned expert weights | `devcheck_round3.py:29–38` | `W[t] = w` is stored before the update from current score S[t]; current forecasts use stored W[t]. Full score precomputation is not accessed early. |
| Ye-type controllers | `devcheck_d1v2.py:63–72` | Current forecast uses lambda[t]; the current return updates lambda[t+1]. |
| Main split | `confirm_run.py:31–35,179–239` | First 1,000 returns initialize base models; next 1,000 provide score history; calibration starts at return 2,001; evaluation begins at return 3,001. Robustness evaluation begins at return 5,001. |
| Lagged yen signal | `study2.py` summarize | `shift(1).rolling(250)` uses the preceding 250 returns only. `verify_study2.py` independently reconstructs that window by direct array slicing. |
| Appreciation state | `study2.py` summarize | Sixty-day cumulative return includes current return; threshold is the full-evaluation-sample 10th percentile. This contains future/full-sample information relative to earlier forecast dates and is correctly limited to retrospective description. It does not feed forecasting. |
| Signal tertiles and regression | `study2.py` summarize | The signal is lagged, but grouping thresholds and regression estimates use the full evaluation sample. These are descriptive analyses, not a deployable trading/forecasting rule. |
| Other risk-state groups | `confirm_run.py:251–258` | VaR tercile boundaries use the full evaluation sample; saved states are ex post diagnostics, not predictors. |
| Development versus evaluation | Manuscript §4.1; frozen protocol and code | The yen historical sample ends in 2009, while yen development data start in 2010. Industry portfolios were not in the development set, but economic histories overlap with development equity data; international indices are explicitly secondary. Exact chronological provenance is a separate source/version audit. |

No direct current- or future-return access was identified in the inspected forecasting and calibration update paths. This conclusion is bounded by the inspected code and saved provenance. It does not establish absence of undocumented prior researcher exposure or real-time vintage/revision bias. The archive uses later-vintage historical data, not a point-in-time database.

One implementation clarification is relevant to reproduction: the manuscript's general statement about 1,000-day estimation and 20-day refitting should not be implemented as a new common rule for every base method. The actual code uses 125/250/500-day historical windows, recursively updated EWMAs initialized on 1,000 returns, and 1,000-day GARCH/GJR fits every 20 days. Reproduction must preserve the code as used.

## Statistical interpretation checks

This is a bounded reproducibility assessment, not an editorial review. None of the following observations implies a change to the completed manuscript, its empirical values or its conclusions.

| Category | Assessment from the inspected evidence |
|---|---|
| 1. Simpson's paradox | No sign reversal in the quoted cross-series relationship: pooled and within-industry/index correlations have the same direction. Daily panel weighting still differs from equal weighting of per-series full-sample means for nonaligned indices; the code's specified weighting must be retained. |
| 2. Ecological fallacy | Cross-series relationships are explicitly exploratory associations of summary statistics. They do not establish a day-level forecasting rule; the separate lagged-signal test does not support such a rule. |
| 3. Berkson's paradox | No causal interpretation is supported for state-conditioned gains. Appreciation states select extreme realized returns; within-state associations are descriptive and could reflect selection. |
| 4. Collider bias | No controlled causal model was identified. Ex post return/state conditioning can create associations and is not treated as causal evidence. |
| 5. Base-rate neglect | Tail levels .025 and .01, empirical breach rates, observation counts, and tolerances are explicit. Rare-event uncertainty remains; the risk criterion uses point estimates, not inferential coverage equivalence. |
| 6. Regression to the mean | Extreme appreciation/crisis episodes are followed by ordinary periods; the narrative is descriptive. A gain in selected extreme periods is not evidence that an operational intervention would cause a persistent gain. |
| 7. Survivorship bias | Inputs are published industry portfolios and contemporary historical index files. Constituent-level selection and point-in-time data-vintage effects cannot be independently audited from these aggregate series; no survivorship-free claim is established. |
| 8. Look-elsewhere effect | H1–H3 have Holm correction; secondary contrasts and state analyses are labeled secondary/descriptive. Many comparisons are preserved, including negative results. H3 is borderline and sensitivity-adjusted values exceed .05 for the longer block lengths. |
| 9. Garden of forking paths | Development settings, frozen parameters, robustness analyses and the historical-yen protocol are retained. The study has a version-recorded freeze, not an independently public preregistration; prior exposure beyond the retained record is not verifiable here. |
| 10. Correlation versus causation | Forecast score comparisons describe performance of fixed algorithms on observed histories; the cross-series analysis does not identify a structural causal effect. No causal model is needed to reproduce the numerical comparisons. |
| 11. Reverse causality | Cross-series correlations are contemporaneous summaries. The yen signal precedes its forecast day, but full-sample regression estimates remain descriptive and do not establish a predictive causal mechanism. |

Primary findings must be interpreted using the specified one-sided tests and Holm family. Unadjusted two-sided 95% intervals need not give the same decision as Holm-adjusted one-sided p-values; treating them as interchangeable would be incorrect.

## Limits of this audit

This work did not refit models, redraw bootstrap samples, certify raw-data redistribution rights, verify all source-provider vintages, or establish unseen researcher chronology. It verified the link from the final paper to the retained numerical results and recomputed the additional descriptive sums/decade means. Full re-execution, numerical tolerance, independent-package behavior, and any mismatch must be documented by the package's execution and comparison report. The missing original Study 1 daily q/e files and the ex post state classifications should remain explicit limitations regardless of successful replay.
