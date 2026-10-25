# Data access and frozen input identity

The package includes the historical DEXJPUS input for Study 2. Study 1 requires seven external files: one French Data Library ZIP and six Yahoo Finance JSON responses. Redistribution permission for the Study 1 files was not established. The expected SHA-256 hashes, original request URLs, byte counts and retrieval timestamps are preserved in `study1/expected_fetch_manifest.json`.

Run all commands below from the package root. Replace `../authorized_study1` with the location of files that you are entitled to use.

## Verify available inputs

```text
python code/data/manage_inputs.py verify
python code/data/manage_inputs.py verify --study1 ../authorized_study1
```

The first command verifies bundled FRED data and reports `EXTERNAL_INPUT_REQUIRED` for Study 1. It does not certify a complete Study 1 reproduction. The second command also verifies all seven external Study 1 files; any absent file, byte-count discrepancy or hash discrepancy produces exit status 2. Exit status 0 with `ALL_INPUTS_VERIFIED` confirms matching input bytes, not model-result reproduction.

The external directory must have this structure:

```text
authorized_study1/
  french/30_Industry_Portfolios_daily_CSV.zip
  yahoo/yahoo_TWII.json
  yahoo/yahoo_KS11.json
  yahoo/yahoo_FTSE.json
  yahoo/yahoo_GDAXI.json
  yahoo/yahoo_AXJO.json
  yahoo/yahoo_GSPTSE.json
```

To import verified inputs for personal, authorized use:

```text
python code/data/manage_inputs.py import-study1 ../authorized_study1
python code/data/manage_inputs.py verify --study1 data/study1/raw
```

Import validates every input before copying any file. It writes matching files to `data/study1/raw/`, retains already matching files, and refuses conflicting destinations. It also copies the packaged original manifest as `data/study1/raw/fetch_manifest.json`. The original estimator also requires this manifest. The supported Study 1 entry point rejects an absent or different manifest before fitting. A direct external `--study1-data` directory must include a JSON-equivalent copy of the packaged expected manifest. Importing does not confer redistribution permission. Keep privately imported inputs out of any redistribution unless the relevant rights have been established.

## French Data Library

Use the [official library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) and its [30-industry construction page](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_30_ind_port.html). The exact download used in the study is [30_Industry_Portfolios_daily_CSV.zip](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/30_Industry_Portfolios_daily_CSV.zip).

The frozen file was retrieved on 23 October 2026 at 22:23:33 UTC and identifies the 202608 CRSP database in its internal header. The provider may replace this URL with later vintages. Download it through the provider's interface, place it under `french/`, and run the verifier. A differing hash must not be silently accepted for an exact reproduction. An authorized copy of the archived vintage may be necessary. The official page carries a Fama/French copyright notice; this package does not assert a general redistribution licence.

## Yahoo Finance

The actual observations were downloaded from the Yahoo Finance chart endpoint as JSON for `^TWII`, `^KS11`, `^FTSE`, `^GDAXI`, `^AXJO` and `^GSPTSE` on 23 October 2026. Exact request strings are recorded in the expected manifest. These records document past acquisition; they do not establish present access permission or endpoint availability.

Follow Yahoo's [official historical-download instructions](https://help.yahoo.com/kb/sln2311.html) and applicable [terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html). The official workflow is to find each symbol, open Historical Data, select dates and daily frequency, then download where licensed. Yahoo states that CSV downloads require a Gold subscription and that some instruments are unavailable for licensing reasons. The terms restrict automated collection without prior permission.

A currently downloaded CSV is not a drop-in replacement for the archived JSON. It may differ in values, date handling and vintage, and the frozen loader reads JSON `timestamp`, `meta.gmtoffset` and `indicators.quote[0].close`. For exact reproduction, obtain authorized access to the six historical JSON files identified by the expected hashes and place them under `yahoo/`. No supported reproduction command downloads Yahoo data. `code/data/fetch_original.py` is retained solely as evidence of original acquisition; it is not the recommended acquisition command. A fresh download cannot guarantee recovery of the frozen vintage.

## FRED / Federal Reserve H.10

The bundled `study2/DEXJPUS_1974_2009.csv` was retrieved on 24 October 2026 from [FRED DEXJPUS](https://fred.stlouisfed.org/series/DEXJPUS), supplied by the Board of Governors of the Federal Reserve System. The quotation is Japanese yen per US dollar, daily and not seasonally adjusted. The series carries the tag “Public Domain: Citation Requested”; the [Board's distribution policy](https://www.federalreserve.gov/disclaimer.htm) permits copying Board information unless otherwise indicated, with attribution requested.

To request the original date range into a separate, new directory:

```text
python code/data/manage_inputs.py fetch-fred ../fresh_fred_check
```

This optional network command requests the exact archived URL, writes a download receipt, and compares new bytes with the frozen hash. It does not replace the packaged input. Exit status 2 with `DIFFERENT_VINTAGE` means the response differs; a fresh download is not sufficient evidence of exact recovery. Use the bundled verified vintage for reproducing the completed paper.

## Sample and transformation conventions

`sample_inventory.csv` records one row for each of the thirty industries, six indices and the historical yen series. Counts and dates were independently recalculated from the original inputs during the packaging audit. Industry returns use `100 * log(1 + r/100)`. Indices and yen use `100 * log(P_t/P_(t-1))` after the original missing-value rules. There is no imputation or winsorization. Complete transformations and source attribution appear in `../Data_Sources.pdf`.

All histories are retrospective provider vintages. Exact input verification does not establish point-in-time data availability, revision-free histories or independent model validation.
