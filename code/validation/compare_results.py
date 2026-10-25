"""Exhaustive numeric comparisons of replay outputs with immutable research references."""
from pathlib import Path
import json
import platform
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
REF=ROOT/'outputs/reference'; NEW=ROOT/'outputs/reproduced'; OUT=ROOT/'outputs/verification'
OUT.mkdir(parents=True,exist_ok=True)
KEYS={
 'confirm_series_metrics.csv':['name','alpha','group','period'],
 'series_metrics.csv':['name','alpha','group','period'],
 'confirm_diagnostics.csv':['name','alpha'], 'diag.csv':['name','alpha'],
 'confirm_states.csv':['name','alpha','group','state'],'states.csv':['name','alpha','group','state'],
 'confirm_crisis_by_series.csv':['name','alpha','shock','group'],
 'crisis.csv':['name','alpha','shock','group'],
 'confirm_crisis.csv':['set','alpha','shock','group'],
 'confirm_daily_means.csv':['set','alpha','date']}
rows=[]
def compare_csv(a,b,label):
    x=pd.read_csv(a); y=pd.read_csv(b)
    if set(x.columns)!=set(y.columns) or len(x)!=len(y):
        rows.append(dict(file=label,column='__structure__',n=len(x),exact=False,max_abs_error=None,within_1e12=False)); return
    keys=KEYS.get(a.name)
    if keys:
        x=x.sort_values(keys).reset_index(drop=True); y=y.sort_values(keys).reset_index(drop=True)
    for c in x:
        if pd.api.types.is_numeric_dtype(x[c]) and not pd.api.types.is_bool_dtype(x[c]):
            xx=x[c].to_numpy(float); yy=y[c].to_numpy(float)
            exact=bool(np.array_equal(xx,yy,equal_nan=True))
            close=bool(np.allclose(xx,yy,atol=1e-12,rtol=0,equal_nan=True))
            finite=np.isfinite(xx)&np.isfinite(yy)
            gap=float(np.max(np.abs(xx[finite]-yy[finite]))) if finite.any() else 0.
        else:
            exact=x[c].fillna('__NA__').equals(y[c].fillna('__NA__')); close=exact; gap=0. if exact else None
        rows.append(dict(file=label,column=c,n=len(x),exact=exact,max_abs_error=gap,within_1e12=close))

coverage={}
for group in ['study1','study2_run1','study2_summary','derived','table_sources']:
    files=list((REF/group).glob('*.csv')); compared=0
    for a in files:
        b=NEW/group/a.name
        if b.exists(): compare_csv(a,b,f'{group}/{a.name}'); compared+=1
    coverage[group]={'reference_csv_files':len(files),'compared_csv_files':compared}

arrays=[]
a=REF/'study2_run1/forecasts.npz'; b=NEW/'study2_run1/forecasts.npz'
if b.exists():
    with np.load(a,allow_pickle=False) as x,np.load(b,allow_pickle=False) as y:
        assert set(x.files)==set(y.files)
        for k in x.files:
            xx,yy=x[k],y[k]
            if np.issubdtype(xx.dtype,np.number):
                exact=bool(np.array_equal(xx,yy,equal_nan=True)); close=bool(np.allclose(xx,yy,atol=1e-12,rtol=0,equal_nan=True))
                finite=np.isfinite(xx)&np.isfinite(yy); gap=float(np.max(np.abs(xx[finite]-yy[finite]))) if finite.any() else 0.
            else: exact=bool(np.array_equal(xx,yy)); close=exact; gap=0. if exact else None
            arrays.append({'array':k,'elements':xx.size,'exact':exact,'max_abs_error':gap,'within_1e12':close})
pd.DataFrame(rows).to_csv(OUT/'numeric_comparison.csv',index=False)
pd.DataFrame(arrays).to_csv(OUT/'study2_array_comparison.csv',index=False)

paper=[]
expected=ROOT/'provenance/paper_expected_values.csv'; actual=NEW/'tables/all_table_cells.csv'
if expected.exists() and actual.exists():
    x=pd.read_csv(expected,dtype=str,keep_default_na=False); y=pd.read_csv(actual,dtype=str,keep_default_na=False)
    keys=['table','row','column']
    z=x.merge(y,on=keys,how='left',suffixes=('_paper','_reproduced'))
    def norm(s):return ' '.join(str(s).replace('−','-').split())
    z['match']=[norm(a)==norm(b) for a,b in zip(z.displayed_text_paper,z.displayed_text_reproduced)]
    z.to_csv(OUT/'paper_cell_comparison.csv',index=False)
    paper={'cells':len(z),'matched':int(z.match.sum()),'tables':z.table.nunique()}
summary={'scope':'Reference outputs versus available reproduced files; source of each stage must be read with execution records.',
 'absolute_tolerance':1e-12,'relative_tolerance':0,'exact_matches_reported_separately':True,
 'coverage':coverage,'csv_columns_compared':len(rows),'csv_columns_exact':sum(r['exact'] for r in rows),
 'csv_columns_within_tolerance':sum(r['within_1e12'] for r in rows),
 'array_count':len(arrays),'arrays_exact':sum(r['exact'] for r in arrays),
 'arrays_within_tolerance':sum(r['within_1e12'] for r in arrays),'paper':paper,
 'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},
 'unverified':['Study 1 original per-series daily q/e were not archived; direct pathwise equality is unavailable.',
               'Matching current-vintage historical data does not verify point-in-time data availability.']}
(OUT/'comparison_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
if any(not r['within_1e12'] for r in rows+arrays) or (paper and paper['matched']!=paper['cells']):
    raise SystemExit('MISMATCH: inspect comparison CSVs; references have not been overwritten.')
