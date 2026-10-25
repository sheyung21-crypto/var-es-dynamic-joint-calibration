"""D1 version 2, development round 1, on all explored daily series.

Implements the revised D1 of the research protocol
(see provenance/Prespecified_Design.md): lower-bounded log multipliers,
separate VaR/ES steps set by half-life, optional cap on the ES update ratio. Every series
here was explored in earlier stages, so nothing is confirmatory. The version-1 quick check
(../quickcheck_d1) is reused for the pool rebuild, S1 and scoring, and is not modified.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'; os.environ['OMP_NUM_THREADS'] = '1'
import json, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
import arch

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
sys.path.insert(0, str(RUN / 'quickcheck_d1'))
import quickcheck_d1 as v1  # noqa: E402

SERIES = {'SP500': ('equity', RUN / 'deepening5' / 'external_data' / 'SP500.csv'),
          'DJIA': ('equity', RUN / 'deepening5' / 'external_data' / 'DJIA.csv'),
          'NASDAQCOM': ('equity', RUN / 'deepening5' / 'external_data' / 'NASDAQCOM.csv'),
          'DEXUSEU': ('fx', RUN / 'stage3' / 'fx_data' / 'DEXUSEU.csv'),
          'DEXJPUS': ('fx', RUN / 'stage3' / 'fx_data' / 'DEXJPUS.csv')}
ALPHAS = (0.025, 0.01)
HALF_LIVES = (125, 250, 500, 1000)
CAPS = (3.0, np.inf)
KAPPA = 4.0                    # tail elasticity |q| f(q) / alpha used to map a half-life to the VaR step
FLOOR = float(np.log(0.5))     # lower bound of both log multipliers
YE_STEPS = (0.01, 0.025, 0.05, 0.1)   # the step grid of Ye et al. (2026), Table A4
EVAL_FROM = 250                # first index where every arm, S1 included, is available
SHOCKS = ['1987-10-19', '1998-08-17', '2001-09-17', '2008-09-15', '2011-08-08', '2015-08-24', '2020-02-24']
CRISIS_DAYS = 60
SEED = 20261025


def steps(alpha, half_life):
    """ES step from the exact local half-life; VaR step slowed by the tail elasticity."""
    ge = np.log(2) / (alpha * half_life)
    return ge / KAPPA, ge


def run_d1v2(y, q, e, alpha, half_life, cap):
    gq, ge = steps(alpha, half_life)
    n = len(y); u = np.zeros(n + 1); v = np.zeros(n + 1); dq = np.zeros(n); de = np.zeros(n)
    qc = np.empty(n); ec = np.empty(n); floored = np.zeros(n, bool); g = np.zeros(n)
    for t in range(n):
        qc[t] = np.exp(u[t]) * q[t]
        cand = np.exp(v[t]) * e[t]
        floored[t] = cand > qc[t]
        ec[t] = min(cand, qc[t])
        hit = float(y[t] < qc[t])
        g[t] = hit * min(abs(y[t]) / abs(ec[t]), cap) - alpha
        raw = u[t] + gq * (hit - alpha); u[t + 1] = max(FLOOR, raw); dq[t] = u[t + 1] - raw
        raw = v[t] + ge * g[t]; v[t + 1] = max(FLOOR, raw); de[t] = v[t + 1] - raw
    return qc, ec, {'log_cq': u, 'log_ce': v, 'dq': dq, 'de': de, 'g': g, 'floored': floored,
                    'gamma_q': gq, 'gamma_e': ge}


def run_ye(y, q, e, alpha, step):
    """Ye et al. eq. (7) with the scale-consistent loss (a = b = 1, budget 2 * alpha)."""
    n = len(y); lam = np.zeros(n + 1); qc = np.empty(n); ec = np.empty(n); xi = np.zeros(n)
    gap = np.maximum(q - e, v1.YE['gap_floor'])
    for t in range(n):
        qc[t] = q[t] - lam[t] * gap[t]; ec[t] = e[t] - lam[t] * gap[t]
        loss = float(y[t] < qc[t]) + min(max(qc[t] - y[t], 0.) / gap[t], v1.YE['cap'])
        raw = lam[t] + step * (loss - 2 * alpha)
        lam[t + 1] = min(max(raw, 0.), v1.YE['radius']); xi[t] = raw - lam[t + 1]
    return qc, ec, {'lambda': lam, 'saturation': xi}


def proposition_check(y, q, alpha, cap, info, qc, ec):
    """Proposition 1' with lower projections: realised constants, both one-sided bounds."""
    T = len(y); gq, ge = info['gamma_q'], info['gamma_e']
    R = float(np.max(np.abs(y) / np.abs(q))); G = min(cap, R * np.exp(-FLOOR))
    hit = y < qc
    Uq = max(0., FLOOR, np.log(R) + gq * (1 - alpha))
    Ue = max(0., FLOOR, np.log(R / alpha) + ge * G)
    rate = float(hit.mean())
    z2cap = float(1 - np.sum(hit * np.minimum(np.abs(y) / np.abs(ec), cap)) / (T * alpha))
    return {'T': T, 'R': R, 'G': G, 'exceed_rate': rate, 'bound_ii': alpha + Uq / (gq * T),
            'holds_ii': rate <= alpha + Uq / (gq * T) + 1e-12, 'z2_capped': z2cap,
            'bound_iii': -Ue / (alpha * ge * T), 'holds_iii': z2cap >= -Ue / (alpha * ge * T) - 1e-12,
            'identity_q_gap': float(abs(gq * (hit - alpha).sum() - (info['log_cq'][T] - info['dq'].sum()))),
            'identity_e_gap': float(abs(ge * info['g'].sum() - (info['log_ce'][T] - info['de'].sum()))),
            'floor_binds_q': int((info['dq'] > 0).sum()), 'floor_binds_e': int((info['de'] > 0).sum()),
            'sum_dq': float(info['dq'].sum()), 'sum_de': float(info['de'].sum()),
            'c_q_range': [float(np.exp(info['log_cq'].min())), float(np.exp(info['log_cq'].max()))],
            'c_e_range': [float(np.exp(info['log_ce'].min())), float(np.exp(info['log_ce'].max()))]}


def crisis_windows(dates, y, arms, alpha):
    rows = []
    for shock in SHOCKS:
        start = int(np.searchsorted(dates, shock))
        if start == 0 or start + CRISIS_DAYS > len(dates):
            continue
        w = slice(start, start + CRISIS_DAYS)
        base = v1.fz0(y[w], arms['A0'][0][w], arms['A0'][1][w], alpha)
        for name, (qc, ec, _) in arms.items():
            if not np.all(np.isfinite(qc[w])):
                continue
            rows.append({'shock': shock, 'arm': name, 'first_date': dates[start],
                         'exceed_rate': float(np.mean(y[w] < qc[w])),
                         'dfz_vs_A0': float(np.mean(v1.fz0(y[w], qc[w], ec[w], alpha) - base))})
    return rows


def main():
    started = time.time(); rng = np.random.default_rng(SEED)
    rows, checks, crisis, daily, refits, inputs = [], [], [], [], [], {}
    for asset, (klass, path) in SERIES.items():
        v1.PRICES[asset] = path
        y_all, d_all = v1.load_returns(asset)
        stored = {'dates': d_all[1000:], 'y': y_all[1000:]}
        print(asset, 'rebuilding pool', len(stored['y']), 'days', flush=True)
        q_r, e_r, log = v1.rebuild_pool(asset, stored)
        refits += [{'market': asset, **r} for r in log]
        inputs[str(path.relative_to(RUN))] = v1.sha256(path)
        dates, y = stored['dates'], stored['y']
        ev = np.arange(len(y)) >= EVAL_FROM
        for alpha in ALPHAS:
            q0, e0 = q_r[alpha][:, v1.POOL].mean(1), e_r[alpha][:, v1.POOL].mean(1)
            arms = {'A0': (q0, e0, {})}
            for H in HALF_LIVES:
                for cap in CAPS:
                    name = f'D1v2_H{H}_M{"inf" if np.isinf(cap) else int(cap)}'
                    qc, ec, info = run_d1v2(y, q0, e0, alpha, H, cap)
                    arms[name] = (qc, ec, info)
                    checks.append({'market': asset, 'alpha': alpha, 'arm': name, 'half_life': H, 'cap': cap,
                                   'gamma_q': info['gamma_q'], 'gamma_e': info['gamma_e'],
                                   **proposition_check(y, q0, alpha, cap, info, qc, ec)})
            for name, refit in (('A1d', 1), ('A1', v1.S1_REFIT)):
                arms[name] = v1.run_s1(y, q0, e0, alpha, refit)
            for step in YE_STEPS:
                arms[f'Ye_step{step}'] = run_ye(y, q0, e0, alpha, step)
            crisis += [{'market': asset, 'class': klass, 'alpha': alpha, **r} for r in crisis_windows(dates, y, arms, alpha)]
            ya = y[ev]; base_fz = v1.fz0(ya, q0[ev], e0[ev], alpha)
            for name, (qc, ec, info) in arms.items():
                qa, ea = qc[ev], ec[ev]
                d = v1.fz0(ya, qa, ea, alpha) - base_fz
                row = {'market': asset, 'class': klass, 'alpha': alpha, 'arm': name, 'n_eval': int(ev.sum()),
                       'eval_first': dates[ev][0], 'eval_last': dates[ev][-1],
                       'legal_eval': v1.legal(qa, ea, alpha, ya), **v1.evaluate(ya, qa, ea, alpha),
                       'dfz_vs_A0': float(d.mean())}
                row['ci_low'], row['ci_high'] = v1.block_ci(d, rng) if name != 'A0' else (0., 0.)
                if 'floored' in info:
                    row['floor_triggers_eval'] = int(info['floored'][ev].sum())
                if 'log_cq' in info:
                    row['legal_full_run'] = v1.legal(qc, ec, alpha, y)
                if 'lambda' in info:
                    row['ye_lambda_mean_eval'] = float(info['lambda'][:-1][ev].mean())
                rows.append(row)
                daily.append(pd.DataFrame({'market': asset, 'alpha': alpha, 'arm': name, 'date': dates[ev],
                                           'y': ya, 'q': qa, 'e': ea, 'fz0': v1.fz0(ya, qa, ea, alpha)}))
    summary = pd.DataFrame(rows)
    by_class = summary.groupby(['alpha', 'arm', 'class']).dfz_vs_A0.mean().unstack('class')
    balanced = by_class.mean(axis=1).rename('class_balanced_dfz').reset_index()
    gates = {}
    for alpha in ALPHAS:
        b = balanced[balanced.alpha == alpha].set_index('arm').class_balanced_dfz
        d1 = b[b.index.str.startswith('D1v2')]; ye = b[b.index.str.startswith('Ye')]
        best = d1.idxmin(); best_ye = ye.idxmin()
        d1_rows = summary[(summary.alpha == alpha) & summary.arm.str.startswith('D1v2')]
        legal_ok = bool(d1_rows.legal_eval.all() and d1_rows.legal_full_run.all())
        gates[str(alpha)] = {'class_balanced_dfz': b.to_dict(), 'selected_d1': best, 'selected_d1_dfz': float(d1[best]),
                             'd1_configs_not_worse': int((d1 <= 0).sum()), 'selected_ye': best_ye,
                             'selected_ye_dfz': float(ye[best_ye]), 'S1_daily_dfz': float(b['A1d']),
                             'a_legality': legal_ok, 'b_d1_not_worse_than_A0': bool(d1[best] <= 0),
                             'pass': bool(legal_ok and d1[best] <= 0),
                             'note': 'configs selected on the same explored data; optimistic by construction'}
    gates['primary_level'] = '0.025'; gates['round'] = 1; gates['continue'] = gates['0.025']['pass']
    summary.to_csv(HERE / 'devcheck_summary.csv', index=False)
    balanced.to_csv(HERE / 'devcheck_class_balanced.csv', index=False)
    pd.concat(daily).to_csv(HERE / 'devcheck_daily.csv', index=False)
    pd.DataFrame(checks).to_csv(HERE / 'devcheck_proposition_checks.csv', index=False)
    pd.DataFrame(crisis).to_csv(HERE / 'devcheck_crisis_windows.csv', index=False)
    pd.DataFrame(refits).to_csv(HERE / 'devcheck_refits.csv', index=False)
    (HERE / 'devcheck_gate.json').write_text(json.dumps(gates, indent=2), encoding='utf-8')
    manifest = {'role': 'explored development round 1 for D1 version 2; not confirmatory',
                'series': {k: c for k, (c, _) in SERIES.items()}, 'eval_from_index': EVAL_FROM, 'alphas': ALPHAS,
                'half_lives': HALF_LIVES, 'caps': [str(c) for c in CAPS], 'kappa': KAPPA, 'floor': FLOOR,
                'ye_steps': YE_STEPS, 'shocks': SHOCKS, 'crisis_days': CRISIS_DAYS,
                'gate_statistic': 'mean dFZ0 vs A0 within asset class, then equal weight across classes',
                'inputs_sha256': inputs, 'script_sha256': v1.sha256(__file__),
                'v1_script_sha256': v1.sha256(RUN / 'quickcheck_d1' / 'quickcheck_d1.py'),
                'seconds': time.time() - started,
                'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                             'scipy': scipy.__version__, 'arch': arch.__version__}}
    (HERE / 'devcheck_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(gates, indent=2))


if __name__ == '__main__':
    sys.exit(main())
