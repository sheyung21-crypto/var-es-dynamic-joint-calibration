"""Confirmation run of the frozen research protocol: one pass on unexplored data.

Usage:
  python -I -X utf8 confirm_run.py <data dir> <output dir>   confirmation data, after the freeze commit
  python -I -X utf8 confirm_run.py --dev <output dir>        same pipeline on explored DEXUSEU and DEXJPUS

Implements sections 3-6 of the protocol (see provenance/Prespecified_Design.md):
expanded10 pool (1,000-day estimation, GARCH refits every 20 days), equal weights (A) and
MCS-filtered equal weights (C), calibrations S1 every 20 days and daily, the four-speed D1
aggregate, Ye et al., the single GJR-t reference R0, and the stratified stationary-bootstrap
tests of H1-H3 with Holm. Model and calibration code is imported unchanged from the
development rounds and the Amendola et al. MCS port in pilot5.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'; os.environ['OMP_NUM_THREADS'] = '1'
import hashlib, io, json, math, platform, subprocess, sys, time, zipfile
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2, norm

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
sys.path.insert(0, str(RUN / 'devcheck_round3')); sys.path.insert(0, str(RUN / 'pilot5'))
import devcheck_round3 as r3  # noqa: E402
import pilot as mcs  # noqa: E402
r2, r1, v1 = r3.r2, r3.r1, r3.v1

ALPHAS = (0.025, 0.01)
START = '1963-07-01'
EST = 1000              # days 1-1,000 estimate the base models (built into v1.rebuild_pool)
CAL = 1000              # pool index of day 2,001: MCS selection and every calibration start here
EVAL = 2000             # pool index of day 3,001: common evaluation period
ROBUST = 4000           # pool index of day 5,001: period of the 2,000-day window robustness check
MCS_STEP, MCS_LEVEL, MCS_BOOT = 20, 0.25, 1000
ETA, YE_TUNED, YE_FAITHFUL = 2.0, 0.01, 0.05
BOOT, SEED, CHUNK = 9999, 20261024, 200
SENS_BLOCKS = (20, 60, 250)
CRISIS_DAYS = 60
INDICES = ['TWII', 'KS11', 'FTSE', 'GDAXI', 'AXJO', 'GSPTSE']
MAIN_GROUPS = ['A0', 'A1', 'A1d', 'A2', 'A3', 'A3f', 'F', 'C0', 'C1', 'C1d', 'C2', 'C3', 'R0']
ROBUST_GROUPS = ['A1_2k', 'A1d_2k', 'C0_2k', 'C1_2k', 'C1d_2k', 'C2_2k', 'C3_2k']
PRIMARY = {'H1': ('A2', 'A0'), 'H2': ('A2', 'A1d'), 'H3': ('A2', 'A3')}
SECONDARY = {'A2_vs_F': ('A2', 'F'), 'A2_vs_A1': ('A2', 'A1'), 'A2_vs_A3f': ('A2', 'A3f'),
             'A2_vs_R0': ('A2', 'R0'), 'C2_vs_C0': ('C2', 'C0'), 'C0_vs_A0': ('C0', 'A0'),
             'C1d_vs_A1d': ('C1d', 'A1d'), 'C2_vs_A2': ('C2', 'A2'), 'C3_vs_A3': ('C3', 'A3')}
ROBUST_CONTRASTS = {'H1': ('A2', 'A0'), 'H2': ('A2', 'A1d_2k'), 'H3': ('A2', 'A3'),
                    'H2_main_window': ('A2', 'A1d'), 'C0_vs_A0': ('C0_2k', 'A0'), 'C2_vs_A2': ('C2_2k', 'A2')}
H4_PAIRS = {'D1': (('C0', 'A0'), ('C2', 'A2')), 'S1_daily': (('C0', 'A0'), ('C1d', 'A1d')),
            'Ye': (('C0', 'A0'), ('C3', 'A3'))}


# ---------------------------------------------------------------- data
def load_industries(data):
    z = zipfile.ZipFile(data / 'french' / '30_Industry_Portfolios_daily_CSV.zip')
    lines = z.read(z.namelist()[0]).decode('latin-1').splitlines()
    head = next(i for i, l in enumerate(lines) if 'Average Value Weighted Returns -- Daily' in l)
    end = next(i for i in range(head + 2, len(lines)) if not lines[i].strip()[:1].isdigit())
    df = pd.read_csv(io.StringIO('\n'.join(lines[head + 1:end])), skipinitialspace=True)
    df = df.rename(columns={df.columns[0]: 'date'})
    df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
    df = df[df['date'] >= START]
    series, notes = {}, {}
    for col in df.columns[1:]:
        r = df[col].to_numpy(float); ok = ~np.isin(r, (-99.99, -999.)) & np.isfinite(r)
        series[col] = ('industry', df['date'].to_numpy(dtype=str)[ok], 100 * np.log1p(r[ok] / 100))
        notes[col] = {'missing_days': int((~ok).sum())}
    return series, notes


def load_index(path):
    res = json.loads(path.read_text(encoding='utf-8'))['chart']['result'][0]
    ts = np.asarray(res['timestamp'], dtype=np.int64)
    close = np.asarray(res['indicators']['quote'][0]['close'], dtype=float)
    dates = pd.to_datetime(ts + res['meta']['gmtoffset'], unit='s').strftime('%Y-%m-%d')
    s = pd.Series(close, index=dates)
    dup = int(s.index.duplicated().sum()); s = s[~s.index.duplicated(keep='last')]
    null = int((~np.isfinite(s) | (s <= 0)).sum()); s = s[np.isfinite(s) & (s > 0)]
    p = s.to_numpy()
    return s.index.to_numpy(dtype=str)[1:], 100 * np.log(p[1:] / p[:-1]), {
        'rows': int(len(ts)), 'duplicate_dates_kept_last': dup, 'null_close_removed': null}


def load_confirmation(data):
    series, notes = load_industries(data)
    sets = {'industries': list(series)}
    for name in INDICES:
        d, y, note = load_index(data / 'yahoo' / f'yahoo_{name}.json')
        series[name] = ('index', d, y); notes[name] = note
    sets['indices'] = INDICES
    return series, notes, sets


def load_dev():
    series = {}
    for name in ('DEXUSEU', 'DEXJPUS'):
        v1.PRICES[name] = r1.SERIES[name][1]
        y, d = v1.load_returns(name)
        series[name] = ('fx', d, y)
    return series, {}, {'dev': ['DEXUSEU', 'DEXJPUS']}


# ---------------------------------------------------------------- per-series forecasts
def s1(y, q, e, alpha, refit, window):
    keep = v1.S1_WINDOW; v1.S1_WINDOW = window
    try:
        return v1.run_s1(y, q, e, alpha, refit)
    finally:
        v1.S1_WINDOW = keep


def mcs_combination(y, Q, E, alpha, window, start, rng):
    """MCS-filtered equal weights, re-selected every 20 days on the past `window` days of FZ0.

    Amendola et al. code: rugarch mcsTest range statistic (includedR), alpha 0.25, 1,000 block
    bootstrap draws, block length max over models of np::b.star (circular), at least 2.
    """
    M = len(y); L = v1.fz0(y[:, None], Q, E, alpha)
    qc = np.full(M, np.nan); ec = np.full(M, np.nan); sizes = []
    for t in range(start, M):
        if (t - start) % MCS_STEP == 0:
            x = L[t - window:t]; k = mcs.bstar(x)
            u = rng.random(math.ceil(window / k) * MCS_BOOT)
            boot = mcs.means_from_indices(x, mcs.block_indices(window, k, MCS_BOOT, u))
            keep = mcs.select(x.mean(0), boot - x.mean(0), alpha=MCS_LEVEL)[0]; sizes.append(len(keep))
        qc[t] = Q[t, keep].mean(); ec[t] = E[t, keep].mean()
    return qc, ec, sizes


def calibrate(y, q, e, alpha, window, prefix, extras):
    out = {f'{prefix}0': (q, e, {})}
    out[f'{prefix}1'] = s1(y, q, e, alpha, 20, window)
    out[f'{prefix}1d'] = s1(y, q, e, alpha, 1, window)
    experts = [r2.run_d1z1(y, q, e, alpha, H, 0.0) for H in r1.HALF_LIVES]
    out[f'{prefix}2'] = r3.run_aggregate(y, [x[:2] for x in experts], alpha, ETA)
    out[f'{prefix}3'] = r1.run_ye(y, q, e, alpha, YE_TUNED)
    if extras:
        out['A3f'] = r1.run_ye(y, q, e, alpha, YE_FAITHFUL)
        out['F'] = (np.mean([x[0] for x in experts], 0), np.mean([x[1] for x in experts], 0), {})
    return out, experts


def kupiec(hit, alpha):
    n = len(hit); x = int(hit.sum()); pi = x / n
    ll0 = (n - x) * math.log(1 - alpha) + x * math.log(alpha)
    ll1 = ((n - x) * math.log(1 - pi) if x < n else 0.) + (x * math.log(pi) if x else 0.)
    return float(chi2.sf(max(0., -2 * (ll0 - ll1)), 1))


def christoffersen(hit):
    a, b = hit[:-1], hit[1:]
    n = {(i, j): int(((a == i) & (b == j)).sum()) for i in (0, 1) for j in (0, 1)}

    def ll(k0, k1):
        return 0. if k0 == 0 or k1 == 0 else k0 * math.log(k0 / (k0 + k1)) + k1 * math.log(k1 / (k0 + k1))
    l1 = ll(n[0, 0], n[0, 1]) + ll(n[1, 0], n[1, 1]); l0 = ll(n[0, 0] + n[1, 0], n[0, 1] + n[1, 1])
    return float(chi2.sf(max(0., -2 * (l0 - l1)), 1))


def metrics(y, q, e, alpha, base_q=None):
    hit = y < q; n = len(y)
    m = {'days': n, 'fz_mean': float(np.mean(v1.fz0(y, q, e, alpha))), 'breach_rate': float(hit.mean()),
         'kupiec_p': kupiec(hit, alpha), 'christoffersen_p': christoffersen(hit),
         'z2': float(1 - np.sum(hit * np.abs(y) / np.abs(e)) / (n * alpha)),
         'mean_abs_var': float(np.mean(-q)), 'mean_abs_es': float(np.mean(-e)),
         'over_conservative': bool(hit.mean() < 0.8 * alpha),
         'var_log_change': float(np.mean(np.abs(np.diff(np.log(-q))))),
         'es_log_change': float(np.mean(np.abs(np.diff(np.log(-e))))),
         'es_equals_var_days': int(np.sum(e >= q))}
    if base_q is not None:
        m['coef_log_change'] = float(np.mean(np.abs(np.diff(np.log(q / base_q)))))
    if alpha == 0.01:
        c = np.convolve(hit.astype(int), np.ones(250, int), 'valid')
        m['basel_yellow_share'] = float(np.mean((c >= 5) & (c <= 9))); m['basel_red_share'] = float(np.mean(c >= 10))
    return m


def run_series(job):
    name, klass, dates, y, seed = job
    started = time.time()
    v1.load_returns = lambda asset: (y, dates)   # rebuild_pool reads returns through this hook
    q_r, e_r, refits = v1.rebuild_pool(name, {'dates': dates[EST:], 'y': y[EST:]})
    yy, dd = y[EST:], dates[EST:]; M = len(yy); rng = np.random.default_rng(seed)
    robust = M > ROBUST + 250
    out = {'name': name, 'class': klass, 'dates': dd[EVAL:], 'y': yy[EVAL:], 'robust_start': dd[ROBUST] if robust else None,
           'fz': {}, 'hit': {}, 'metrics': [], 'crisis': [], 'states': [], 'diag': [],
           'refit_failures': {m: sum(1 for r in refits if r['model'] == m and r['status'] != 'success')
                              for m in ('GARCH_T', 'GJR')}}
    ye = yy[EVAL:]
    for alpha in ALPHAS:
        Q, E = q_r[alpha][:, v1.POOL], e_r[alpha][:, v1.POOL]
        q0, e0 = Q.mean(1), E.mean(1)
        qC, eC, sizes = mcs_combination(yy, Q, E, alpha, 1000, CAL, rng)
        seg = slice(CAL, M); ys = yy[seg]
        pred, experts = calibrate(ys, q0[seg], e0[seg], alpha, 1000, 'A', True)
        cpred, _ = calibrate(ys, qC[seg], eC[seg], alpha, 1000, 'C', False)
        pred.update(cpred); pred['R0'] = (q_r[alpha][seg, 11], e_r[alpha][seg, 11], {})
        diag = {'name': name, 'alpha': alpha, 'mcs_mean_size': float(np.mean(sizes)),
                'mcs_full_set_share': float(np.mean(np.array(sizes) == len(v1.POOL))),
                's1_clipped_fits_A1': pred['A1'][2]['clipped_fits'], 's1_clipped_fits_A1d': pred['A1d'][2]['clipped_fits'],
                'ye_lambda_zero_share': float(np.mean(pred['A3'][2]['lambda'][EVAL - CAL:-1] == 0))}
        W = pred['A2'][2]['weights'][EVAL - CAL:]
        for H, w, ex in zip(r1.HALF_LIVES, W.mean(0), experts):
            diag[f'agg_weight_H{H}'] = float(w)
            diag[f'var_floor_share_H{H}'] = float(np.mean(ex[2]['log_cq'][EVAL - CAL:-1] <= 0))
        qC2 = np.full(M, np.nan)
        if robust:
            qC2, eC2, sizes2 = mcs_combination(yy, Q, E, alpha, 2000, EVAL, rng)
            seg2 = slice(EVAL, M); ys2 = yy[seg2]; pad = np.full(EVAL - CAL, np.nan)
            for g, refit in (('A1_2k', 20), ('A1d_2k', 1)):
                qq, ee, info = s1(ys2, q0[seg2], e0[seg2], alpha, refit, 2000); pred[g] = (np.r_[pad, qq], np.r_[pad, ee], info)
            c2, _ = calibrate(ys2, qC2[seg2], eC2[seg2], alpha, 2000, 'C', False)
            for g, (qq, ee, info) in c2.items():
                pred[g + '_2k'] = (np.r_[pad, qq], np.r_[pad, ee], info)
            diag['mcs2k_mean_size'] = float(np.mean(sizes2))
        out['diag'].append(diag)

        def base_of(g):
            """Uncalibrated combination behind a calibrated group, for the coefficient-stability metric."""
            if g in ('A0', 'C0', 'C0_2k', 'R0'):
                return None
            if g.startswith('A') or g == 'F':
                return q0[seg][EVAL - CAL:]
            return (qC2 if g.endswith('_2k') else qC)[seg][EVAL - CAL:]
        for g, (qq, ee, _) in pred.items():
            qe, ee_ = qq[EVAL - CAL:], ee[EVAL - CAL:]
            ok = np.isfinite(qe)
            fz = np.full(len(ye), np.nan); fz[ok] = v1.fz0(ye[ok], qe[ok], ee_[ok], alpha)
            out['fz'][(alpha, g)] = fz; out['hit'][(alpha, g)] = np.where(ok, ye < qe, False)
            periods = [('main', ok)] if not g.endswith('_2k') else []
            if robust:
                periods.append(('robust', np.arange(len(ye)) >= ROBUST - EVAL))
            bq = base_of(g)
            for period, mask in periods:
                m = metrics(ye[mask], qe[mask], ee_[mask], alpha, None if bq is None else bq[mask])
                legal = bool(np.all(qe[mask] < 0) and np.all(ee_[mask] <= qe[mask]) and np.all(np.isfinite(fz[mask])))
                out['metrics'].append({'name': name, 'class': klass, 'alpha': alpha, 'group': g, 'period': period,
                                       'legal': legal, **m})
        for shock in r1.SHOCKS:
            if shock < out['dates'][0]:
                continue
            j = int(np.searchsorted(out['dates'], shock))
            if j + CRISIS_DAYS > len(ye):
                continue
            w = slice(j, j + CRISIS_DAYS)
            for g in MAIN_GROUPS:
                out['crisis'].append({'name': name, 'alpha': alpha, 'shock': shock, 'first_day': out['dates'][j],
                                      'group': g, 'breach_rate': float(out['hit'][(alpha, g)][w].mean()),
                                      'fz_mean': float(out['fz'][(alpha, g)][w].mean())})
        var0 = -pred['A0'][0][EVAL - CAL:]; cut = np.quantile(var0, [1 / 3, 2 / 3])
        state = np.digitize(var0, cut)
        for g in ('A0', 'A1d', 'A2', 'A3'):
            qe, ee_ = pred[g][0][EVAL - CAL:], pred[g][1][EVAL - CAL:]
            for s, label in enumerate(('low', 'mid', 'high')):
                k = state == s; hit = ye[k] < qe[k]
                out['states'].append({'name': name, 'alpha': alpha, 'group': g, 'state': label, 'days': int(k.sum()),
                                      'breach_rate': float(hit.mean()),
                                      'z2': float(1 - np.sum(hit * np.abs(ye[k]) / np.abs(ee_[k])) / (k.sum() * alpha))})
    out['seconds'] = time.time() - started
    return out


# ---------------------------------------------------------------- inference
def sb_draws(n, b, reps, rng):
    """Stationary-bootstrap indices (Politis-Romano), mean block length b, wrapping inside the stratum."""
    new = rng.random((reps, n)) < 1.0 / b; new[:, 0] = True
    start = rng.integers(0, n, size=(reps, n))
    last = np.maximum.accumulate(np.where(new, np.arange(n), 0), axis=1)
    return (np.take_along_axis(start, last, axis=1) + np.arange(n) - last) % n


def boot_null(D, strata, b, rng):
    """Centred, decade-stratified stationary-bootstrap means of each column of D, weighted by days."""
    out = np.zeros((BOOT, D.shape[1])); n = len(D)
    for s in np.unique(strata):
        idx = np.flatnonzero(strata == s); Ds = D[idx] - D[idx].mean(0); w = len(idx) / n
        for c0 in range(0, BOOT, CHUNK):
            r = min(CHUNK, BOOT - c0)
            out[c0:c0 + r] += w * Ds[sb_draws(len(idx), b, r, rng)].mean(1)
    return out


def nw(d, lag):
    x = d - d.mean(); n = len(d); lrv = x @ x / n
    for k in range(1, lag + 1):
        lrv += 2 * (1 - k / (lag + 1)) * (x[k:] @ x[:-k]) / n
    t = d.mean() / math.sqrt(lrv / n)
    return float(t), float(norm.cdf(t))


def holm(p):
    adj, run, m = {}, 0., len(p)
    for i, k in enumerate(sorted(p, key=p.get)):
        run = max(run, min(1., (m - i) * p[k])); adj[k] = run
    return adj


def decade(dates):
    return np.array([int(d[:3]) * 10 for d in dates])


def test_rows(means, contrasts, blocks, rng, kind, setname, alpha, mask=None):
    """One-sided stratified stationary-bootstrap test of E[d] < 0 for each contrast, plus NW checks."""
    dates = means.index.to_numpy(dtype=str)
    keep = np.ones(len(dates), bool) if mask is None else mask
    D = np.column_stack([(means[a] - means[b]).to_numpy()[keep] for a, b in contrasts.values()])
    D_ok = np.isfinite(D).all(1); D = D[D_ok]; dd = dates[keep][D_ok]; strata = decade(dd); n = len(D)
    rows = []
    for j, (name, (a, b)) in enumerate(contrasts.items()):
        for blk, tag in [(blocks.get(name, blocks['default']), 'pw')] + [(s, f'b{s}') for s in SENS_BLOCKS]:
            null = boot_null(D[:, [j]], strata, blk, rng)[:, 0]; d = float(D[:, j].mean())
            lag_auto = int(math.floor(4 * (n / 100) ** (2 / 9)))
            t_auto, p_auto = nw(D[:, j], lag_auto)
            rows.append({'set': setname, 'alpha': alpha, 'kind': kind, 'contrast': name, 'a': a, 'b': b,
                         'block_spec': tag, 'block': blk, 'days': n, 'first': dd[0], 'last': dd[-1], 'mean': d,
                         'ci_low': float(d + np.quantile(null, .025)), 'ci_high': float(d + np.quantile(null, .975)),
                         'p_one_sided': float((1 + np.sum(null <= d)) / (1 + BOOT)),
                         'nw_lag': lag_auto, 'nw_t': t_auto, 'nw_p': p_auto,
                         **{f'nw_p_lag{L}': nw(D[:, j], L)[1] for L in SENS_BLOCKS}})
            if kind != 'primary':
                break
    return rows


def period_rows(means, contrasts, setname, alpha):
    rows = []; dates = means.index.to_numpy(dtype=str)
    labels = {f'{d}s': decade(dates) == d for d in np.unique(decade(dates))}
    labels.update({'1975-2012': dates < '2013-01-01', '2013-': dates >= '2013-01-01'})
    for name, (a, b) in contrasts.items():
        d = (means[a] - means[b]).to_numpy()
        for label, k in labels.items():
            x = d[k & np.isfinite(d)]
            if len(x) > 30:
                lag = int(math.floor(4 * (len(x) / 100) ** (2 / 9))); t, p = nw(x, lag)
                se = abs(x.mean() / t) if t else float('nan')
                rows.append({'set': setname, 'alpha': alpha, 'contrast': name, 'period': label, 'days': len(x),
                             'mean': float(x.mean()), 'nw_ci_low': float(x.mean() - 1.96 * se),
                             'nw_ci_high': float(x.mean() + 1.96 * se)})
    return rows


def verdict(primary, h5):
    p = {r['contrast']: r for r in primary}
    sig = {k: p[k]['p_holm'] < 0.05 for k in PRIMARY}
    risk = h5['A2']['breach_in_tolerance'] and not h5['A2']['over_conservative'] and h5['A2']['abs_z2_below_A0']
    if not sig['H1']:
        row = 'H1 不成立：D1 未達標，照實報告；不在確認資料上重調'
    elif sig['H2'] and sig['H3']:
        row = ('H1–H3 都成立，風險代價可接受：方法論文，D1 是有效改進，而且勝過最接近的線上方法' if risk else
               'H1–H3 都成立，但風險代價未達第 6 節標準：照實報告兩者')
    else:
        row = 'H1 成立，H2 或 H3 不成立：實證比較，校準有效，但 D1 沒有勝過滾動批次或 Ye 等（不顯著者寫「無法區分」）'
    return {'significant_after_holm': sig, 'risk_cost_acceptable': risk, 'section6_row': row}


# ---------------------------------------------------------------- main
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    started = time.time()
    dev = sys.argv[1] == '--dev'
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=RUN, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'confirm', 'quickcheck_d1', 'devcheck_d1v2',
                                'devcheck_round2', 'devcheck_round3', 'pilot5/pilot.py'], cwd=RUN, capture_output=True,
                               text=True).stdout.strip()
    except OSError:
        commit, dirty = '', 'git unavailable'
    out_dir = Path(sys.argv[2]); out_dir.mkdir(parents=True, exist_ok=False)
    if dev:
        series, notes, sets = load_dev(); data = None
    else:
        data = Path(sys.argv[1]); series, notes, sets = load_confirmation(data)
    params = json.loads((HERE / 'freeze_params.json').read_text(encoding='utf-8'))['block_lengths']
    jobs = [(name, klass, d, y, SEED + i) for i, (name, (klass, d, y)) in enumerate(series.items())]
    workers = min(len(jobs), max(1, (os.cpu_count() or 2) - 2))
    with Pool(workers) as pool:
        results = {r['name']: r for r in pool.imap_unordered(run_series, jobs)}
    print(f'forecasts done in {time.time() - started:.0f}s', flush=True)
    metrics_df = pd.DataFrame([m for r in results.values() for m in r['metrics']])
    if not metrics_df['legal'].all():
        bad = metrics_df[~metrics_df['legal']][['name', 'alpha', 'group', 'period']]
        raise SystemExit(f'illegal forecasts:\n{bad}')
    metrics_df.to_csv(out_dir / 'confirm_series_metrics.csv', index=False)
    pd.DataFrame([d for r in results.values() for d in r['diag']]).to_csv(out_dir / 'confirm_diagnostics.csv', index=False)
    pd.DataFrame([s for r in results.values() for s in r['states']]).to_csv(out_dir / 'confirm_states.csv', index=False)
    crisis = pd.DataFrame([c for r in results.values() for c in r['crisis']])
    rng = np.random.default_rng(SEED)
    tests, periods, crisis_rows, h4_rows, h5_rows, daily, verdicts = [], [], [], [], [], [], {}
    for setname, names in sets.items():
        for alpha in ALPHAS:
            groups = MAIN_GROUPS + [g for g in ROBUST_GROUPS if (alpha, g) in results[names[0]]['fz']]
            means = pd.DataFrame({g: pd.concat([pd.Series(results[n]['fz'][(alpha, g)], index=results[n]['dates'])
                                                for n in names if (alpha, g) in results[n]['fz']], axis=1).mean(axis=1)
                                  for g in groups}).sort_index()
            means.index = means.index.astype(str)
            daily.append(means.assign(set=setname, alpha=alpha).reset_index(names='date'))
            blocks = {h: params[f'{h}@{alpha}']['block'] for h in PRIMARY}; blocks['default'] = blocks['H1']
            kind = 'primary' if setname in ('industries', 'dev') else 'replication'
            prim = test_rows(means[MAIN_GROUPS], PRIMARY, blocks, rng, kind, setname, alpha)
            if kind == 'primary':
                pw = {r['contrast']: r['p_one_sided'] for r in prim if r['block_spec'] == 'pw'}
                adj = holm(pw)
                for r in prim:
                    if r['block_spec'] == 'pw':
                        r['p_holm'] = adj[r['contrast']]
            tests += prim
            tests += test_rows(means[MAIN_GROUPS], SECONDARY, blocks, rng, 'secondary', setname, alpha)
            starts = [results[n]['robust_start'] for n in names if results[n]['robust_start']]
            if starts and all(g in means for g in ROBUST_GROUPS):
                mask = means.index.to_numpy(dtype=str) >= max(starts)
                tests += test_rows(means, ROBUST_CONTRASTS, blocks, rng, 'robust_2000_window', setname, alpha, mask)
            periods += period_rows(means, {**PRIMARY, 'A2_vs_F': ('A2', 'F')}, setname, alpha)
            for label, ((a0, b0), (a1, b1)) in H4_PAIRS.items():
                before = (means[a0] - means[b0]).to_numpy(); after = (means[a1] - means[b1]).to_numpy()
                ok = np.isfinite(before) & np.isfinite(after)
                null = boot_null(np.column_stack([before[ok], after[ok]]), decade(means.index.to_numpy(dtype=str)[ok]),
                                 blocks['H1'], rng)
                diff = float(after[ok].mean() - before[ok].mean()); nd = null[:, 1] - null[:, 0]
                h4_rows.append({'set': setname, 'alpha': alpha, 'calibration': label,
                                'mcs_gap_before': float(before[ok].mean()), 'mcs_gap_after': float(after[ok].mean()),
                                'after_minus_before': diff, 'ci_low': float(diff + np.quantile(nd, .025)),
                                'ci_high': float(diff + np.quantile(nd, .975)),
                                'abs_gap_shrinks': bool(abs(after[ok].mean()) < abs(before[ok].mean()))})
            h5 = {}
            for g in ('A0', 'A2', 'A1d', 'A3'):
                rate = float(np.concatenate([results[n]['hit'][(alpha, g)] for n in names]).mean())
                m = metrics_df[(metrics_df['name'].isin(names)) & (metrics_df.alpha == alpha) & (metrics_df.group == g)
                               & (metrics_df.period == 'main')]
                h5[g] = {'breach_rate': rate, 'z2_day_weighted': float(np.average(m['z2'], weights=m['days'])),
                         'breach_in_tolerance': bool(0.9 * alpha <= rate <= 1.1 * alpha),
                         'over_conservative': bool(rate < 0.8 * alpha)}
            for g in h5:
                h5[g]['abs_z2_below_A0'] = bool(abs(h5[g]['z2_day_weighted']) < abs(h5['A0']['z2_day_weighted']))
                h5_rows.append({'set': setname, 'alpha': alpha, 'group': g, **h5[g]})
            if kind == 'primary':
                verdicts[f'{setname}@{alpha}'] = verdict([r for r in prim if r['block_spec'] == 'pw'], h5)
            sub = crisis[crisis['name'].isin(names) & (crisis.alpha == alpha)] if len(crisis) else crisis
            if len(sub):
                agg = sub.groupby(['shock', 'group']).agg(series=('name', 'nunique'), first_day=('first_day', 'min'),
                                                         breach_rate=('breach_rate', 'mean'), fz_mean=('fz_mean', 'mean'))
                crisis_rows.append(agg.reset_index().assign(set=setname, alpha=alpha))
    pd.DataFrame(tests).to_csv(out_dir / 'confirm_tests.csv', index=False)
    pd.DataFrame(periods).to_csv(out_dir / 'confirm_periods.csv', index=False)
    pd.DataFrame(h4_rows).to_csv(out_dir / 'confirm_h4.csv', index=False)
    pd.DataFrame(h5_rows).to_csv(out_dir / 'confirm_h5.csv', index=False)
    crisis.to_csv(out_dir / 'confirm_crisis_by_series.csv', index=False)
    if crisis_rows:
        pd.concat(crisis_rows).to_csv(out_dir / 'confirm_crisis.csv', index=False)
    pd.concat(daily).to_csv(out_dir / 'confirm_daily_means.csv', index=False)
    pool_check = None
    if dev:
        old = pd.read_csv(RUN / 'devcheck_round3' / 'devcheck3_daily.csv')
        old = old[(old.arm == 'A0') & old.market.isin(list(results))]
        new = pd.concat([pd.DataFrame({'market': n, 'alpha': a, 'date': r['dates'], 'fz_new': r['fz'][(a, 'A0')]})
                         for n, r in results.items() for a in ALPHAS])
        both = old.merge(new, on=['market', 'alpha', 'date'])
        pool_check = {'overlap_days': len(both), 'a0_max_abs_gap_vs_round3': float((both.fz0 - both.fz_new).abs().max())}
    meta = {'mode': 'development dry run (explored data)' if dev else 'confirmation (single frozen run)',
            'git_commit': commit, 'uncommitted_changes_in_used_code_at_start': dirty, 'verdict': verdicts,
            'dev_pool_reproduction': pool_check,
            'series': {n: {'class': r['class'], 'eval_first': r['dates'][0], 'eval_last': r['dates'][-1],
                           'eval_days': len(r['dates']), 'robust_start': r['robust_start'],
                           'refit_failures': r['refit_failures'], 'seconds': round(r['seconds'], 1),
                           **notes.get(n, {})} for n, r in sorted(results.items())},
            'inputs': json.loads((data / 'fetch_manifest.json').read_text(encoding='utf-8')) if data else 'dev series',
            'scripts': {p.name: sha256(p) for p in (HERE / 'confirm_run.py', HERE / 'freeze_params.py',
                                                    RUN / 'quickcheck_d1' / 'quickcheck_d1.py',
                                                    RUN / 'devcheck_d1v2' / 'devcheck_d1v2.py',
                                                    RUN / 'devcheck_round2' / 'devcheck_round2.py',
                                                    RUN / 'devcheck_round3' / 'devcheck_round3.py',
                                                    RUN / 'pilot5' / 'pilot.py')},
            'settings': {'alphas': ALPHAS, 'start': START, 'eval_from_day': EVAL + EST + 1, 'mcs': [MCS_STEP, MCS_LEVEL, MCS_BOOT],
                         'eta': ETA, 'ye_steps': [YE_TUNED, YE_FAITHFUL], 'boot': BOOT, 'seed': SEED, 'blocks': params},
            'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
            'seconds': round(time.time() - started, 1)}
    (out_dir / 'confirm_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(verdicts, indent=2, ensure_ascii=False))
    show = pd.DataFrame(tests); show = show[(show.block_spec == 'pw') | (show.kind != 'primary')]
    print(show[['set', 'alpha', 'kind', 'contrast', 'days', 'mean', 'ci_low', 'ci_high', 'p_one_sided']].round(5).to_string(index=False))


if __name__ == '__main__':
    sys.exit(main())
