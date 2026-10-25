"""Freeze parameters taken from explored development data: Politis-White block lengths.

Section 5 of the protocol fixes the main bootstrap block length at the Politis-White automatic
choice on development data. The confirmation sets are equity, so this uses the saved round-2 and
round-3 daily scores of the three development equity indices; nothing is re-estimated here and no
confirmation file is read.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
EQUITY = ['SP500', 'DJIA', 'NASDAQCOM']
CONTRASTS = {'H1': ('AGG_eta2.0', 'A0'), 'H2': ('AGG_eta2.0', 'A1d'), 'H3': ('AGG_eta2.0', 'Ye_step0.01')}


def pw_block_sb(x):
    """np::b.star stationary-bootstrap length (Politis-White 2004, Patton-Politis-White 2009).

    Same lag selection and flat-top kernel as pilot5/pilot.bstar, which ports the circular-block
    column; the stationary bootstrap uses D_SB = 2 g(0)^2 instead of (4/3) g(0)^2.
    """
    x = np.asarray(x, float); n = len(x); kn = max(5, math.ceil(math.log10(n)))
    mm = math.ceil(math.sqrt(n)) + kn; cap = math.ceil(min(3 * math.sqrt(n), n / 3))
    x = x - x.mean(); cov = np.array([(x[:n - k] * x[k:]).sum() / n for k in range(mm + 1)])
    rho = cov[1:] / cov[0]; crit = norm.ppf(.975) * math.sqrt(math.log10(n) / n)
    ins = np.abs(rho) < crit
    runs = [k + 1 for k in range(mm - kn + 1) if ins[k:k + kn].all()]
    sig = np.flatnonzero(np.abs(rho) > crit) + 1
    mh = runs[0] if runs else (int(sig[-1]) if len(sig) else 1)
    M = min(2 * mh, mm); ks = np.arange(1, M + 1); lam = np.where(ks / M < .5, 1, 2 * (1 - ks / M))
    g = 2 * np.sum(lam * ks * cov[1:M + 1]); lr = cov[0] + 2 * np.sum(lam * cov[1:M + 1])
    return float(min(cap, np.cbrt(2 * g * g / (2 * lr ** 2)) * np.cbrt(n)))


def main():
    r3 = pd.read_csv(RUN / 'devcheck_round3' / 'devcheck3_daily.csv')
    r2 = pd.read_csv(RUN / 'devcheck_round2' / 'devcheck2_daily.csv')
    a0 = r3[r3.arm == 'A0'].merge(r2[r2.arm == 'A0'], on=['market', 'alpha', 'date'])
    a0_gap = float((a0.fz0_x - a0.fz0_y).abs().max())
    fz = pd.concat([r3[r3.arm.isin(['A0', 'AGG_eta2.0', 'Ye_step0.01'])], r2[r2.arm == 'A1d']])
    fz = fz[fz.market.isin(EQUITY)]
    wide = fz.pivot_table(index=['alpha', 'date'], columns=['arm', 'market'], values='fz0')
    blocks = {}
    for alpha in (0.025, 0.01):
        w = wide.loc[alpha]
        for h, (a, b) in CONTRASTS.items():
            d = (w[a] - w[b])[EQUITY].dropna().mean(axis=1)
            blocks[f'{h}@{alpha}'] = {'block': round(pw_block_sb(d.to_numpy()), 2), 'days': len(d),
                                       'first': d.index[0], 'last': d.index[-1]}
    out = {'source': 'devcheck3_daily.csv (A0, AGG_eta2.0, Ye_step0.01) and devcheck2_daily.csv (A1d); '
                     'equal-weight average of SP500, DJIA, NASDAQCOM on their common dates',
           'a0_round2_vs_round3_max_abs_gap': a0_gap, 'block_lengths': blocks}
    (HERE / 'freeze_params.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    sys.exit(main())
