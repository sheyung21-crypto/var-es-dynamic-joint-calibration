"""D1 development round 3 (final): fixed-share exponential weights over four speeds.

Implements the round-3 plan written into section 7 of the research protocol
(see provenance/Prespecified_Design.md) before this run. The experts are the
round-2 trackers with the log-1 floor; the aggregation borrows the DtACI structure but is not
a faithful DtACI reproduction. Rounds 0-2 (../quickcheck_d1, ../devcheck_d1v2,
../devcheck_round2) are reused and not modified.
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
sys.path.insert(0, str(RUN / 'devcheck_round2'))
import devcheck_round2 as r2  # noqa: E402
r1, v1 = r2.r1, r2.v1

ETAS = (0.5, 2.0)
SHARE = 1 / 250
SEED = 20261027


def run_aggregate(y, experts, alpha, eta, share=SHARE):
    """Fixed-share exponential weights on daily expert FZ0; day-t weights use losses up to t-1."""
    Q = np.column_stack([qc for qc, _ in experts]); E = np.column_stack([ec for _, ec in experts])
    S = v1.fz0(y[:, None], Q, E, alpha)
    n, K = Q.shape; w = np.full(K, 1 / K); W = np.empty((n, K))
    for t in range(n):
        W[t] = w
        nw = w * np.exp(-eta * (S[t] - S[t].min())); nw /= nw.sum()
        w = (1 - share) * nw + share / K
    return np.einsum('tk,tk->t', W, Q), np.einsum('tk,tk->t', W, E), {'weights': W}


def main():
    started = time.time(); rng = np.random.default_rng(SEED)
    rows, crisis, daily, refits, weights, aggchecks, inputs = [], [], [], [], [], [], {}
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
            experts = []
            for H in r1.HALF_LIVES:
                qc, ec, info = r2.run_d1z1(y, q0, e0, alpha, H, 0.0)
                arms[f'D1z1_H{H}_L1'] = (qc, ec, info); experts.append((qc, ec))
            for eta in ETAS:
                qa, ea, info = run_aggregate(y, experts, alpha, eta)
                name = f'AGG_eta{eta}'
                arms[name] = (qa, ea, info)
                W = info['weights']
                aggchecks.append({'market': asset, 'alpha': alpha, 'arm': name,
                                  'weights_valid': bool(np.all(W >= 0) and np.allclose(W.sum(1), 1)),
                                  'never_looser_than_A0': bool(np.all(qa <= q0 + 1e-12) and np.all(ea <= e0 + 1e-12)),
                                  'legal_full_run': v1.legal(qa, ea, alpha, y)})
                segments = [('eval', ev)]
                for shock in r1.SHOCKS:
                    start = int(np.searchsorted(dates, shock))
                    if 0 < start and start + r1.CRISIS_DAYS <= len(dates):
                        mask = np.zeros(len(y), bool); mask[start:start + r1.CRISIS_DAYS] = True
                        segments.append((shock, mask))
                for seg, mask in segments:
                    weights.append({'market': asset, 'alpha': alpha, 'arm': name, 'segment': seg,
                                    **{f'w_H{H}': float(W[mask, k].mean()) for k, H in enumerate(r1.HALF_LIVES)}})
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
                       'z1': r2.z1(ya, qa, ea), 'dfz_vs_A0': float(d.mean())}
                row['ci_low'], row['ci_high'] = v1.block_ci(d, rng) if name != 'A0' else (0., 0.)
                rows.append(row)
                daily.append(pd.DataFrame({'market': asset, 'alpha': alpha, 'arm': name, 'date': dates[ev],
                                           'y': ya, 'q': qa, 'e': ea, 'fz0': v1.fz0(ya, qa, ea, alpha)}))
    summary = pd.DataFrame(rows); checks = pd.DataFrame(aggchecks)
    by_class = summary.groupby(['alpha', 'arm', 'class']).dfz_vs_A0.mean().unstack('class')
    balanced = by_class.mean(axis=1).rename('class_balanced_dfz').reset_index()
    gates = {}
    for alpha in r1.ALPHAS:
        b = balanced[balanced.alpha == alpha].set_index('arm').class_balanced_dfz
        agg = b[b.index.str.startswith('AGG')]
        best = agg.idxmin()
        ok_rows = summary[(summary.alpha == alpha) & summary.arm.str.startswith('AGG')]
        ok_checks = checks[checks.alpha == alpha]
        legal_ok = bool(ok_rows.legal_eval.all() and ok_checks[['weights_valid', 'never_looser_than_A0',
                                                                 'legal_full_run']].all().all())
        gates[str(alpha)] = {'class_balanced_dfz': b.to_dict(), 'selected': best, 'selected_dfz': float(agg[best]),
                             'configs_not_worse': int((agg <= 0).sum()), 'a_legality': legal_ok,
                             'b_not_worse_than_A0': bool(agg[best] <= 0), 'pass': bool(legal_ok and agg[best] <= 0),
                             'note': 'eta selected on the same explored data; optimistic by construction'}
    gates['primary_level'] = '0.025'; gates['round'] = 3; gates['continue'] = gates['0.025']['pass']
    summary.to_csv(HERE / 'devcheck3_summary.csv', index=False)
    balanced.to_csv(HERE / 'devcheck3_class_balanced.csv', index=False)
    pd.concat(daily).to_csv(HERE / 'devcheck3_daily.csv', index=False)
    checks.to_csv(HERE / 'devcheck3_aggregate_checks.csv', index=False)
    pd.DataFrame(weights).to_csv(HERE / 'devcheck3_weights.csv', index=False)
    pd.DataFrame(crisis).to_csv(HERE / 'devcheck3_crisis_windows.csv', index=False)
    pd.DataFrame(refits).to_csv(HERE / 'devcheck3_refits.csv', index=False)
    (HERE / 'devcheck3_gate.json').write_text(json.dumps(gates, indent=2), encoding='utf-8')
    manifest = {'role': 'explored development round 3 (final) for D1; not confirmatory',
                'change_from_round2': 'fixed-share exponential weights over the four log-1 trackers',
                'etas': ETAS, 'share': SHARE, 'experts': [f'D1z1_H{H}_L1' for H in r1.HALF_LIVES],
                'series': {k: c for k, (c, _) in r1.SERIES.items()}, 'eval_from_index': r1.EVAL_FROM,
                'gate_statistic': 'mean dFZ0 vs A0 within asset class, then equal weight across classes',
                'inputs_sha256': inputs, 'script_sha256': v1.sha256(__file__),
                'round2_script_sha256': v1.sha256(RUN / 'devcheck_round2' / 'devcheck_round2.py'),
                'round1_script_sha256': v1.sha256(RUN / 'devcheck_d1v2' / 'devcheck_d1v2.py'),
                'v1_script_sha256': v1.sha256(RUN / 'quickcheck_d1' / 'quickcheck_d1.py'),
                'seconds': time.time() - started,
                'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                             'scipy': scipy.__version__, 'arch': arch.__version__}}
    (HERE / 'devcheck3_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(gates, indent=2))


if __name__ == '__main__':
    sys.exit(main())
