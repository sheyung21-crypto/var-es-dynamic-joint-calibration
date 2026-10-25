# Packaging changes

The original project files were not edited. Eight retained core files (seven Python modules and the frozen parameter JSON) correspond to their original versions; in five of the modules only the module docstring was edited (see Documentation edits below), and their executable code is unchanged. All identities are recorded in `code_changes.json`.

The following changes are limited to packaging and observation of results:

1. Copied only the core modules imported by the final drivers, preserving their directory relationships. Omitted exploratory result bundles, development caches, duplicate manuscript builds, compiled Python files and unrelated pilots. Historical main functions within retained modules remain as source context; the supported entry point is `code/reproduce.py`.
2. Changed root/data/result paths in the historical-yen wrapper, summary auditor, saved-forecast validator and table/figure builders to be relative to this package. Model functions, data transformations, parameters, RNG sequence, optimizer settings and empirical values were not altered.
3. Directed output to `outputs/reproduced/` and immutable comparison inputs to `outputs/reference/`. Final table and figure generation uses a completed Study 1 replay when present and explicitly falls back to archived results in the review-only path. The final-paper plots read their source files directly, avoiding duplicate plot-data copies. Figure 4 applies the original subtraction formulas directly to the selected per-series metrics, so a completed replay also supplies those coordinates. The summary auditor selects completed replay files when present.
4. Retained the final paper's original table builders, method labels, numerical rounding and plotting functions. Limited plotting to English; no Chinese font file or Word/LaTeX toolchain is needed. The final-paper table specifications are exported as CSV and JSON without changing the manuscript.
5. Added input verification/import, fresh-workspace creation, run logging, exhaustive numeric comparisons, paper-value comparisons and future-perturbation checks. The Study 1 wrapper checks the original required acquisition manifest before starting estimation, avoiding a late failure from an absent receipt. These are wrappers and audit routines, not replacement forecasting models. New support scripts are identified in `added_support_code.json`.
6. Pinned all 17 observed numerical/plotting dependencies, including transitive packages, and recorded a clean-environment installation. No R dependency is introduced; the final research pipeline uses the retained Python MCS port.
7. Omitted French/Yahoo raw data and copyrighted development equity data from the distribution. Kept the public-domain historical DEXJPUS input, acquisition records, hashes and lawful-access instructions. This affects external input availability, not the model or local verification run.
8. Both frozen protocols are retained by the author and summarized in `Prespecified_Design.md`, which identifies each by its freeze commit and SHA-256; `Frozen_Settings.md` maps the settings used by the code. Original machine-readable result records retain their original status strings where needed for evidence.

`portability_changes.diff` records every textual difference for copied Python scripts. New orchestration/validation files have no original research counterpart and are separately hashed. The legacy `study2.py fetch` function and `fetch_original.py` preserve historical acquisition logic, including its original Git/vintage guards; use `code/data/manage_inputs.py` for the documented standalone input workflow. Replaying the frozen studies does not invoke those historical download paths.

Duplicate plot-data copies, legacy intermediate plots and generated TeX table files are omitted from the final delivery. Reference and replay results are deliberately retained separately because their comparison is the purpose of this package. PDF metadata may differ between renderings; numerical equality and displayed table values are the comparison criteria.

## Documentation edits

No model, data, setting or numerical result was changed by these edits.

1. Added `Prespecified_Design.md`, a summary of the frozen Study 1 and Study 2 protocols with their freeze commits, commit times and SHA-256 digests. The original protocol files are not distributed; the identity of the Study 2 protocol is also recorded in `data/study2/fetch_manifest.json`.
2. In the module docstrings of `confirm_run.py`, `devcheck_d1v2.py`, `devcheck_round2.py`, `devcheck_round3.py` and `quickcheck_d1.py`, replaced a private working link to the research protocol, which readers could not open, with a pointer to `Prespecified_Design.md`. A comparison of the parsed syntax trees with docstrings removed confirms that the executable code of all five modules is unchanged. Their new hashes are in `code_changes.json`.
3. Replaced the local absolute path in two figure-generation logs with `<package root>`.
4. Revised the README, `paper_mapping.md`, `Frozen_Settings.md`, the verification report (an added note and two reworded sentences) and both documentation PDFs to refer to the manuscript version of 25 October 2026. That version adds only the ORCID, code-availability and funding lines; its tables and numerical text are identical to the version of 24 October 2026 used in the verification.
5. Added an MIT `LICENSE` for the code and documentation; third-party data keep their providers' terms.
