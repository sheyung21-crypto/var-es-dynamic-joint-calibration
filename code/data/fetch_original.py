"""Download the confirmation data of protocol section 3 and record their hashes.

Usage: python -I fetch_data.py <new empty data directory>
Ken French 30 industry portfolios (daily) and six Yahoo Finance index histories. The files are
only saved and hashed here; nothing in this script computes forecasts or performance.
"""
import hashlib, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FRENCH = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/30_Industry_Portfolios_daily_CSV.zip'
YAHOO = ('https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
         '?period1=0&period2={now}&interval=1d&includeAdjustedClose=true')
INDICES = {'TWII': '^TWII', 'KS11': '^KS11', 'FTSE': '^FTSE', 'GDAXI': '^GDAXI', 'AXJO': '^AXJO',
           'GSPTSE': '^GSPTSE'}
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def fetch(url, path):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
        body = r.read()
    path.write_bytes(body)
    return {'file': path.name, 'url': url, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            'downloaded_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}


def main():
    out = Path(sys.argv[1]); (out / 'french').mkdir(parents=True); (out / 'yahoo').mkdir()
    rows = [fetch(FRENCH, out / 'french' / '30_Industry_Portfolios_daily_CSV.zip')]
    now = int(time.time())
    for name, sym in INDICES.items():
        rows.append(fetch(YAHOO.format(sym=urllib.request.quote(sym), now=now), out / 'yahoo' / f'yahoo_{name}.json'))
        time.sleep(1)
    (out / 'fetch_manifest.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    for r in rows:
        print(r['file'], r['bytes'], r['sha256'][:16])


if __name__ == '__main__':
    sys.exit(main())
