"""Future-perturbation checks on copies of inputs; no change to empirical results."""
from pathlib import Path
import importlib.util
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('s2',ROOT/'code/pipeline/study2.py')
s2=importlib.util.module_from_spec(spec); spec.loader.exec_module(s2)
f=s2.frozen
z=np.load(ROOT/'outputs/reference/study2_run1/forecasts.npz',allow_pickle=False)
checks=[]

def compare(name,x,y):
    exact=bool(np.array_equal(x,y,equal_nan=True))
    valid=np.isfinite(x)&np.isfinite(y)
    gap=float(np.max(np.abs(x[valid]-y[valid]))) if valid.any() else 0.
    checks.append({'check':name,'elements':x.size,'exact':exact,'max_abs_error':gap,
                   'pass':bool(np.allclose(x,y,atol=1e-12,rtol=0,equal_nan=True))})

# Refit a deliberately shortened history, perturbing only returns from index 2100 onward.
# The forecast at index 2100 must still equal the original complete-history forecast.
y=z['all_returns'][:2150].copy(); dates=z['all_dates'][:2150]
y[2100:]=3*y[2100:]+0.1
f.v1.load_returns=lambda _: (y,dates)
q,e,_=f.v1.rebuild_pool('prefix_test',{'dates':dates[1000:],'y':y[1000:]})
for a in f.ALPHAS:
    for kind,values in [('q',q),('e',e)]:
        compare(f'base_{kind}_{a}_through_return_2101',
                values[a][:1101,f.v1.POOL],z[f'base_{kind}_{a}'][:1101,f.v1.POOL])

for a in f.ALPHAS:
    Q=z[f'base_q_{a}'][:2400,f.v1.POOL]; E=z[f'base_e_{a}'][:2400,f.v1.POOL]
    yy=z['all_returns'][1000:3400].copy(); altered=yy.copy(); altered[2100:]=altered[2100:]*3+0.1
    # Same RNG draws: the altered future cannot change selection/forecasts at or before 2100.
    qc,ec,_=f.mcs_combination(yy,Q,E,a,1000,1000,np.random.default_rng(f.SEED))
    qa,ea,_=f.mcs_combination(altered,Q,E,a,1000,1000,np.random.default_rng(f.SEED))
    compare(f'mcs_q_{a}',qc[:2101],qa[:2101]); compare(f'mcs_e_{a}',ec[:2101],ea[:2101])
    q0,e0=Q.mean(1)[1000:],E.mean(1)[1000:]
    original,_=f.calibrate(yy[1000:],q0,e0,a,1000,'A',True)
    changed,_=f.calibrate(altered[1000:],q0,e0,a,1000,'A',True)
    for g in original:
        for j,kind in enumerate(['q','e']):
            compare(f'{g}_{kind}_{a}',original[g][j][:1101],changed[g][j][:1101])
    compare(f'aggregation_weights_{a}',original['A2'][2]['weights'][:1101],changed['A2'][2]['weights'][:1101])

report={'scope':'Finite perturbation checks of frozen algorithms; not proof for every possible path.',
 'perturbation':'Changed current/future returns at stated cutoffs; compared all forecasts through the cutoff.',
 'checks':checks,'all_pass':all(c['pass'] for c in checks),
 'limits':['Historical source vintages are not point-in-time vintage data.',
           'Full-period state/tertile thresholds are retrospective descriptive analyses, not forecasting inputs.',
           'Provider revisions and external selection bias are outside these computational timing tests.']}
dest=ROOT/'outputs/verification/leakage_checks.json'; dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if not report['all_pass']: raise SystemExit('Future-information perturbation mismatch')
