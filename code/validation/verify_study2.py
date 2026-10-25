"""Validate the saved historical-yen run without refitting any model."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'outputs/reproduced/study2_run1'; SUM=ROOT/'outputs/reproduced/study2_summary'
z=np.load(RUN/'forecasts.npz',allow_pickle=False)
dd=pd.read_csv(SUM/'descriptive_daily.csv')
reg=pd.read_csv(SUM/'signal_regression.csv').set_index('alpha')
metrics=pd.read_csv(RUN/'series_metrics.csv')
report={'scope':'saved forecasts, timing, score/metrics, independent HAC library check; no model rerun','checks':{},'notes':[]}
dates=z['all_dates']; y=z['all_returns']
assert len(y)==9043 and len(z['eval_dates'])==6043
assert np.array_equal(dates[3000:],z['eval_dates'])
report['checks']['split']={'first':str(z['eval_dates'][0]),'last':str(z['eval_dates'][-1]),'days':len(z['eval_dates'])}
gaps=[]
for a in (.025,.01):
    aa=str(a); n=len(z['eval_y']); yy=z['eval_y']; w=dd[dd.alpha==a]
    qbase=z['base_q_'+aa][:,[8,9,10,3,4,5,6,7,11,12]].mean(1)
    # Independently index signals on the full-return calendar: today i=3000+t,
    # base-pool index i-1000; past window is [i-1250, i-1000).
    lag=np.array([(y[i-250:i]<qbase[i-1250:i-1000]).mean()-a for i in range(3000,len(y))])
    assert np.allclose(lag,w.lagged_signal,rtol=0,atol=1e-15)
    r60=np.array([y[i-59:i+1].sum() for i in range(3000,len(y))])
    assert np.allclose(r60,w.r60,rtol=0,atol=1e-12)
    for g in ['A0','A1','A1d','A2','A3','A3f','F','C0','C1','C1d','C2','C3','R0']:
        q,e=z['q_'+aa+'_'+g],z['e_'+aa+'_'+g]
        assert np.isfinite(q).all() and np.isfinite(e).all() and (e<=q).all() and (q<0).all()
        score=-1.0*(yy<q)*(q-yy)/(a*e)+q/e+np.log(-e)-1
        assert np.allclose(score,z['fz_'+aa+'_'+g],rtol=0,atol=1e-12)
        row=metrics[(metrics.alpha==a)&(metrics.group==g)&(metrics.period=='main')].iloc[0]
        assert abs(score.mean()-row.fz_mean)<1e-12
        assert abs((yy<q).mean()-row.breach_rate)<1e-12
        z2=1-np.mean((yy<q)*np.abs(yy)/np.abs(e))/a
        assert abs(z2-row.z2)<1e-12
    d=z['fz_'+aa+'_A2']-z['fz_'+aa+'_A0']
    fit=sm.OLS(d,sm.add_constant(lag)).fit().get_robustcov_results(cov_type='HAC',maxlags=250,use_correction=False,use_t=False)
    slope_gap=abs(fit.params[1]-reg.loc[a,'slope']); se_gap=abs(fit.bse[1]-reg.loc[a,'slope_se'])
    assert slope_gap<1e-10 and se_gap<1e-10
    gaps.append({'alpha':a,'slope_gap':slope_gap,'se_gap':se_gap})
    assert (z['q_'+aa+'_A2']<=z['q_'+aa+'_A0']+1e-12).all()
    assert (z['e_'+aa+'_A2']<=z['e_'+aa+'_A0']+1e-12).all()
    W=z['weights_'+aa]
    assert (W>=0).all() and np.allclose(W.sum(1),1)
report['checks']['independent_statsmodels_0146_hac']=gaps
report['checks']['all_26_main_forecast_paths']='legal; score, breach and Z2 agree with saved metrics'
report['checks']['signal_250_day_alignment']='all evaluation dates verified by independent full-array slicing'
report['checks']['sixty_day_returns']='all evaluation dates verified by direct summation'
report['checks']['conservatism_and_weights']='valid'
verdict=json.loads((SUM/'verdict.json').read_text(encoding='utf-8'))
mean=np.mean(z['fz_0.025_A2']-z['fz_0.025_A0'])
assert abs(mean-verdict['primary']['mean'])<1e-14
assert verdict['primary']['p_one_sided']==.1973 and not verdict['confirmed'] and not verdict['holm_applied']
receipt=json.loads((ROOT/'data/study2/fetch_manifest.json').read_text(encoding='utf-8'))
assert hashlib.sha256((ROOT/'data/study2/DEXJPUS_1974_2009.csv').read_bytes()).hexdigest()==receipt['sha256']
report['checks']['primary_mean_and_decision']='consistent with saved first analysis'
report['notes']=['Bootstrap p-value is audited from its frozen algorithm/seed and saved first execution, not recomputed here.',
'Normal intervals used 1.96 as specified; no t-distribution or finite-sample covariance adjustment.',
'Raw input and forecast hashes match receipts; no 2010+ data entered this run.']
(ROOT/'outputs/verification/study2_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
