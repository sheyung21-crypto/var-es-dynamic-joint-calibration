"""Verify frozen inputs and import lawfully obtained Study 1 files.

This utility uses only the Python standard library. It never downloads Yahoo
data and does not change research parameters, observations, or original inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
STUDY1_MANIFEST = ROOT / "data" / "study1" / "expected_fetch_manifest.json"
STUDY2_MANIFEST = ROOT / "data" / "study2" / "fetch_manifest.json"
FRED_FILE = "DEXJPUS_1974_2009.csv"
FRED_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    "?id=DEXJPUS&cosd=1974-01-02&coed=2009-12-31"
)
STUDY1_PATHS = {
    "30_Industry_Portfolios_daily_CSV.zip": "french/30_Industry_Portfolios_daily_CSV.zip",
    **{f"yahoo_{name}.json": f"yahoo/yahoo_{name}.json"
       for name in ("TWII", "KS11", "FTSE", "GDAXI", "AXJO", "GSPTSE")},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_file(path: Path, relative_name: str, expected: dict) -> dict:
    report = {"file": relative_name, "expected_sha256": expected["sha256"],
              "expected_bytes": expected["bytes"]}
    if not path.is_file():
        return {**report, "status": "MISSING"}
    actual_bytes = path.stat().st_size
    actual_hash = sha256(path)
    matched = actual_bytes == expected["bytes"] and actual_hash == expected["sha256"]
    return {**report, "actual_bytes": actual_bytes, "actual_sha256": actual_hash,
            "status": "MATCH" if matched else "MISMATCH"}


def study1_specs() -> list[tuple[str, dict]]:
    rows = read_manifest(STUDY1_MANIFEST)
    if not isinstance(rows, list) or len(rows) != len(STUDY1_PATHS):
        raise ValueError("The expected Study 1 manifest must contain exactly seven inputs.")
    names = [row["file"] for row in rows]
    if len(set(names)) != len(names) or set(names) != set(STUDY1_PATHS):
        raise ValueError("The expected Study 1 manifest contains unexpected or duplicate inputs.")
    return [(STUDY1_PATHS[row["file"]], row) for row in rows]


def verify_study1(source: Path) -> list[dict]:
    return [check_file(source / name, name, expected)
            for name, expected in study1_specs()]


def verify(source: Path | None) -> int:
    fred = check_file(ROOT / "data" / "study2" / FRED_FILE,
                      "data/study2/" + FRED_FILE, read_manifest(STUDY2_MANIFEST))
    report = {"study2": fred}
    failed = fred["status"] != "MATCH"
    if source is None:
        report["study1"] = {
            "status": "EXTERNAL_INPUT_REQUIRED",
            "instruction": "Obtain authorized frozen inputs; pass their directory with --study1.",
        }
    else:
        checks = verify_study1(source)
        study1_ok = all(row["status"] == "MATCH" for row in checks)
        report["study1"] = {"status": "MATCH" if study1_ok else "FAILED", "files": checks}
        failed = failed or not study1_ok
    report["status"] = "FAILED" if failed else (
        "BUNDLED_INPUT_VERIFIED_STUDY1_EXTERNAL" if source is None else "ALL_INPUTS_VERIFIED")
    print(json.dumps(report, indent=2))
    return 2 if failed else 0


def import_study1(source: Path) -> int:
    checks = verify_study1(source)
    if any(row["status"] != "MATCH" for row in checks):
        print(json.dumps({"status": "REFUSED_INPUT_MISMATCH", "files": checks}, indent=2))
        return 2

    destination = ROOT / "data" / "study1" / "raw"
    if not destination.resolve().is_relative_to(ROOT):
        raise ValueError("The import destination resolves outside this package.")
    # All source checks and destination-conflict checks precede any copy.
    transfers = [(source / name, destination / name, expected["sha256"])
                 for name, expected in study1_specs()]
    transfers.append((STUDY1_MANIFEST, destination / "fetch_manifest.json", sha256(STUDY1_MANIFEST)))
    for _, target, expected_hash in transfers:
        if not target.resolve().is_relative_to(ROOT):
            raise ValueError("An import target resolves outside this package.")
        if target.exists() and (not target.is_file() or sha256(target) != expected_hash):
            raise FileExistsError(f"Conflicting destination; no files copied: {target.relative_to(ROOT)}")

    copied, retained = [], []
    for origin, target, expected_hash in transfers:
        relative_name = target.relative_to(ROOT).as_posix()
        if target.exists():
            retained.append(relative_name)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with origin.open("rb") as incoming, target.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        if sha256(target) != expected_hash:
            # Never leave a changed-in-transit source masquerading as a verified input.
            target.unlink()
            raise RuntimeError(f"Input changed during copying: {relative_name}")
        copied.append(relative_name)
    print(json.dumps({"status": "IMPORTED", "copied": copied, "already_matching": retained,
                      "manifest": "data/study1/raw/fetch_manifest.json",
                      "note": "Importing does not confer data redistribution rights."}, indent=2))
    return 0


def fetch_fred(destination: Path) -> int:
    expected = read_manifest(STUDY2_MANIFEST)
    if expected["url"] != FRED_URL:
        raise ValueError("Packaged FRED manifest does not contain the frozen request URL.")
    if destination.exists():
        raise FileExistsError("Choose a new, non-existing destination directory.")
    request = urllib.request.Request(
        FRED_URL, headers={"User-Agent": "VaR-Reproducibility-Package/1.0 (academic research)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read(10 * 1024 * 1024 + 1)
        content_type = response.headers.get("Content-Type")
    if len(body) > 10 * 1024 * 1024 or b"DEXJPUS" not in body[:150]:
        raise ValueError("Response is not the expected bounded FRED CSV document.")
    actual_hash = hashlib.sha256(body).hexdigest()
    matched = actual_hash == expected["sha256"] and len(body) == expected["bytes"]
    receipt = {"source": expected["source"], "series": "DEXJPUS", "url": FRED_URL,
               "downloaded_utc": datetime.now(timezone.utc).isoformat(),
               "file": FRED_FILE, "bytes": len(body), "sha256": actual_hash,
               "expected_sha256": expected["sha256"], "expected_bytes": expected["bytes"],
               "content_type": content_type, "matches_frozen_vintage": matched,
               "status": "MATCH" if matched else "DIFFERENT_VINTAGE",
               "note": "The packaged original was not replaced. A new download may contain revisions."}
    destination.mkdir(parents=True, exist_ok=False)
    (destination / FRED_FILE).write_bytes(body)
    (destination / "download_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if matched else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("verify", help="Verify bundled FRED data and optional external Study 1 inputs.")
    check.add_argument("--study1", type=Path, metavar="PATH", help="Directory containing french/ and yahoo/.")
    copy = commands.add_parser("import-study1", help="Import seven exactly matching, authorized Study 1 inputs.")
    copy.add_argument("path", type=Path, metavar="PATH")
    fetch = commands.add_parser("fetch-fred", help="Fetch into a new directory and compare with the frozen FRED hash.")
    fetch.add_argument("destination", type=Path, metavar="DEST")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return verify(args.study1)
        if args.command == "import-study1":
            return import_study1(args.path)
        return fetch_fred(args.destination)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
