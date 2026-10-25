"""Verify the delivered file manifest without third-party packages."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
manifest=ROOT/'MANIFEST_SHA256.csv'
failures=[];checked=0
with manifest.open(encoding='utf-8',newline='') as stream:
    for r in csv.DictReader(stream):
        p=(ROOT/r['path']).resolve()
        if not p.is_relative_to(ROOT.resolve()): raise ValueError('Manifest path escapes package')
        ok=p.is_file() and p.stat().st_size==int(r['bytes']) and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
        checked+=1
        if not ok:failures.append(r['path'])
result={'files_checked':checked,'failures':failures,'status':'MATCH' if not failures else 'MISMATCH',
 'note':'The manifest excludes itself; new files in later reproduction workspaces are not delivery files.'}
print(json.dumps(result,indent=2))
if failures:raise SystemExit(1)
