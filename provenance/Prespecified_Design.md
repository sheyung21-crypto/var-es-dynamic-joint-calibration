# Prespecified design of Studies 1 and 2

This summary was prepared on 25 October 2026 from the two frozen protocol files. It is not itself a frozen document; where it differs from the originals, the originals govern. Both protocols were frozen in the author's version-controlled research repository and were not registered with a third party. The original files are retained by the author and are identified below by commit and SHA-256 digest.

| | Study 1 (US industries, international indices) | Study 2 (historical yen) |
|---|---|---|
| Frozen protocol file | `protocol_frozen_rev142.md` (Traditional Chinese, revision 142) | `STUDY2_PROTOCOL.md` (English) |
| SHA-256 of the frozen file | `b05afa755812a8b7211e47bbf30e85a23d46b965d299ad397a030569adfbe119` | `848876b417bd4153c83c1457aca2263df5f80e101de9c7855e63ec38f428b09a` |
| Freeze commit | `c429d8eb58c884060aeddc294a61e6fa2e398ce1` | `54a4ce2d1af16326cf0a14c93d555523b6135f11` |
| Commit time | 2026-10-24 06:40:58 +08:00 | 2026-10-24 08:59:16 +08:00 |
| Evaluation inputs obtained | 2026-10-23 22:23:33-22:23:40 UTC (06:23 +08:00 on 24 October), before the freeze commit. The protocol prohibits computing any forecast performance on the confirmation data before the freeze. | 2026-10-24 01:00:07 UTC (09:00 +08:00), after the commit. The data receipt `data/study2/fetch_manifest.json` records this commit and the protocol's SHA-256. |

Section references in code comments (for example "sections 3-6" or "section 7") refer to the original Study 1 protocol: §1 question and motivation, §2 hypotheses, §3 data and samples, §4 models and comparison design, §5 metrics and inference, §6 success criteria and interpretation, §7 execution order and freeze rules, with the development-round records and the freeze record.

## Study 1

**Primary hypotheses.** Three co-primary hypotheses, one-sided and Holm-adjusted at 5%, on the mean FZ0 score at the 97.5% level:

- H1: EW+DJC (code A2) has a lower mean score than EW (A0).
- H2: EW+DJC has a lower mean score than EW+BCd (A1d).
- H3: EW+DJC has a lower mean score than EW+YE (A3).

Secondary: H4, the advantage of MCS selection before and after calibration; H5, the violation rate and Z2 of EW+DJC. The 99% level is a secondary replication and is always reported.

**Decision rules fixed in advance.**

- The primary hypotheses take the mean-outperformance form; the alternative form (non-inferiority plus crisis improvement) was rejected at the freeze.
- Risk-cost criterion: the violation rate of EW+DJC lies in 2.25%-2.75% and is not below 0.8 alpha, and its |Z2| is smaller than that of EW.
- If H1 fails, the failure is reported and nothing is re-tuned on the confirmation data. Non-significant H2 and H3 are reported as "cannot be distinguished"; no equivalence margin or TOST is used.
- All arms are reported, including failures and estimation errors. After the freeze, only an inconsistency between code and protocol, a data error or a code error may change the analysis, and every arm is then rerun; any other deviation is labelled exploratory.

**Data.**

- Confirmation sample: the 30 Kenneth R. French industry portfolios, value-weighted daily returns, 1 July 1963 to 31 August 2026 (file SHA-256 `04a7a74fcd7c12e90461718e5ba8490e99d18c3e9323182b6c7a7b320e6cd34a`, CRSP 202608 vintage).
- External replication: TWII, KOSPI, FTSE 100, DAX, S&P/ASX 200 and S&P/TSX from Yahoo Finance. The protocol records that none of these six indices had been used by any code or data during development.
- Development data (repeated use allowed): the series of the earlier rounds, namely nine other international indices, the S&P 500, NASDAQ and DJIA, and exchange rates.
- Split of each series, counted in returns: 1-1,000 estimate the base models; 1,001-2,000 build the score history for MCS; 2,001-3,000 warm up the calibrations; evaluation starts at return 3,001 (3 July 1975 for the industries).

**Frozen methods.** A ten-model pool (historical simulation with 125, 250 and 500 days; EWMA with decay 0.94 and 0.994 and normal or t5 innovations; GARCH(1,1)-t; GJR-GARCH(1,1)-t; GJR filtered historical simulation), estimated on 1,000 returns and refitted every 20 days. MCS selection with the range statistic at alpha = 0.25 and 1,000 block-bootstrap draws, updated every 20 days. Batch calibration refitted every 20 days (A1) and daily (A1d). DJC with H in {125, 250, 500, 1000}, kappa = 4, floor log 1, M = 3, eta = 2 and sigma = 1/250. The Ye-type step 0.01 was selected on development data from {0.01, 0.025, 0.05, 0.1}; step 0.05 is reported as A3f. The single GJR-GARCH-t model (R0) is a reference.

**Inference.** The daily cross-sectional mean FZ0 difference d_t is tested with H0: E[d_t] >= 0 against H1: E[d_t] < 0, using a centred stationary bootstrap stratified by calendar decade and weighted by days, with 9,999 replications. Expected block lengths were chosen on development data with the Politis-White method: 3.26, 2.80 and 2.88 days for H1-H3 at 97.5%, and 5.05, 3.33 and 5.05 days at 99%. Sensitivity analyses use 20, 60 and 250 days, with a Newey-West Diebold-Mariano cross-check.

**Precision planning** (development data only). At the 97.5% level the minimum detectable mean effect was about 0.008-0.013 at 80% power and the Holm level, depending on the correlation between industries. Because the development-period mean effect on equities was -0.0005, the estimated power of the mean-outperformance test was about 2-3%.

**Prespecified secondary diagnostics.** Kupiec unconditional-coverage and Christoffersen independence tests; Acerbi-Szekely Z2; checks by market state; the share of 250-day windows in the Basel yellow and red zones at 99% (diagnostic only); average VaR and ES magnitude; stability of forecasts and multipliers; seven crisis windows of 60 trading days starting 1987-10-19, 1998-08-17, 2001-09-17, 2008-09-15, 2011-08-08, 2015-08-24 and 2020-02-24; results by decade and for 1975-2012 versus 2013 onward; and the 2,000-day window on a common evaluation period.

## Study 2

**Purpose.** A single-series, backward-in-time validation: does the frozen EW+DJC have a lower mean FZ0 score than EW at the 97.5% level in an earlier yen period? The study was motivated by a development finding on post-2010 yen data and does not establish general effectiveness.

- Data: FRED DEXJPUS, 2 January 1974 to 31 December 2009, downloaded only after the protocol commit; no data from 2010 onward are used. Missing levels are removed, returns are 100 log(P_t/P_{t-1}), and the split follows Study 1.
- Methods: the archived Study 1 code (`confirm_run.py`, SHA-256 `aaf98e688c2c21659149260f2bc100bd9620a00011cd201982ceca3adc477b3c`) without changes, with all 13 arms.
- Primary test: one-sided, decade-stratified stationary bootstrap with 9,999 replications and an expected block length of 3.26 days; the decision rule is p < 0.05; no Holm adjustment; seed 20261024.
- Interpretation fixed in advance: if p >= 0.05, state that the development-period yen improvement was not confirmed. In either case, limit the claim to the yen and the realized dates, and acknowledge that the market was selected during development.
- Secondary descriptions: the 99% level (block length 5.05); contrasts of EW+DJC with EW+BCd, EW+YE, GJR and EW+DJC-FIX; violation rates and Z2 for every arm; the inherited crisis windows; block lengths of 20, 60 and 250 days; a retrospective sharp-appreciation state (60-day cumulative return at or below the evaluation-period 10th percentile) with Newey-West intervals at lag 250; and a lagged violation signal over the previous 250 days, grouped by terciles, with an OLS slope and a Newey-West lag-250 interval (a negative slope was anticipated).
