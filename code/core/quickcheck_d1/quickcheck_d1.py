"""D1 quick check on explored development data: legality and primary FZ0 score.

Implements rule 1 of section 7 of the research protocol
(see provenance/Prespecified_Design.md). SP500 and DEXUSEU were explored in
earlier stages, so nothing here is confirmatory. Reads earlier-stage price files and the
stage4 base/forecast NPZs; writes only to this folder.

Methods on the expanded10 equal-weight combination (A0):
  A2  D1 daily online joint calibration (log multipliers), gamma grid
  A1d S1 rolling batch calibration refitted daily (closed-form FZ0 optimum)
  A1  S1 refitted every 20 days
  A3  Ye et al. (2026) projected online update, eq. (7) with loss (4)
At 99% also C0 (stored Raw250 MCS combination) and C2 (D1 on C0).
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'; os.environ['OMP_NUM_THREADS'] = '1'
import hashlib, json, platform, sys, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.stats import norm, t as student
import arch
from arch import arch_model

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
ASSETS = ['SP500', 'DEXUSEU']
PRICES = {'SP500': RUN / 'deepening5' / 'external_data' / 'SP500.csv',
          'DEXUSEU': RUN / 'stage3' / 'fx_data' / 'DEXUSEU.csv'}
EVAL_START = '2022-07-01'
ALPHAS = (0.025, 0.01)                       # primary 97.5%, secondary 99%
GAMMAS = (0.005, 0.01, 0.02, 0.05)
POOL = [8, 9, 10, 3, 4, 5, 6, 7, 11, 12]     # expanded10 in stage4 column order
NAMES = ['HS125', 'HS250', 'HS500', 'EWMA_N_006', 'EWMA_N_0006', 'EWMA_T5_006', 'EWMA_T5_0006',
         'GARCH_T', 'HS_EMP125', 'HS_EMP250', 'HS_EMP500', 'GJR_T', 'GJR_FHS']
S1_WINDOW, S1_MIN, S1_REFIT = 1000, 250, 20
COEF_BOX = (0.2, 5.0)
YE = {'step': 0.05, 'radius': 3.0, 'cap': 3.0, 'gap_floor': 0.05, 'a': 0.025, 'b': 0.025, 'budget': 0.05}
BLOCK, BOOT, SEED = 20, 1999, 20261024
MCS_METHOD = 'Raw250'


def fz0(y, q, e, alpha):
    return -np.maximum(q - y, 0) / (alpha * e) + q / e + np.log(-e) - 1


def normal_qe(alpha):
    q = norm.ppf(alpha)
    return q, -norm.pdf(q) / alpha


def t_qe(nu, alpha):
    z = student.ppf(alpha, nu); s = np.sqrt((nu - 2) / nu)
    return s * z, -s * (nu + z * z) / (nu - 1) * student.pdf(z, nu) / alpha


def empirical_qe(values, alpha):
    """Same definition as stage4/pool_generate.empirical_qe."""
    z = np.sort(np.asarray(values, dtype=float)); z = z[np.isfinite(z)]
    a = len(z) * alpha; k = int(np.floor(a)); f = a - k
    return float(z[int(np.ceil(a)) - 1]), float((z[:k].sum() + (f * z[k] if f > 0 else 0.)) / a)


def load_returns(asset):
    s = pd.read_csv(PRICES[asset]); col = s.columns[0]
    s[col] = pd.to_datetime(s[col]); s[asset] = pd.to_numeric(s[asset], errors='coerce')
    s = s.loc[s[asset].notna() & (s[col] <= '2026-10-22')]
    y = 100 * np.log(s[asset].to_numpy()[1:] / s[asset].to_numpy()[:-1])
    return y, s[col].iloc[1:].dt.strftime('%Y-%m-%d').to_numpy(dtype=str)


def rebuild_pool(asset, stored):
    """Rebuild expanded10 at every alpha with the original model definitions.

    EWMA and GARCH-t follow deepening5/external_validate.py and stage3/gate_validate.py;
    HS_EMP, GJR-t and GJR-FHS follow stage4/pool_empirical_run.py.
    """
    y, dates = load_returns(asset)
    N = len(y) - 1000
    assert np.array_equal(dates[1000:], stored['dates']) and np.array_equal(y[1000:], stored['y'])
    q = {a: np.full((N, 13), np.nan) for a in ALPHAS}; e = {a: np.full((N, 13), np.nan) for a in ALPHAS}
    v = np.array([np.mean(y[:1000] ** 2)] * 2); rates = np.array([.06, .006])
    garch = gvar = None; gjr = h = resid = None; log = []
    for t in range(N):
        i = 1000 + t
        if t % 20 == 0:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    fit = arch_model(y[i - 1000:i], mean='Zero', vol='GARCH', p=1, q=1, dist='StudentsT',
                                     rescale=False).fit(disp='off', show_warning=False)
                if fit.convergence_flag != 0:
                    raise RuntimeError(f'convergence_flag={fit.convergence_flag}')
                if not np.isfinite(fit.params).all() or fit.params['nu'] <= 2:
                    raise RuntimeError('invalid parameters')
                garch = fit.params.to_dict(); gvar = float(fit.forecast(horizon=1, reindex=False).variance.iloc[-1, 0])
                log.append({'model': 'GARCH_T', 't': t, 'date': dates[i], 'status': 'success'})
            except Exception as ex:
                if garch:
                    gvar = garch['omega'] + garch['alpha[1]'] * y[i - 1] ** 2 + garch['beta[1]'] * gvar
                log.append({'model': 'GARCH_T', 't': t, 'date': dates[i], 'status': 'failed', 'error': repr(ex)})
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    fit = arch_model(y[i - 1000:i], mean='Zero', vol='GARCH', p=1, o=1, q=1, power=2.,
                                     dist='StudentsT', rescale=False).fit(disp='off', show_warning=False,
                                                                           options={'maxiter': 300})
                if fit.convergence_flag != 0:
                    raise RuntimeError('optimizer did not converge')
                gjr = {k: float(val) for k, val in fit.params.items()}
                h = float(fit.forecast(horizon=1, reindex=False).variance.iloc[-1, 0])
                resid = np.asarray(fit.resid) / np.asarray(fit.conditional_volatility)
                resid = resid[np.isfinite(resid)][-1000:]
                log.append({'model': 'GJR', 't': t, 'date': dates[i], 'status': 'success'})
            except Exception as ex:
                log.append({'model': 'GJR', 't': t, 'date': dates[i], 'status': 'retained_previous', 'error': repr(ex)})
        elif garch:
            gvar = garch['omega'] + garch['alpha[1]'] * y[i - 1] ** 2 + garch['beta[1]'] * gvar
        sigma = np.sqrt(h) if gjr else None
        for a in ALPHAS:
            qn, en = normal_qe(a); qt, et = t_qe(5., a)
            for j, w in enumerate((125, 250, 500)):
                q[a][t, 8 + j], e[a][t, 8 + j] = empirical_qe(y[i - w:i], a)
            q[a][t, 3:5] = np.sqrt(v) * qn; e[a][t, 3:5] = np.sqrt(v) * en
            q[a][t, 5:7] = np.sqrt(v) * qt; e[a][t, 5:7] = np.sqrt(v) * et
            if garch:
                gq, ge = t_qe(garch['nu'], a); q[a][t, 7] = np.sqrt(gvar) * gq; e[a][t, 7] = np.sqrt(gvar) * ge
            else:
                q[a][t, 7] = np.sqrt(v[0]) * qt; e[a][t, 7] = np.sqrt(v[0]) * et
            if gjr:
                gq, ge = t_qe(gjr['nu'], a); q[a][t, 11] = sigma * gq; e[a][t, 11] = sigma * ge
                fq, fe = empirical_qe(resid, a); q[a][t, 12] = sigma * fq; e[a][t, 12] = sigma * fe
            else:
                q[a][t, 11:] = q[a][t, 5]; e[a][t, 11:] = e[a][t, 5]
        if resid is not None:
            resid = np.r_[resid, y[i] / sigma][-1000:]
        if gjr:
            h = gjr['omega'] + gjr['alpha[1]'] * y[i] ** 2 + gjr['gamma[1]'] * y[i] ** 2 * (y[i] < 0) + gjr['beta[1]'] * h
        v = (1 - rates) * v + rates * y[i] ** 2
    return q, e, log


def run_d1(y, q, e, alpha, gamma):
    """Protocol D1: log-multiplicative online updates; ES floored at the calibrated VaR."""
    n = len(y); lq = np.zeros(n + 1); le = np.zeros(n + 1)
    qc = np.empty(n); ec = np.empty(n); floored = np.zeros(n, bool)
    for t in range(n):
        qc[t] = np.exp(lq[t]) * q[t]
        cand = np.exp(le[t]) * e[t]
        floored[t] = cand > qc[t]
        ec[t] = min(cand, qc[t])
        hit = float(y[t] < qc[t])
        lq[t + 1] = lq[t] + gamma * (hit - alpha)
        le[t + 1] = le[t] + gamma * (hit * abs(y[t]) / abs(ec[t]) - alpha)
    return qc, ec, {'log_cq': lq, 'log_ce': le, 'floored': floored}


def s1_coefficients(y, q, e, alpha):
    """Closed-form minimiser of summed FZ0 over (c_q, c_e) for q~ = c_q q, e~ = c_e e.

    With r = q/e and k = y/q, the optimal VaR multiplier is the r-weighted (1-alpha)
    quantile of k, and the ES multiplier is mean(r * (c_q + (k - c_q)_+ / alpha)).
    """
    r = q / e; k = y / q
    order = np.argsort(k, kind='stable'); cw = np.cumsum(r[order]) / r.sum()
    cq = float(k[order][min(np.searchsorted(cw, 1 - alpha), len(k) - 1)])
    ce = float(np.mean(r * (cq + np.maximum(k - cq, 0) / alpha)))
    return cq, ce


def run_s1(y, q, e, alpha, refit):
    n = len(y); qc = np.full(n, np.nan); ec = np.full(n, np.nan)
    floored = np.zeros(n, bool); clipped = 0; cq = ce = None; first = S1_MIN
    for t in range(S1_MIN, n):
        if cq is None or (t - first) % refit == 0:
            lo = max(0, t - S1_WINDOW)
            cq, ce = s1_coefficients(y[lo:t], q[lo:t], e[lo:t], alpha)
            raw = (cq, ce); cq, ce = (float(np.clip(c, *COEF_BOX)) for c in raw)
            clipped += int(raw != (cq, ce))
        qc[t] = cq * q[t]; cand = ce * e[t]; floored[t] = cand > qc[t]; ec[t] = min(cand, qc[t])
    return qc, ec, {'floored': floored, 'clipped_fits': clipped}


def run_ye(y, q, e, alpha, scaled):
    """Ye et al. (2026) eq. (7): projected update of one parallel inflation on [0, radius].

    scaled=True divides loss (4) by (1 - tau), i.e. a = b = 1 with budget 2 * alpha, which
    matches the realised risk of 0.050 in their Table A4. scaled=False uses Table 6 literally.
    """
    n = len(y); lam = np.zeros(n + 1); qc = np.empty(n); ec = np.empty(n); xi = np.zeros(n)
    gap = np.maximum(q - e, YE['gap_floor'])
    a, b, budget = (1., 1., 2 * alpha) if scaled else (YE['a'], YE['b'], YE['budget'])
    for t in range(n):
        qc[t] = q[t] - lam[t] * gap[t]; ec[t] = e[t] - lam[t] * gap[t]
        loss = a * float(y[t] < qc[t]) + b * min(max(qc[t] - y[t], 0.) / gap[t], YE['cap'])
        raw = lam[t] + YE['step'] * (loss - budget)
        lam[t + 1] = min(max(raw, 0.), YE['radius']); xi[t] = raw - lam[t + 1]
    return qc, ec, {'lambda': lam, 'saturation': xi}


def block_ci(d, rng):
    n = len(d); nb = -(-n // BLOCK)
    starts = rng.integers(0, n, size=(BOOT, nb))
    idx = ((starts[:, :, None] + np.arange(BLOCK)) % n).reshape(BOOT, -1)[:, :n]
    means = d[idx].mean(axis=1)
    return float(np.quantile(means, .025)), float(np.quantile(means, .975))


def evaluate(y, qc, ec, alpha):
    hit = y < qc
    return {'fz_mean': float(np.mean(fz0(y, qc, ec, alpha))), 'exceed_rate': float(hit.mean()),
            'z2': float(1 - np.sum(hit * np.abs(y) / np.abs(ec)) / (len(y) * alpha)),
            'mean_abs_var': float(np.mean(-qc)), 'mean_abs_es': float(np.mean(-ec)),
            'var_daily_change': float(np.mean(np.abs(np.diff(np.log(-qc)))))}


def legal(qc, ec, alpha, y):
    return bool(np.all(np.isfinite(qc)) and np.all(np.isfinite(ec)) and np.all(qc < 0) and np.all(ec <= qc)
                and np.all(np.isfinite(fz0(y, qc, ec, alpha))))


def proposition_check(y, q, alpha, gamma, info, qc, ec):
    """Verify Proposition 1 (ii)-(iii) on the full D1 run with realised constants."""
    T = len(y); R = float(np.max(np.abs(y) / np.abs(q)))
    cmin = float(np.exp(info['log_cq'][:T].min()))
    hit = y < qc
    rate = float(hit.mean()); z2 = float(1 - np.sum(hit * np.abs(y) / np.abs(ec)) / (T * alpha))
    b2 = max(0., np.log(R) + gamma * (1 - alpha)) / (gamma * T)
    b3 = max(0., np.log(R / alpha) + gamma * R / cmin) / (alpha * gamma * T)
    return {'T': T, 'R': R, 'c_min': cmin, 'exceed_rate': rate, 'bound_ii': alpha + b2,
            'holds_ii': rate <= alpha + b2 + 1e-12, 'z2': z2, 'bound_iii': -b3, 'holds_iii': z2 >= -b3 - 1e-12,
            'identity_var_gap': float(abs((hit - alpha).sum() * gamma - info['log_cq'][T])),
            'max_log_cq': float(info['log_cq'].max()), 'min_log_cq': float(info['log_cq'].min()),
            'max_log_ce': float(info['log_ce'].max()), 'min_log_ce': float(info['log_ce'].min())}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    started = time.time(); rng = np.random.default_rng(SEED)
    rows, checks, validation, daily, fits = [], [], {}, [], []
    inputs = {}
    for asset in ASSETS:
        bpath = RUN / 'stage4' / f'pool_empirical_base_{asset}.npz'
        fpath = RUN / 'stage4' / f'pool_empirical_forecasts_{asset}.npz'
        inputs.update({str(p.relative_to(RUN)): sha256(p) for p in (bpath, fpath, PRICES[asset])})
        base = np.load(bpath, allow_pickle=False); fc = np.load(fpath, allow_pickle=False)
        dates = base['dates']; y = base['y']
        print(asset, 'rebuilding pool', flush=True)
        q_r, e_r, log = rebuild_pool(asset, base)
        fits += [{'market': asset, **r} for r in log]
        stored_q = base['q'][:, POOL]; stored_e = base['e'][:, POOL]
        diff = {NAMES[j]: float(max(np.max(np.abs(q_r[0.01][:, j] - base['q'][:, j])),
                                    np.max(np.abs(e_r[0.01][:, j] - base['e'][:, j])))) for j in POOL}
        A0_stored = (stored_q.mean(1), stored_e.mean(1))
        combo_t = fc['t_eval']; pools = list(fc['pool_names']); methods = list(fc['method_names'])
        pi = pools.index('expanded10')
        eq_q = fc['forecast_q'][pi, :, methods.index('EqualAll')]; eq_e = fc['forecast_e'][pi, :, methods.index('EqualAll')]
        validation[asset] = {'rebuilt_vs_stored_99_max_abs_diff': diff,
                             'A0_vs_stored_EqualAll_max_abs_diff': float(max(np.max(np.abs(A0_stored[0][combo_t] - eq_q)),
                                                                             np.max(np.abs(A0_stored[1][combo_t] - eq_e))))}
        ev = dates >= EVAL_START
        for alpha in ALPHAS:
            if alpha == 0.01:
                q0, e0 = A0_stored            # authoritative stored 99% forecasts
            else:
                q0, e0 = q_r[alpha][:, POOL].mean(1), e_r[alpha][:, POOL].mean(1)
            arms = {'A0': (q0, e0, {})}
            for g in GAMMAS:
                qc, ec, info = run_d1(y, q0, e0, alpha, g)
                arms[f'A2_g{g}'] = (qc, ec, info)
                checks.append({'market': asset, 'alpha': alpha, 'arm': f'A2_g{g}', 'gamma': g,
                               **proposition_check(y, q0, alpha, g, info, qc, ec)})
            for name, refit in (('A1d', 1), ('A1', S1_REFIT)):
                arms[name] = run_s1(y, q0, e0, alpha, refit)
            arms['A3_scaled'] = run_ye(y, q0, e0, alpha, scaled=True)
            if alpha == 0.025:
                arms['A3_literal'] = run_ye(y, q0, e0, alpha, scaled=False)
            if alpha == 0.01:
                mi = methods.index(MCS_METHOD)
                cq = np.full(len(y), np.nan); ce = np.full(len(y), np.nan)
                cq[combo_t] = fc['forecast_q'][pi, :, mi]; ce[combo_t] = fc['forecast_e'][pi, :, mi]
                arms['C0'] = (cq, ce, {})
                for g in GAMMAS:
                    qc = np.full(len(y), np.nan); ec = np.full(len(y), np.nan)
                    sub_q, sub_e, _ = run_d1(y[combo_t], cq[combo_t], ce[combo_t], alpha, g)
                    qc[combo_t] = sub_q; ec[combo_t] = sub_e
                    arms[f'C2_g{g}'] = (qc, ec, {})
            ya = y[ev]; base_fz = fz0(ya, q0[ev], e0[ev], alpha)
            for name, (qc, ec, info) in arms.items():
                qa, ea = qc[ev], ec[ev]
                row = {'market': asset, 'alpha': alpha, 'arm': name, 'n_eval': int(ev.sum()),
                       'legal_eval': legal(qa, ea, alpha, ya), **evaluate(ya, qa, ea, alpha)}
                d = fz0(ya, qa, ea, alpha) - base_fz
                row['dfz_vs_A0'] = float(d.mean())
                row['ci_low'], row['ci_high'] = block_ci(d, rng) if name != 'A0' else (0., 0.)
                row['floor_triggers_eval'] = int(info['floored'][ev].sum()) if 'floored' in info else None
                row['s1_clipped_fits'] = info.get('clipped_fits')
                if 'log_cq' in info:
                    row['c_q_min_run'] = float(np.exp(info['log_cq']).min()); row['c_q_max_run'] = float(np.exp(info['log_cq']).max())
                    row['c_e_min_run'] = float(np.exp(info['log_ce']).min()); row['c_e_max_run'] = float(np.exp(info['log_ce']).max())
                    row['legal_full_run'] = legal(qc, ec, alpha, y)
                if 'lambda' in info:
                    lam = info['lambda'][:-1]
                    row['ye_lambda_mean_eval'] = float(lam[ev].mean())
                    row['ye_upper_hits'] = int(np.sum(np.isclose(info['lambda'][1:], YE['radius'])))
                    row['ye_lower_hits'] = int(np.sum(info['lambda'][1:] == 0.))
                    row['ye_mean_abs_saturation'] = float(np.mean(np.abs(info['saturation'])))
                rows.append(row)
                daily.append(pd.DataFrame({'market': asset, 'alpha': alpha, 'arm': name, 'date': dates[ev],
                                           'y': ya, 'q': qa, 'e': ea, 'fz0': fz0(ya, qa, ea, alpha)}))
    summary = pd.DataFrame(rows)
    gates = {}
    for alpha in ALPHAS:
        s = summary[(summary.alpha == alpha) & summary.arm.str.startswith('A2_g')]
        avg = s.groupby('arm').dfz_vs_A0.mean()
        best = avg.idxmin()
        legal_ok = bool(s.legal_eval.all() and s.legal_full_run.all())
        gates[str(alpha)] = {'two_market_avg_dfz_by_gamma': avg.to_dict(), 'selected_arm_on_dev': best,
                             'selected_avg_dfz': float(avg[best]), 'gammas_not_worse': int((avg <= 0).sum()),
                             'a_legality': legal_ok, 'b_d1_not_worse_than_A0': bool(avg[best] <= 0),
                             'pass': bool(legal_ok and avg[best] <= 0),
                             'note': 'gamma selected on the same explored data; optimistic by construction'}
    gates['primary_level'] = '0.025'
    gates['continue'] = gates['0.025']['pass']
    summary.to_csv(HERE / 'quickcheck_summary.csv', index=False)
    pd.concat(daily).to_csv(HERE / 'quickcheck_daily.csv', index=False)
    pd.DataFrame(checks).to_csv(HERE / 'quickcheck_proposition_checks.csv', index=False)
    pd.DataFrame(fits).to_csv(HERE / 'quickcheck_refits.csv', index=False)
    (HERE / 'quickcheck_validation.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
    (HERE / 'quickcheck_gate.json').write_text(json.dumps(gates, indent=2), encoding='utf-8')
    manifest = {'role': 'explored development quick check; not confirmatory', 'eval_start': EVAL_START,
                'alphas': ALPHAS, 'gammas': GAMMAS, 'pool': [NAMES[j] for j in POOL], 'mcs_method': MCS_METHOD,
                's1': {'window': S1_WINDOW, 'min_window': S1_MIN, 'refit_A1': S1_REFIT, 'coef_box': COEF_BOX},
                'ye': YE, 'bootstrap': {'block': BLOCK, 'B': BOOT, 'seed': SEED, 'type': 'circular, per market'},
                'inputs_sha256': inputs, 'script_sha256': sha256(__file__), 'seconds': time.time() - started,
                'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                             'scipy': scipy.__version__, 'arch': arch.__version__}}
    (HERE / 'quickcheck_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(gates, indent=2))


if __name__ == '__main__':
    sys.exit(main())
