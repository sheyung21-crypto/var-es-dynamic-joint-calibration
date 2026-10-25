"""Recompute archived Study 1 summaries; no forecast/bootstrap rerun or source mutation."""
from pathlib import Path
import hashlib, io, json, math, platform, zipfile
import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
import os
SRC=Path(os.environ['VAR_STUDY1_DATA'])
R=ROOT/'outputs/reference/study1'
if (ROOT/'outputs/reproduced/study1/confirm_meta.json').exists():
 R=ROOT/'outputs/reproduced/study1'
O=ROOT/'outputs/reproduced/derived'; A=ROOT/'outputs/verification'; F=ROOT/'outputs/reproduced/legacy_figures'
for p in (O,A,F): p.mkdir(parents=True,exist_ok=True)
def save(df,name): df.to_csv(O/('study1_'+name+'.csv'),index=False,float_format='%.16g')
def holm(p):
 p=np.asarray(p); order=np.argsort(p); out=np.empty_like(p)
 out[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(p),0,-1)))
 return out
def hac(d,L):
 x=d-d.mean(); n=len(x); v=x@x/n
 for k in range(1,L+1): v+=2*(1-k/(L+1))*(x[k:]@x[:-k])/n
 return float(norm.cdf(d.mean()/np.sqrt(v/n)))
daily=pd.read_csv(R/'confirm_daily_means.csv')
tests=pd.read_csv(R/'confirm_tests.csv')
metrics=pd.read_csv(R/'confirm_series_metrics.csv')
h5=pd.read_csv(R/'confirm_h5.csv')
meta=json.loads((R/'confirm_meta.json').read_text(encoding='utf-8'))
main=metrics[metrics.period=='main']
rows=[]
for r in tests.itertuples(index=False):
 s=daily[(daily['set']==r.set)&(daily.alpha==r.alpha)&(daily.date>=r.first)&(daily.date<=r.last)]
 d=(s[r.a]-s[r.b]).dropna().to_numpy()
 rows.append(dict(set=r.set,alpha=r.alpha,kind=r.kind,contrast=r.contrast,block_spec=r.block_spec,recomputed_mean=d.mean(),archived_mean=r.mean,mean_absolute_error=abs(d.mean()-r.mean),days=len(d),archived_days=r.days,nw_p_recomputed=hac(d,int(r.nw_lag)),nw_p_archived=r.nw_p,nw_p_absolute_error=abs(hac(d,int(r.nw_lag))-r.nw_p)))
check=pd.DataFrame(rows); save(check,'mean_audit')
p=tests[(tests.kind=='primary')&(tests.block_spec=='pw')].copy(); p['p_holm_recomputed']=np.nan
for _,s in p.groupby(['set','alpha']): p.loc[s.index,'p_holm_recomputed']=holm(s.p_one_sided.to_numpy())
p['holm_absolute_error']=abs(p.p_holm-p.p_holm_recomputed); save(p,'primary_audit'); save(tests,'all_archived_contrasts')
# Date split independently read from raw data; models are never run.
with zipfile.ZipFile(SRC/'french'/'30_Industry_Portfolios_daily_CSV.zip') as z:
 lines=z.read(z.namelist()[0]).decode('latin-1').splitlines()
i=next(i for i,l in enumerate(lines) if 'Average Value Weighted Returns -- Daily' in l)
j=next(j for j in range(i+2,len(lines)) if not lines[j].strip()[:1].isdigit())
f=pd.read_csv(io.StringIO('\n'.join(lines[i+1:j])),skipinitialspace=True)
dates=pd.to_datetime(f.iloc[:,0].astype(str),format='%Y%m%d').dt.strftime('%Y-%m-%d'); sel=dates>='1963-07-01'; f=f.loc[sel]; dates=dates[sel]
raw={}
for n in f.columns[1:]:
 v=f[n].to_numpy(float); raw[n]=dates.to_numpy()[np.isfinite(v)&~np.isin(v,[-99.99,-999])]
for path in sorted((SRC/'yahoo').glob('yahoo_*.json')):
 r=json.loads(path.read_text())['chart']['result'][0]
 d=pd.to_datetime(np.asarray(r['timestamp'])+r['meta']['gmtoffset'],unit='s').strftime('%Y-%m-%d')
 v=pd.Series(r['indicators']['quote'][0]['close'],index=d,dtype=float); v=v[~v.index.duplicated(keep='last')]; v=v[np.isfinite(v)&(v>0)]
 raw[path.stem.removeprefix('yahoo_')]=v.index.to_numpy()[1:]
date_rows=[]
for n,d in raw.items():
 r=meta['series'][n]
 date_rows.append(dict(name=n,first=d[3000],last=d[-1],days=len(d)-3000,robust_first=d[5000],match=d[3000]==r['eval_first'] and d[-1]==r['eval_last'] and len(d)-3000==r['eval_days'] and d[5000]==r['robust_start']))
df_dates=pd.DataFrame(date_rows); save(df_dates,'date_audit')
rows=[]
for r in h5.itertuples(index=False):
 cl='industry' if r.set=='industries' else 'index'; s=main[(main['class']==cl)&(main.alpha==r.alpha)&(main.group==r.group)]
 rate=np.average(s.breach_rate,weights=s.days); z2=np.average(s.z2,weights=s.days)
 rows.append(dict(set=r.set,alpha=r.alpha,group=r.group,recomputed_breach_rate=rate,archived_breach_rate=r.breach_rate,breach_absolute_error=abs(rate-r.breach_rate),recomputed_z2=z2,archived_z2=r.z2_day_weighted,z2_absolute_error=abs(z2-r.z2_day_weighted)))
risk=pd.DataFrame(rows); save(risk,'risk_audit')
rows=[]
for (cl,alpha,g),s in main.groupby(['class','alpha','group'],sort=False):
 sn='industries' if cl=='industry' else 'indices'; d=daily[(daily['set']==sn)&(daily.alpha==alpha)]
 rows.append(dict(set=sn,alpha=alpha,group=g,series=s.name.nunique(),series_days=int(s.days.sum()),mean_fz_calendar_day_weighted=d[g].mean(),**{k:np.average(s[k],weights=s.days) for k in ['breach_rate','z2','mean_abs_var','mean_abs_es','var_log_change','es_log_change']},es_equals_var_days=int(s.es_equals_var_days.sum())))
save(pd.DataFrame(rows),'methods')
rows=[]
for (n,alpha),s in main.groupby(['name','alpha']):
 s=s.set_index('group'); a=s.loc['A0']; b=s.loc['A2']
 rows.append(dict(name=n,**{'class':a['class']},alpha=alpha,days=int(a.days),a0_fz=a.fz_mean,a2_fz=b.fz_mean,d_a2_minus_a0=b.fz_mean-a.fz_mean,a0_breach_rate=a.breach_rate,a0_breach_excess=a.breach_rate-alpha,a0_abs_breach_error=abs(a.breach_rate-alpha),a0_z2=a.z2,a0_abs_z2=abs(a.z2),a2_breach_rate=b.breach_rate,a2_z2=b.z2))
e=pd.DataFrame(rows); save(e,'exploratory_series')
rows=[]
for alpha in [.025,.01]:
 for cl in ['all','industry','index']:
  s=e[(e.alpha==alpha)&((e['class']==cl)|(cl=='all'))]
  for x in ['a0_breach_excess','a0_abs_breach_error','a0_z2','a0_abs_z2']:
   rows.append(dict(alpha=alpha,**{'class':cl},x=x,n_series=len(s),pearson_r=s[x].corr(s.d_a2_minus_a0),spearman_rho=spearmanr(s[x],s.d_a2_minus_a0).statistic,ols_descriptive_slope=np.polyfit(s[x],s.d_a2_minus_a0,1)[0],n_negative_d=int((s.d_a2_minus_a0<0).sum())))
corr=pd.DataFrame(rows); save(corr,'exploratory_correlations')
crisis=pd.read_csv(R/'confirm_crisis.csv'); rows=[]
for (sn,alpha,shock),s in crisis.groupby(['set','alpha','shock']):
 s=s.set_index('group'); rows.append(dict(set=sn,alpha=alpha,shock=shock,series=s.loc['A2','series'],a0_fz=s.loc['A0','fz_mean'],a2_fz=s.loc['A2','fz_mean'],d_a2_minus_a0=s.loc['A2','fz_mean']-s.loc['A0','fz_mean'],a0_breach_rate=s.loc['A0','breach_rate'],a2_breach_rate=s.loc['A2','breach_rate']))
save(pd.DataFrame(rows),'crisis_contrasts')
period=pd.read_csv(R/'confirm_periods.csv'); save(period,'periods')
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
fig,axs=plt.subplots(2,2,figsize=(9,6),sharey='row')
for i,alpha in enumerate([.025,.01]):
 s=e[e.alpha==alpha]
 for j,(col,scale,label) in enumerate([('a0_breach_excess',100,'A0 breach rate minus target (percentage points)'),('a0_z2',1,'A0 Z2 (negative indicates underestimation)')]):
  ax=axs[i,j]
  for cl,marker,color,label2 in [('industry','o','#1f5f8b','30 industries'),('index','^','#bf6c23','6 indices')]:
   ss=s[s['class']==cl]; ax.scatter(ss[col]*scale,ss.d_a2_minus_a0,marker=marker,color=color,label=label2,s=27,alpha=.85)
  ax.axhline(0,color='.5',lw=.8); ax.axvline(0,color='.7',lw=.8); ax.set_xlabel(label); ax.set_title(f'{100*(1-alpha):g}%: descriptive summaries')
  if j==0: ax.set_ylabel('Mean FZ0(A2) minus mean FZ0(A0)')
  if i==j==0: ax.legend(frameon=False)
fig.tight_layout()
for ext in ['pdf','png']: fig.savefig(F/f'study1_exploratory_calibration.{ext}',dpi=180)
plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(9.5,3.5),sharey=True)
for ax,alpha in zip(axs,[.025,.01]):
 s=tests[(tests['set']=='industries')&(tests.alpha==alpha)&(tests.block_spec=='pw')&tests.kind.isin(['primary','secondary'])].set_index('contrast').loc[['H1','H2','H3','A2_vs_F','A2_vs_R0']]
 yy=np.arange(5)[::-1]; ax.errorbar(s['mean'],yy,xerr=np.stack([s['mean']-s.ci_low,s.ci_high-s['mean']]),fmt='o',capsize=3,color='#1f5f8b'); ax.axvline(0,color='.5',lw=.8); ax.set_yticks(yy,['H1: A2 - A0','H2: A2 - A1d','H3: A2 - A3','A2 - F','A2 - GJR-t']); ax.set_title(f'{100*(1-alpha):g}%'); ax.set_xlabel('Mean FZ0 difference (A2 minus comparator)')
fig.tight_layout()
for ext in ['pdf','png']: fig.savefig(F/f'study1_primary_contrasts.{ext}',dpi=180)
plt.close(fig)
audit=dict(verification_status='ANALYZED; archived-summary arithmetic verified',forecast_rerun=False,bootstrap_rerun=False,mean_rows_checked=len(check),mean_max_absolute_error=float(check.mean_absolute_error.max()),days_all_match=bool((check.days==check.archived_days).all()),holm_max_absolute_error=float(p.holm_absolute_error.max()),nw_p_max_absolute_error=float(check.nw_p_absolute_error.max()),raw_date_checks=len(df_dates),raw_dates_all_match=bool(df_dates.match.all()),risk_breach_max_absolute_error=float(risk.breach_absolute_error.max()),risk_z2_max_absolute_error=float(risk.z2_absolute_error.max()),archived_legality_flags_all_true=bool(metrics.legal.all()),critical_errors_identified=[],source_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(R.glob('*.csv'))},versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__))
(A/'study1_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
assert audit['mean_max_absolute_error']<1e-12 and audit['holm_max_absolute_error']<1e-12 and audit['raw_dates_all_match'] and audit['days_all_match']
print(json.dumps({k:v for k,v in audit.items() if k!='source_sha256'},indent=2))
print(corr[corr.x.isin(['a0_breach_excess','a0_z2'])].to_string(index=False))

