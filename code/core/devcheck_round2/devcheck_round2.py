"""D1 development round 2: ES coefficient updated only on breach days (Z1 target).

Implements the round-2 plan written into section 7 of the research protocol
(see provenance/Prespecified_Design.md) before this run. Same five explored
series, evaluation spans and gate statistic as round 1 (../devcheck_d1v2), which is reused
for the pool rebuild, reference arms and scoring and is not modified.
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
sys.path.insert(0, str(RUN / 'devcheck_d1v2'))
import devcheck_d1v2 as r1  # noqa: E402
v1 = r1.v1

FLOORS = {'L05': float(np.log(0.5)), 'L1': 0.0}
CAP = 3.0
SEED = 20261026


def run_d1z1(y, q, e, alpha, half_life, floor, cap=CAP):
    """Round-2 D1: VaR update as in round 1; the ES coefficient moves only on breach days."""
    gq, ge = r1.steps(alpha, half_life)
    n = len(y); u = np.zeros(n + 1); v = np.zeros(n + 1); dq = np.zeros(n); de = np.zeros(n)
    qc = np.empty(n); ec = np.empty(n); floored = np.zeros(n, bool); g = np.zeros(n)
    for t in range(n):
        qc[t] = np.exp(u[t]) * q[t]
        cand = np.exp(v[t]) * e[t]
        floored[t] = cand > qc[t]
        ec[t] = min(cand, qc[t])
        hit = float(y[t] < qc[t])
        g[t] = hit * (min(abs(y[t]) / abs(ec[t]), cap) - 1.)
        raw = u[t] + gq * (hit - alpha); u[t + 1] = max(floor, raw); dq[t] = u[t + 1] - raw
        raw = v[t] + ge * g[t]; v[t + 1] = max(floor, raw); de[t] = v[t + 1] - raw
    return qc, ec, {'log_cq': u, 'log_ce': v, 'dq': dq, 'de': de, 'g': g, 'floored': floored,
                    'gamma_q': gq, 'gamma_e': ge}


def z1(y, qc, ec):
    hit = y < qc
    return float(1 - np.mean(np.abs(y[hit]) / np.abs(ec[hit]))) if hit.any() else float('nan')


def proposition_check(y, q, alpha, floor, info, qc, ec):
    """Proposition 1 (ii) and Proposition 2 on the full run with realised constants."""
    T = len(y); gq, ge = info['gamma_q'], info['gamma_e']
    R = float(np.max(np.abs(y) / np.abs(q))); G = min(CAP, R * np.exp(-floor))
    hit = y < qc; N = int(hit.sum())
    Uq = max(0., np.log(R) + gq * (1 - alpha)); U1 = max(0., np.log(R) + ge * (G - 1))
    rate = float(hit.mean())
    z1cap = float(1 - np.sum(hit * np.minimum(np.abs(y) / np.abs(ec), CAP)) / N) if N else float('nan')
    return {'T': T, 'N': N, 'R': R, 'G': G, 'exceed_rate': rate, 'bound_ii': alpha + Uq / (gq * T),
            'holds_ii': rate <= alpha + Uq / (gq * T) + 1e-12, 'z1_capped': z1cap,
            'bound_z1': -U1 / (ge * N) if N else float('nan'),
            'holds_z1': bool(N == 0 or z1cap >= -U1 / (ge * N) - 1e-12),
            'identity_q_gap': float(abs(gq * (hit - alpha).sum() - (info['log_cq'][T] - info['dq'].sum()))),
            'identity_e_gap': float(abs(ge * info['g'].sum() - (info['log_ce'][T] - info['de'].sum()))),
            'floor_binds_q': int((info['dq'] > 0).sum()), 'floor_binds_e': int((info['de'] > 0).sum()),
            'c_q_range': [float(np.exp(info['log_cq'].min())), float(np.exp(info['log_cq'].max()))],
            'c_e_range': [float(np.exp(info['log_ce'].min())), float(np.exp(info['log_ce'].max()))]}


def main():
    started = time.time(); rng = np.random.default_rng(SEED)
    rows, checks, crisis, daily, refits, inputs = [], [], [], [], [], {}
    for asset, (klass, path) in r1.SERIES.items():
        v1.PRICES[asset] = path
        y_all, d_all = v1.load_returns(asset)
        stored = {'dates': d_all[1000:], 'y': y_all[1000:]}
        print(asset, 'rebuilding pool', len(stored['y']), 'days', flush=True)
        q_r, e_r, log = v1.rebuild_pool(asset, stored)
        refits += [{'market': asset, **r} for r in log]
        inputs[str(path.relative_to(RUN))] = v1.sha256(path)
        dates, y = stored['dates'], stored['y']
        ev = np.arange(len(y)) >= r1.EVAL_FROM
        for alpha in r1.ALPHAS:
            q0, e0 = q_r[alpha][:, v1.POOL].mean(1), e_r[alpha][:, v1.POOL].mean(1)
            arms = {'A0': (q0, e0, {})}
            for H in r1.HALF_LIVES:
                for tag, floor in FLOORS.items():
                    name = f'D1z1_H{H}_{tag}'
                    qc, ec, info = run_d1z1(y, q0, e0, alpha, H, floor)
                    arms[name] = (qc, ec, info)
                    checks.append({'market': asset, 'alpha': alpha, 'arm': name, 'half_life': H, 'floor': floor,
                                   'gamma_q': info['gamma_q'], 'gamma_e': info['gamma_e'],
                                   **proposition_check(y, q0, alpha, floor, info, qc, ec)})
            arms['D1v2_H1000_M3'] = r1.run_d1v2(y, q0, e0, alpha, 1000, 3.0)
            arms['A1d'] = v1.run_s1(y, q0, e0, alpha, 1)
            for step in (0.01, 0.05):
                arms[f'Ye_step{step}'] = r1.run_ye(y, q0, e0, alpha, step)
            crisis += [{'market': asset, 'class': klass, 'alpha': alpha, **r}
                       for r in r1.crisis_windows(dates, y, arms, alpha)]
            ya = y[ev]; base_fz = v1.fz0(ya, q0[ev], e0[ev], alpha)
            for name, (qc, ec, info) in arms.items():
                qa, ea = qc[ev], ec[ev]
                d = v1.fz0(ya, qa, ea, alpha) - base_fz
                row = {'market': asset, 'class': klass, 'alpha': alpha, 'arm': name, 'n_eval': int(ev.sum()),
                       'eval_first': dates[ev][0], 'eval_last': dates[ev][-1],
                       'legal_eval': v1.legal(qa, ea, alpha, ya), **v1.evaluate(ya, qa, ea, alpha),
                       'z1': z1(ya, qa, ea), 'dfz_vs_A0': float(d.mean())}
                row['ci_low'], row['ci_high'] = v1.block_ci(d, rng) if name != 'A0' else (0., 0.)
                if 'floored' in info:
                    row['floor_triggers_eval'] = int(info['floored'][ev].sum())
                if 'log_cq' in info:
                    row['legal_full_run'] = v1.legal(qc, ec, alpha, y)
                rows.append(row)
                daily.append(pd.DataFrame({'market': asset, 'alpha': alpha, 'arm': name, 'date': dates[ev],
                                           'y': ya, 'q': qa, 'e': ea, 'fz0': v1.fz0(ya, qa, ea, alpha)}))
    summary = pd.DataFrame(rows)
    by_class = summary.groupby(['alpha', 'arm', 'class']).dfz_vs_A0.mean().unstack('class')
    balanced = by_class.mean(axis=1).rename('class_balanced_dfz').reset_index()
    gates = {}
    for alpha in r1.ALPHAS:
        b = balanced[balanced.alpha == alpha].set_index('arm').class_balanced_dfz
        d1 = b[b.index.str.startswith('D1z1')]
        best = d1.idxmin()
        d1_rows = summary[(summary.alpha == alpha) & summary.arm.str.startswith('D1z1')]
        legal_ok = bool(d1_rows.legal_eval.all() and d1_rows.legal_full_run.all())
        gates[str(alpha)] = {'class_balanced_dfz': b.to_dict(), 'selected_d1': best, 'selected_d1_dfz': float(d1[best]),
                             'd1_configs_not_worse': int((d1 <= 0).sum()),
                             'floor1_minus_floor05_by_H': {H: float(b[f'D1z1_H{H}_L1'] - b[f'D1z1_H{H}_L05'])
                                                           for H in r1.HALF_LIVES},
                             'a_legality': legal_ok, 'b_d1_not_worse_than_A0': bool(d1[best] <= 0),
                             'pass': bool(legal_ok and d1[best] <= 0),
                             'note': 'configs selected on the same explored data; optimistic by construction'}
    gates['primary_level'] = '0.025'; gates['round'] = 2; gates['continue'] = gates['0.025']['pass']
    summary.to_csv(HERE / 'devcheck2_summary.csv', index=False)
    balanced.to_csv(HERE / 'devcheck2_class_balanced.csv', index=False)
    pd.concat(daily).to_csv(HERE / 'devcheck2_daily.csv', index=False)
    pd.DataFrame(checks).to_csv(HERE / 'devcheck2_proposition_checks.csv', index=False)
    pd.DataFrame(crisis).to_csv(HERE / 'devcheck2_crisis_windows.csv', index=False)
    pd.DataFrame(refits).to_csv(HERE / 'devcheck2_refits.csv', index=False)
    (HERE / 'devcheck2_gate.json').write_text(json.dumps(gates, indent=2), encoding='utf-8')
    manifest = {'role': 'explored development round 2 for D1; not confirmatory',
                'change_from_round1': 'ES coefficient updated only on breach days towards a capped tail ratio of 1 (Z1)',
                'floors': FLOORS, 'cap': CAP, 'half_lives': r1.HALF_LIVES, 'kappa': r1.KAPPA,
                'series': {k: c for k, (c, _) in r1.SERIES.items()}, 'eval_from_index': r1.EVAL_FROM,
                'gate_statistic': 'mean dFZ0 vs A0 within asset class, then equal weight across classes',
                'inputs_sha256': inputs, 'script_sha256': v1.sha256(__file__),
                'round1_script_sha256': v1.sha256(RUN / 'devcheck_d1v2' / 'devcheck_d1v2.py'),
                'v1_script_sha256': v1.sha256(RUN / 'quickcheck_d1' / 'quickcheck_d1.py'),
                'seconds': time.time() - started,
                'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                             'scipy': scipy.__version__, 'arch': arch.__version__}}
    (HERE / 'devcheck2_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(gates, indent=2))


if __name__ == '__main__':
    sys.exit(main())
