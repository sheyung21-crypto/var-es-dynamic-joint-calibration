"""Frozen historical-yen evaluation; fetch -> forecast once -> summarize saved arrays.

All numerical forecast routines are imported unchanged from the verified archive.
The callbacks only retain arrays that confirm_run.run_series otherwise discards.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import urllib.request
import numpy as np
import pandas as pd
import scipy
import arch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'code' / 'core'
sys.path.insert(0, str(SOURCE / 'confirm'))
import confirm_run as frozen

URL = 'https://fred.stlouisfed.org/graph/?g=1&cosd=1974-01-02&coed=2009-12-31&id=DEXJPUS'
CSV_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS&cosd=1974-01-02&coed=2009-12-31'
DATA = ROOT / 'data' / 'study2' / 'DEXJPUS_1974_2009.csv'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def fetch():
    protocol = ROOT / 'provenance' / 'STUDY2_PROTOCOL.md'
    tracked = git('show', 'HEAD:publication_20261024/STUDY2_PROTOCOL.md')
    if tracked.replace('\r\n', '\n') != protocol.read_text(encoding='utf-8').strip():
        raise RuntimeError('Current protocol must match committed protocol before download')
    if DATA.exists():
        raise FileExistsError('Original download is immutable; use saved data')
    DATA.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(CSV_URL, headers={'User-Agent': 'Mozilla/5.0 (academic reproducibility study)'})
    with urllib.request.urlopen(req, timeout=90) as response:
        body = response.read()
        metadata = {'content_type': response.headers.get('Content-Type'), 'status': response.status}
    if b'DEXJPUS' not in body[:150]:
        raise RuntimeError('Not the expected FRED CSV response')
    DATA.write_bytes(body)
    receipt = {'source': 'Federal Reserve Board H.10 via FRED', 'series': 'DEXJPUS',
               'quotation': 'Japanese yen per U.S. dollar', 'url': CSV_URL,
               'requested_start': '1974-01-02', 'requested_end': '2009-12-31',
               'started_utc': start, 'downloaded_utc': datetime.now(timezone.utc).isoformat(),
               'bytes': len(body), 'sha256': sha(DATA), 'protocol_commit': git('rev-parse', 'HEAD'),
               'protocol_sha256': sha(protocol), **metadata}
    save_json(DATA.parent / 'fetch_manifest.json', receipt)
    print(json.dumps(receipt, indent=2), flush=True)

def load_yen():
    df = pd.read_csv(DATA)
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df['DEXJPUS'] = pd.to_numeric(df['DEXJPUS'], errors='coerce')
    df = df[df[date_col].between('1974-01-02', '2009-12-31')].copy()
    missing = int(df['DEXJPUS'].isna().sum())
    df = df.dropna(subset=['DEXJPUS'])
    assert df[date_col].is_monotonic_increasing and df[date_col].is_unique
    assert (df['DEXJPUS'] > 0).all()
    prices = df['DEXJPUS'].to_numpy(float)
    y = 100 * np.log(prices[1:] / prices[:-1])
    dates = df[date_col].iloc[1:].dt.strftime('%Y-%m-%d').to_numpy(dtype=str)
    notes = {'levels': len(df), 'missing_levels_removed': missing, 'returns': len(y),
             'first_level': str(df[date_col].iloc[0].date()), 'last_level': str(df[date_col].iloc[-1].date()),
             'first_return': dates[0], 'estimation_last': dates[999], 'mcs_accumulation_first': dates[1000],
             'calibration_first': dates[2000], 'evaluation_first': dates[3000], 'evaluation_last': dates[-1],
             'evaluation_days': len(y)-3000}
    return y, dates, notes

def forecast(out):
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    source_hashes = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob('*.py')}
    y, dates, notes = load_yen()
    receipt = json.loads((DATA.parent/'fetch_manifest.json').read_text(encoding='utf-8'))
    assert sha(DATA) == receipt['sha256']
    save_json(out/'execution_started.json', {'started_utc':datetime.now(timezone.utc).isoformat(),
              'data_sha256':sha(DATA), 'protocol_commit':receipt['protocol_commit'], 'source_hashes':source_hashes,
              'script_sha256':sha(__file__), 'seed':frozen.SEED, 'versions':{'python':platform.python_version(),
              'numpy':np.__version__, 'pandas':pd.__version__, 'scipy':scipy.__version__, 'arch':arch.__version__}})
    captured = {}
    original_calibrate = frozen.calibrate
    original_pool = frozen.v1.rebuild_pool

    def capture_calibrate(yy, q, e, alpha, window, prefix, extras):
        result = original_calibrate(yy, q, e, alpha, window, prefix, extras)
        captured[(alpha, prefix, window)] = result
        return result

    def capture_pool(*args, **kwargs):
        result = original_pool(*args, **kwargs)
        captured['pool'] = result
        print('Base-model forecasts completed', flush=True)
        return result

    frozen.calibrate = capture_calibrate
    frozen.v1.rebuild_pool = capture_pool
    try:
        result = frozen.run_series(('DEXJPUS', 'fx', dates, y, frozen.SEED))
    finally:
        frozen.calibrate = original_calibrate
        frozen.v1.rebuild_pool = original_pool
    metrics = pd.DataFrame(result['metrics'])
    assert metrics['legal'].all(), 'Frozen pipeline produced illegal forecasts'
    metrics.to_csv(out/'series_metrics.csv', index=False)
    for key in ('diag', 'crisis', 'states'):
        pd.DataFrame(result[key]).to_csv(out/(key+'.csv'), index=False)
    qr, er, refits = captured['pool']
    pd.DataFrame(refits).to_csv(out/'model_refits.csv', index=False)
    arrays = {'all_returns':y, 'all_dates':dates, 'eval_dates':result['dates'], 'eval_y':result['y']}
    rows = []
    for a in frozen.ALPHAS:
        # The A dictionary is the actual dictionary expanded by run_series with C and R0 arms.
        pred, experts = captured[(a, 'A', 1000)]
        aa = str(a)
        arrays['base_q_'+aa] = qr[a]
        arrays['base_e_'+aa] = er[a]
        arrays['weights_'+aa] = pred['A2'][2]['weights']
        arrays['a0_warmup_q_'+aa] = pred['A0'][0]
        for g in frozen.MAIN_GROUPS:
            q, e, _ = pred[g]
            qe, ee = q[1000:], e[1000:]
            score = frozen.v1.fz0(result['y'], qe, ee, a)
            assert np.array_equal(score, result['fz'][(a,g)]), (a,g)
            arrays['q_'+aa+'_'+g] = qe
            arrays['e_'+aa+'_'+g] = ee
            arrays['fz_'+aa+'_'+g] = score
            rows.append(pd.DataFrame({'date':result['dates'], 'alpha':a,'group':g,'y':result['y'],
                                      'q':qe,'e':ee,'fz0':score,'hit':result['y']<qe}))
        for H, ex in zip(frozen.r1.HALF_LIVES, experts):
            arrays[f'expert_q_{aa}_{H}'] = ex[0]
            arrays[f'expert_e_{aa}_{H}'] = ex[1]
    np.savez_compressed(out/'forecasts.npz', **arrays)
    pd.concat(rows, ignore_index=True).to_csv(out/'daily_forecasts.csv.gz', index=False, compression={'method':'gzip','mtime':0})
    assert all(sha(SOURCE/p)==h for p,h in source_hashes.items())
    save_json(out/'forecast_meta.json', {**notes, 'seconds':time.time()-started, 'refit_failures':result['refit_failures'],
               'forecast_sha256':sha(out/'forecasts.npz'), 'capture_exact_score_match_all_main_arms':True,
               'frozen_sources_unchanged':True, 'completed_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps(notes, indent=2), flush=True)

def hac_cov(X, residual, lag=250):
    score = X * residual[:,None]
    meat = score.T @ score
    for k in range(1, min(lag,len(X)-1)+1):
        cross = score[k:].T @ score[:-k]
        meat += (1-k/(lag+1))*(cross+cross.T)
    bread = np.linalg.inv(X.T @ X)
    return bread @ meat @ bread

def state_stats(d, mask):
    m = float(d[mask].mean()); p = mask.mean()
    influence = mask*(d-m)/p
    variance = hac_cov(np.ones((len(d),1)), influence)[0,0]
    se = np.sqrt(max(0.,variance))
    return {'days':int(mask.sum()), 'mean':m,'hac250_se':float(se), 'ci_low':m-1.96*se,'ci_high':m+1.96*se}

def summarize(out, dest):
    dest.mkdir(parents=True, exist_ok=False)
    z = np.load(out/'forecasts.npz', allow_pickle=False)
    dates=z['eval_dates']; y=z['eval_y']; all_y=z['all_returns']; n=len(y)
    rng=np.random.default_rng(frozen.SEED)
    params=json.loads((SOURCE/'confirm'/'freeze_params.json').read_text())['block_lengths']
    tests=[]; states=[]; tertiles=[]; regressions=[]; daily=[]
    for a in frozen.ALPHAS:
        aa=str(a); d=z['fz_'+aa+'_A2']-z['fz_'+aa+'_A0']
        default=params[f'H1@{a}']['block']
        for other in ('A0','A1d','A3','R0','F'):
            difference=z['fz_'+aa+'_A2']-z['fz_'+aa+'_'+other]
            for b in ([default,20,60,250] if other=='A0' else [default]):
                null=frozen.boot_null(difference[:,None],frozen.decade(dates),b,rng)[:,0]
                m=float(difference.mean())
                tests.append({'alpha':a,'contrast':'A2_vs_'+other,'block':b,'days':n,'mean':m,
                    'ci_low':m+float(np.quantile(null,.025)), 'ci_high':m+float(np.quantile(null,.975)),
                    'p_one_sided':float((1+np.sum(null<=m))/(1+frozen.BOOT)),
                    'primary':a==.025 and other=='A0' and b==default})
        base_test=next(row for row in tests if row['alpha']==a and row['contrast']=='A2_vs_A0' and row['block']==default)
        r60=pd.Series(all_y).rolling(60).sum().to_numpy()[3000:]
        threshold=float(np.quantile(r60,.10)); state=r60<=threshold
        denominator=float(d.sum())
        unstable=abs(float(d.mean()))<=1e-8 or base_test['ci_low']<=0<=base_test['ci_high']
        ratio=float(d[state].sum()/denominator) if denominator else None
        for flag,label in ((True,'sharp_appreciation'),(False,'other_days')):
            states.append({'alpha':a,'state':label,**state_stats(d,state==flag),'r60_threshold':threshold,
                'total_sum_d':denominator,'state_sum_d':float(d[state==flag].sum()),
                'appreciation_contribution_ratio':ratio,'ratio_unstable':unstable,
                'evidence':'retrospective, full-period quantile'})
        warm_y=all_y[2000:]
        warm_hit=(warm_y<z['a0_warmup_q_'+aa]).astype(float)
        signal=pd.Series(warm_hit).shift(1).rolling(250).mean().to_numpy()[1000:]-a
        assert np.isfinite(signal).all()
        cuts=np.quantile(signal,[1/3,2/3]); groups=np.digitize(signal,cuts,right=True)
        for g in range(3):
            mask=groups==g
            tertiles.append({'alpha':a,'tertile':g+1,'days':int(mask.sum()),'signal_min':float(signal[mask].min()) if mask.any() else None,
                 'signal_max':float(signal[mask].max()) if mask.any() else None,
                 **(state_stats(d,mask) if mask.any() else {'mean':None}), 'cut1':cuts[0],'cut2':cuts[1]})
        X=np.column_stack([np.ones(n),signal]); beta=np.linalg.lstsq(X,d,rcond=None)[0]
        cov=hac_cov(X,d-X@beta); se=np.sqrt(cov[1,1])
        regressions.append({'alpha':a,'days':n,'intercept':float(beta[0]),'slope':float(beta[1]),'hac_lag':250,
                            'slope_se':float(se),'ci_low':float(beta[1]-1.96*se),'ci_high':float(beta[1]+1.96*se)})
        daily.append(pd.DataFrame({'date':dates,'alpha':a,'d_A2_A0':d,'r60':r60,'appreciation_state':state,
                                   'lagged_signal':signal,'signal_tertile':groups+1}))
    for name,rows in [('tests',tests),('appreciation',states),('signal_tertiles',tertiles),('signal_regression',regressions)]:
        pd.DataFrame(rows).to_csv(dest/(name+'.csv'),index=False)
    pd.concat(daily).to_csv(dest/'descriptive_daily.csv',index=False)
    primary=next(row for row in tests if row['primary'])
    verdict={'primary':primary,'confirmed':primary['p_one_sided']<.05,'holm_applied':False,
             'interpretation':('D1 outperformed the uncalibrated combination in the historical-yen evaluation.'
                if primary['p_one_sided']<.05 else 'The development-period yen improvement was not confirmed in the historical held-out evaluation.'),
             'forecast_sha256':sha(out/'forecasts.npz'),'script_sha256':sha(__file__),
             'completed_utc':datetime.now(timezone.utc).isoformat()}
    save_json(dest/'verdict.json',verdict)
    print(json.dumps(verdict,indent=2),flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['fetch','forecast','summarize'])
    p.add_argument('--out',type=Path,default=ROOT/'outputs'/'reproduced'/'study2_run1')
    p.add_argument('--summary',type=Path,default=ROOT/'outputs'/'reproduced'/'study2_summary')
    args=p.parse_args()
    if args.action=='fetch': fetch()
    elif args.action=='forecast': forecast(args.out)
    else: summarize(args.out,args.summary)

if __name__=='__main__': main()
