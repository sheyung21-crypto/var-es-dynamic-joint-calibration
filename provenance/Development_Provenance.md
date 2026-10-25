# Development-data provenance for the frozen parameters

Prepared 25 October 2026. This memo supplements the Study 1/Study 2 source inventory. It documents the five directly identified development datasets that informed the frozen procedure; they are not additional confirmation observations and are not included in the 37-series evaluation inventory. No model was retuned, no parameter file was rewritten, and no raw data were added to the distribution package.

## Role in the completed research

Section 4.1 of the final manuscript distinguishes development observations from confirmation evidence; the corresponding local source is `publication_20261024/paper/design.tex:3`. The five datasets in the final D1 development rounds are explicitly enumerated in `publication_20261024/source_archive/research_run/devcheck_d1v2/devcheck_d1v2.py:23–27` and in the round 1–3 manifests. They are SP500, DJIA, NASDAQCOM, DEXUSEU and DEXJPUS, all obtained through FRED.

The equity and foreign-exchange series informed calibration design and development comparisons. The final block-length calculation is narrower: `confirm/freeze_params.py:16,40–56` uses only SP500, DJIA and NASDAQCOM daily FZ0 score differences from rounds 2 and 3, averaged across their common dates. It does not read the confirmation data or historical pre-2010 yen data. References to `confirm/` and `devcheck*/` in this paragraph are relative to `publication_20261024/source_archive/research_run/`.

The manuscript also acknowledges earlier inspection of international equity indices. This bounded memo does not identify an additional frozen-parameter input from those earlier pilots and does not relabel them as confirmation observations. The five datasets below are the ones directly bound to the recorded final development manifests and frozen parameter calculation.

## Sources, observed samples and processing

| Series | Originating provider; distribution | Daily input actually available | Raw rows / missing removed | Valid levels / returns | Development scoring period in round 2 and round 3 |
|---|---|---|---:|---:|---|
| SP500 | S&P Dow Jones Indices LLC; FRED | 2016-10-24–2026-10-21 | 2,608 / 96 | 2,512 / 2,511 | 2021-10-13–2026-10-21; 1,261 dates |
| DJIA | S&P Dow Jones Indices LLC; FRED | 2016-10-24–2026-10-21 | 2,608 / 96 | 2,512 / 2,511 | 2021-10-13–2026-10-21; 1,261 dates |
| NASDAQCOM | Nasdaq, Inc.; FRED | 2016-01-04–2026-10-21 | 2,817 / 100 | 2,717 / 2,716 | 2020-12-18–2026-10-21; 1,466 dates |
| DEXUSEU | Federal Reserve Board, H.10; FRED | 2010-01-04–2026-10-16 | 4,380 / 180 | 4,200 / 4,199 | 2014-12-30–2026-10-16; 2,949 dates |
| DEXJPUS | Federal Reserve Board, H.10; FRED | 2010-01-04–2026-10-16 | 4,380 / 180 | 4,200 / 4,199 | 2014-12-30–2026-10-16; 2,949 dates |

These counts and dates were independently recalculated from the actual raw CSV files, and scoring periods were read from the existing round 2/3 daily score files. The requested equity interval was 2016-01-01–2026-10-22; the shorter SP500 and DJIA histories are the observations actually returned, not a different requested start. The official [SP500 notes](https://fred.stlouisfed.org/series/SP500) explain FRED's ten-year daily-history agreement for the S&P and Dow Jones series. The NASDAQ sample extends to January 2016. No missing history was reconstructed.

The equity fields are index levels at daily close, not seasonally adjusted. SP500 is a price index excluding dividends, according to its official notes. [DJIA](https://fred.stlouisfed.org/series/DJIA) is likewise supplied as a daily closing index. [NASDAQCOM](https://fred.stlouisfed.org/series/NASDAQCOM) is supplied as a daily closing index with base 5 February 1971 = 100. The project reads these actual level fields and does not substitute an adjusted total-return series.

[DEXUSEU](https://fred.stlouisfed.org/series/DEXUSEU) is US dollars per one euro, and [DEXJPUS](https://fred.stlouisfed.org/series/DEXJPUS) is Japanese yen per one US dollar. Both are daily, not seasonally adjusted H.10 observations; their quotations are not inverted. Therefore negative returns indicate euro depreciation for DEXUSEU and yen appreciation for DEXJPUS.

The common loader converts the date and numeric fields, drops missing levels, restricts dates to no later than 2026-10-22, and calculates `100 * log(P_t/P_(t-1))` between consecutive retained levels (`quickcheck_d1/quickcheck_d1.py:65–70`). First-return dates are 2016-10-25 for SP500 and DJIA, 2016-01-05 for NASDAQCOM, and 2010-01-05 for both FX series. The final development rounds initialize their forecast pool with 1,000 returns and score after another 250 observations (`devcheck_round3/devcheck_round3.py:44–53`; `devcheck_d1v2/devcheck_d1v2.py:34`). These are development splits; they differ from the completed studies' 3,000-return initialization and warm-up.

## Acquisition records

The exact equity requests were recorded in `research_run/deepening5/external_download_manifest.json:3–24`:

- SP500: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2016-01-01&coed=2026-10-22`; retrieved 2026-10-22 at 17:57:23.270989 UTC.
- NASDAQCOM: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM&cosd=2016-01-01&coed=2026-10-22`; retrieved 2026-10-22 at 17:57:24.431999 UTC.
- DJIA: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DJIA&cosd=2016-01-01&coed=2026-10-22`; retrieved 2026-10-22 at 17:57:25.274232 UTC.

The FX records are in `research_run/stage3/gate_download_manifest.json:3–16`, with a preserved copy in `publication_20261024/prior_evidence/research_run/stage3/`:

- DEXUSEU: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU&cosd=2010-01-01&coed=2026-10-22`; retrieved 2026-10-22 at 18:42:08.577940 UTC.
- DEXJPUS: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS&cosd=2010-01-01&coed=2026-10-22`; retrieved 2026-10-22 at 18:42:09.789205 UTC.

This later yen history is a separate file from Study 2's 1974–2009 historical-yen input. The documented numerical samples do not overlap. Neither file establishes point-in-time vintage availability.

## Snapshot checks

All five original development raw files are present both in the current `research_run/` directory and in `publication_20261024/source_archive/research_run/`. For each file, both copies have the same byte count and SHA-256, and the hashes match the round 1, round 2 and round 3 input manifests and original download manifests. No raw-input snapshot discrepancy was found.

| Relative path under either research_run directory | Bytes | Verified SHA-256 |
|---|---:|---|
| `deepening5/external_data/SP500.csv` | 48,903 | `e9bcd388470935a8131bc8101271205f83ee953aecc527822e64365669b38cc2` |
| `deepening5/external_data/DJIA.csv` | 51,414 | `728b015265b88819948987f9a5fafecef499dffa968ede96c7f7b60867bc8c27` |
| `deepening5/external_data/NASDAQCOM.csv` | 57,157 | `584e5c60076083d065e5ba20579265df13fe713110b45a5dfbd857cd103b590f` |
| `stage3/fx_data/DEXUSEU.csv` | 77,785 | `06e0140a16ce28f15a4247047242ddefc870f385c53cd07544bd5946f5702cd5` |
| `stage3/fx_data/DEXJPUS.csv` | 76,841 | `78cf90ce3467e05de3509d9eec4e7a0f0f4156f0cfd2c391c495c25de4e60283` |

The authoritative handoff manifest lists these five raw files at `publication_20261024/source_archive/research_run/handoff/MANIFEST.tsv:39–43`. It also lists the frozen parameter JSON and selector at lines 15–16. The archived and current copies of all three development manifests, `freeze_params.py` and `freeze_params.json` are byte-identical. The quick-check and round 1–3 scripts in both locations match the code hashes recorded by the round 3 manifest (`devcheck_round3/devcheck3_manifest.json:31–34`).

The two daily score files are a narrower provenance limitation: they exist in the current workspace but are **absent** from the handoff `source_archive/`. The inspected development manifests bind raw inputs and scripts, but do not record hashes for these two daily score files. Their present identities are:

| Current workspace file | Bytes | SHA-256 observed 25 October 2026 |
|---|---:|---|
| `research_run/devcheck_round2/devcheck2_daily.csv` | 29,692,518 | `50c85aabf6062cacd7d072ad5c16626e82a7fdec6da39c93d71678ad5b71489f` |
| `research_run/devcheck_round3/devcheck3_daily.csv` | 20,447,949 | `1b1be81eaf20217a79f1a7a56308a458a51b05b3c7669e2a35661e4222e338fd` |

Using these existing score files and the archived selector function, a read-only recalculation reproduced all six stored rounded block lengths exactly: H1/H2/H3 = 3.26/2.80/2.88 at alpha .025 and 5.05/3.33/5.05 at alpha .01. All calculations use 1,261 common equity dates from 2021-10-13 to 2026-10-21. The round 2–round 3 A0 maximum absolute score difference is zero, matching the frozen record. No parameter JSON was written. This verifies the current score files' consistency with the frozen parameter values; it is not proof of their byte identity at the original freeze date and does not constitute a fresh rerun of development forecasts.

The frozen parameter JSON itself has SHA-256 `b8205813ce9cca8c1371f9c20d08439cd68d8e700d52b4d8e8acf3096b9cc5ef`, and its original selector has SHA-256 `7dd6ee380a064d684ecbe5804e6284e685f924f571d70e8b322ebd1c2cdf25dd`. The completed studies should continue to read the retained frozen JSON; no data-driven retuning is needed for their reproduction.

## Access and redistribution limitations

The official [SP500](https://fred.stlouisfed.org/series/SP500) and [DJIA](https://fred.stlouisfed.org/series/DJIA) notes require prior written permission to reproduce the series and identify S&P Dow Jones Indices LLC as the rights holder. [NASDAQCOM](https://fred.stlouisfed.org/series/NASDAQCOM) carries a Nasdaq copyright notice and the tag “Copyrighted: Pre-Approval Required.” These facts distinguish the equity series from Federal Reserve-origin data; FRED hosting is not a blanket redistribution licence. No permission document for these equity inputs was identified in the inspected project records.

The [DEXUSEU](https://fred.stlouisfed.org/series/DEXUSEU) and [DEXJPUS](https://fred.stlouisfed.org/series/DEXJPUS) pages identify the Federal Reserve Board as source and carry the tag “Public Domain: Citation Requested.” The [Board's policy](https://www.federalreserve.gov/disclaimer.htm) supports sharing Board information with attribution unless otherwise indicated. Development FX data are not required to execute the completed Study 1 and Study 2 workflows with retained frozen settings, so their omission from the minimum execution package does not prevent that fixed-parameter reproduction.

Provider policies and series notes were checked on 25 October 2026. A new download can differ through revisions and rolling history limits. This audit neither downloaded new development observations nor supplied copyrighted raw equity histories. A reviewer who wishes to rerun the development process needs authorized historical inputs and the full development score-generation workflow, beyond the minimum package for the completed paper's frozen evaluations.
