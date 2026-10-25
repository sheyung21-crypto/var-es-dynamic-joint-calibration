"""Recompute final-paper numerical prose and decade cells from available replay outputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
PUB=ROOT/'outputs/reproduced'
OUT=ROOT/'outputs/verification'
SRC=PUB/'study1'
if not (SRC/'confirm_meta.json').exists(): SRC=ROOT/'outputs/reference/study1'
dm=pd.read_csv(SRC/'confirm_daily_means.csv')
sum_rows=[]
crises=['1987-10-19','1998-08-17','2001-09-17','2008-09-15','2011-08-08','2015-08-24','2020-02-24']
for alpha in [.025,.01]:
    w=dm[(dm['set']=='industries')&(dm.alpha==alpha)].sort_values('date').reset_index(drop=True)
    mask=np.zeros(len(w),dtype=bool)
    for date in crises:
        i=np.searchsorted(w.date.to_numpy(),date)
        mask[i:i+60]=True
    d=w.A2-w.A0
    for name,m in [('crisis',mask),('other_days',~mask),('total',np.ones(len(w),bool))]:
        sum_rows.append({'study':'industries','alpha':alpha,'subset':name,'days':int(m.sum()),'sum_difference':float(d[m].sum())})
dd=pd.read_csv(PUB/'study2_summary/descriptive_daily.csv')
for alpha in [.025,.01]:
    w=dd[dd.alpha==alpha]
    mask=w.appreciation_state.astype(bool)
    for name,m in [('sharp_appreciation',mask),('other_days',~mask),('total',np.ones(len(w),bool))]:
        sum_rows.append({'study':'yen','alpha':alpha,'subset':name,'days':int(np.sum(m)),'sum_difference':float(w.d_A2_A0[m].sum())})
pd.DataFrame(sum_rows).to_csv(OUT/'paper_descriptive_sums_recomputed.csv',index=False)

w=dm[(dm['set']=='industries')&(dm.alpha==.025)].copy()
w['period']=pd.cut(pd.to_datetime(w.date).dt.year,[1974,1979,1989,1999,2009,2019,2026],labels=['1975-79','1980s','1990s','2000s','2010s','2020-26'])
heat=pd.DataFrame({c:w.groupby('period',observed=True).apply(lambda g,c=c:(g[c]-g.A0).mean())
                   for c in ['A2','F','A1d','A1','A3','A3f','C0','C2','C1d','C1','C3','R0']}).T
heat.to_csv(OUT/'paper_figure_C1_recomputed.csv',index_label='arm')

claims=[]
def claim(name, value, reported, source, decimals):
    displayed=f'{value:.{decimals}f}'
    claims.append({'claim':name,'source':source,'archived_or_recomputed_value':float(value),
                   'paper_reported_value':reported,'decimal_places':decimals,'rounded_value':displayed,
                   'matches_at_paper_precision':displayed==reported})

for r in sum_rows:
    key=(r['study'],r['alpha'],r['subset'])
    reports={('industries',.025,'crisis'):'-157.1',('industries',.025,'other_days'):'55.5',('industries',.025,'total'):'-101.6',
             ('industries',.01,'crisis'):'-295.9',('industries',.01,'other_days'):'117.9',
             ('yen',.025,'sharp_appreciation'):'-91.7',('yen',.025,'other_days'):'49.0',('yen',.025,'total'):'-42.7',
             ('yen',.01,'sharp_appreciation'):'-123.5',('yen',.01,'other_days'):'104.1'}
    if key in reports:
        claim(f'{key} cumulative score difference',r['sum_difference'],reports[key],
              'confirm_daily_means.csv or study2_summary/descriptive_daily.csv; recomputed sum',1)

corr=pd.read_csv(PUB/'derived/study1_exploratory_correlations.csv')
for alpha,cl,x,stat,reported in [
 (.025,'all','a0_breach_excess','pearson_r','-0.774'),(.025,'all','a0_z2','pearson_r','0.842'),
 (.025,'all','a0_breach_excess','spearman_rho','-0.731'),(.025,'all','a0_z2','spearman_rho','0.845'),
 (.025,'industry','a0_breach_excess','pearson_r','-0.681'),(.025,'industry','a0_z2','pearson_r','0.764'),
 (.025,'index','a0_breach_excess','pearson_r','-0.869'),(.025,'index','a0_z2','pearson_r','0.830'),
 (.01,'all','a0_breach_excess','pearson_r','-0.632'),(.01,'all','a0_z2','pearson_r','0.668')]:
    v=corr.loc[(corr.alpha==alpha)&(corr['class']==cl)&(corr.x==x),stat].iloc[0]
    claim(f'{alpha} {cl} {x} {stat}',v,reported,'study1_exploratory_correlations.csv',3)

for arm,period,reported in [('A2','1980s','-0.014'),('A2','1990s','-0.002'),('A2','2000s','-0.013'),
                          ('A2','2010s','0.001'),('A2','2020-26','-0.015'),('R0','1975-79','-0.002'),
                          ('R0','2000s','-0.029'),('R0','2010s','-0.033'),('R0','2020-26','-0.041')]:
    claim(f'Figure C1 {arm} {period}',heat.loc[arm,period],reported,'confirm_daily_means.csv; recomputed decade mean',3)

reg=pd.read_csv(PUB/'study2_summary/signal_regression.csv').set_index('alpha')
for a,field,reported in [(.025,'slope','0.464'),(.025,'ci_low','-0.540'),(.025,'ci_high','1.469'),
                       (.01,'slope','2.227'),(.01,'ci_low','-1.490'),(.01,'ci_high','5.944')]:
    claim(f'Yen lagged signal {a} {field}',reg.loc[a,field],reported,'study2_summary/signal_regression.csv',3)

app=pd.read_csv(PUB/'study2_summary/appreciation.csv')
claim('Yen sharp-appreciation threshold',app.r60_threshold.iloc[0],'-8.37','study2_summary/appreciation.csv',2)
h4=pd.read_csv(SRC/'confirm_h4.csv')
r=h4[(h4['set']=='industries')&(h4.alpha==.025)&(h4.calibration=='D1')].iloc[0]
for f,reported,nd in [('mcs_gap_before','-0.0095',4),('mcs_gap_after','-0.0074',4),('after_minus_before','0.0021',4),
                       ('ci_low','-0.000007',6),('ci_high','0.004480',6)]:
    claim('Industry MCS/DJC interaction '+f,r[f],reported,'confirm_h4.csv',nd)
t=pd.read_csv(SRC/'confirm_tests.csv')
rob=t[(t['set']=='industries')&(t.alpha==.025)&(t.kind=='robust_2000_window')&(t.block_spec=='pw')]
for hyp,field,reported in [('H1','mean','-0.0082'),('H1','ci_low','-0.0217'),('H1','ci_high','0.0027'),('H1','p_one_sided','0.1014'),
                         ('H2','mean','-0.0131'),('H2','ci_low','-0.0242'),('H2','ci_high','-0.0046'),('H2','p_one_sided','0.0109')]:
    claim('Industry 2000-day-window '+hyp+' '+field,rob.loc[rob.contrast==hyp,field].iloc[0],reported,'confirm_tests.csv, kind=robust_2000_window, block_spec=pw',4)
pd.DataFrame(claims).to_csv(OUT/'paper_additional_claims.csv',index=False)


report={'claims':len(claims),'matches':sum(x['matches_at_paper_precision'] for x in claims),
        'study1_source':'replayed' if SRC==PUB/'study1' else 'archived',
        'study2_source':'outputs/reproduced/study2_summary'}
(OUT/'paper_claims_summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
assert report['claims']==report['matches']
