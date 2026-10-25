"""Generate manuscript tables and vector figures only from saved empirical results."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'outputs/reproduced/study1'
if not (SRC/'confirm_meta.json').exists():
    SRC=ROOT/'outputs/reference/study1'
TAB=ROOT/'outputs/reproduced/table_sources'; FIG=ROOT/'outputs/reproduced/legacy_figures'
TAB.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'pdf.fonttype':42})
def esc(v): return str(v).replace('_',r'\_').replace('%',r'\%')
def num(v,d=4): return f'{v:.{d}f}' if np.isfinite(v) else '--'
def interval(row): return f"[{row.ci_low:.4f}, {row.ci_high:.4f}]"
def table(file,caption,label,heads,rows,note='',align=None):
    align=align or 'l'+'r'*(len(heads)-1)
    lines=[r'\begin{table}[htbp]\centering\small',
           r'\caption{'+caption+r'}\label{'+label+'}',
           r'\begin{tabular}{'+align+r'}\toprule',' & '.join(heads)+r'\\\midrule']
    lines += [' & '.join(str(v) for v in row)+r'\\' for row in rows]
    lines += [r'\bottomrule\end{tabular}']
    if note: lines += [r'\par\smallskip\begin{minipage}{.98\linewidth}\footnotesize '+note+r'\end{minipage}']
    lines += [r'\end{table}']
    (TAB/(file+'.tex')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pd.DataFrame(rows,columns=heads).to_csv(TAB/(file+'.csv'),index=False)
t=pd.read_csv(SRC/'confirm_tests.csv')
main=t[(t['set']=='industries')&(t.alpha==.025)]
pri=main[(main.kind=='primary')&(main.block_spec=='pw')]
table('study1_primary','Study 1: primary 97.5\\% FZ0 comparisons','tab:study1primary',
      ['Hypothesis','Comparison','Mean','95\\% interval','One-sided $p$','Holm $p$'],
      [[r.contrast,r.a+'--'+r.b,num(r['mean'],6),interval(r),num(r.p_one_sided),num(r.p_holm)] for _,r in pri.iterrows()],
      'Original archived estimates; 12,897 dates. Negative differences favor A2. Intervals are unadjusted; decisions use Holm-adjusted one-sided tests.')
m=pd.read_csv(SRC/'confirm_series_metrics.csv')
mm=m[(m['class']=='industry')&(m.period=='main')].groupby(['alpha','group'])[['fz_mean','breach_rate','z2']].mean()
groups=['A0','A1','A1d','A2','A3','A3f','F','C0','C1','C1d','C2','C3','R0']
rows=[]
for g in groups:
    x=mm.loc[(.025,g)]; z=mm.loc[(.01,g)]
    rows.append([g,num(x.fz_mean),num(100*x.breach_rate,3),num(x.z2),num(z.fz_mean),num(100*z.breach_rate,3),num(z.z2)])
table('study1_metrics','Study 1: all main arms on the industry panel','tab:study1metrics',
      ['Arm','FZ0$_{97.5}$','Breach \\%',' $Z_{2,97.5}$','FZ0$_{99}$','Breach \\%','$Z_{2,99}$'],rows,
      'Equal-weight industry averages; all industry evaluation lengths coincide. FZ0 is lower-is-better; breach rates and $Z_2$ are descriptive point estimates.')
sec=main[(main.kind=='secondary')&(main.block_spec=='pw')]
table('study1_secondary','Study 1: frozen secondary 97.5\\% contrasts','tab:study1secondary',
      ['Comparison','Mean','95\\% interval'],[[r.a+'--'+r.b,num(r['mean'],6),interval(r)] for _,r in sec.iterrows()],
      'Secondary unadjusted intervals; these comparisons do not change the primary decision.')
cr=pd.read_csv(SRC/'confirm_crisis.csv')
c=cr[(cr['set']=='industries')&(cr.alpha==.025)].pivot(index='shock',columns='group',values='fz_mean')
table('study1_crisis','Study 1: frozen sixty-day industry crisis windows','tab:crisis',
      ['Starting event date','A0 FZ0','A2 FZ0','A2--A0'],
      [[i,num(r.A0),num(r.A2),num(r.A2-r.A0)] for i,r in c.iterrows()],
      'Sixty trading days from the shock date or next available date; descriptive means, not separate confirmations.')
rob=main[(main.kind=='primary')&(main.block_spec!='pw')]
table('study1_robustness','Study 1: primary-contrast block-length sensitivities','tab:robustness',
      ['Contrast','Block','Mean','95\\% interval','One-sided $p$'],
      [[r.contrast,int(r.block),num(r['mean'],6),interval(r),num(r.p_one_sided)] for _,r in rob.iterrows()],
      'Original unadjusted sensitivity values. These are not substituted for the frozen primary tests.')
s99=t[(t.block_spec=='pw')&(((t['set']=='industries')&(t.alpha==.01)&(t.kind=='primary'))|((t['set']=='indices')&(t.kind=='replication')))]
table('study1_secondary99','Secondary tail level and external-index comparisons','tab:secondary99',
      ['Panel','Level','Contrast','Mean','95\\% interval','Raw $p$','Holm $p$'],
      [[r['set'],f'{100*(1-r.alpha):g}\\%',r.contrast,num(r['mean']),interval(r),num(r.p_one_sided),num(r.p_holm)] for _,r in s99.iterrows()],
      'Holm at 99\\% is the archived within-level calculation; index results were not multiplicity-adjusted.')
s2=ROOT/'outputs/reproduced/study2_summary'; run=ROOT/'outputs/reproduced/study2_run1'
tt=pd.read_csv(s2/'tests.csv')
table('study2_tests','Historical yen: A2--A0 and block sensitivities','tab:study2tests',
      ['Level','Block','Mean','95\\% interval','One-sided $p$'],
      [[f'{100*(1-r.alpha):g}\\%',num(r.block,2),num(r['mean'],6),interval(r),num(r.p_one_sided)] for _,r in tt[tt.contrast=='A2_vs_A0'].iterrows()],
      'Only 97.5\\%, block 3.26, is primary; no Holm adjustment. All other rows are prespecified descriptions.')
table('study2_comparators','Historical yen: secondary A2 comparisons','tab:study2comparators',
      ['Level','Comparator','Mean','95\\% interval'],
      [[f'{100*(1-r.alpha):g}\\%',r.contrast.replace('A2_vs_',''),num(r['mean'],6),interval(r)] for _,r in tt[tt.contrast!='A2_vs_A0'].iterrows()],
      'Frozen default block lengths: 3.26 at 97.5\\%, 5.05 at 99\\%. No secondary success thresholds.')
am=pd.read_csv(s2/'appreciation.csv')
table('study2_appreciation','Historical yen: retrospective appreciation states','tab:appreciation',
      ['Level','State','Days','Mean A2--A0','HAC 95\\% interval'],
      [[f'{100*(1-r.alpha):g}\\%','Sharp appreciation' if r.state=='sharp_appreciation' else 'Other days',int(r.days),num(r['mean'],6),interval(r)] for _,r in am.iterrows()],
      'Sharp appreciation is the lowest evaluation-sample decile of trailing sixty-day returns including the current return. Newey--West lag 250 uses original calendar order and conditions on the observed state threshold; this is retrospective.')
sig=pd.read_csv(s2/'signal_tertiles.csv')
table('study2_tertiles','Historical yen: groups of the lagged A0 exceedance signal','tab:signal',
      ['Level','Group','Days','Signal range','Mean A2--A0','HAC 95\\% interval'],
      [[f'{100*(1-r.alpha):g}\\%',int(r.tertile),int(r.days),f'[{r.signal_min:.3f}, {r.signal_max:.3f}]',num(r['mean'],6),interval(r)] for _,r in sig.iterrows()],
      'The signal is the previous 250-day A0 exceedance rate minus $\\alpha$; ties make the three quantile-defined groups unequal in size. Group cutoffs are full-sample descriptive cutoffs.')
reg=pd.read_csv(s2/'signal_regression.csv')
table('study2_regression','Historical yen: OLS association with the lagged signal','tab:regression',
      ['Level','Intercept','Slope','HAC SE','95\\% slope interval'],
      [[f'{100*(1-r.alpha):g}\\%',num(r.intercept,6),num(r.slope),num(r.slope_se),interval(r)] for _,r in reg.iterrows()],
      'Slope is per unit of exceedance-rate signal (not per percentage point). Bartlett Newey--West lag 250; normal intervals, no finite-sample correction.')
ym=pd.read_csv(run/'series_metrics.csv'); ym=ym[ym.period=='main'].set_index(['alpha','group'])
rows=[]
for g in groups:
    a,b=ym.loc[(.025,g)],ym.loc[(.01,g)]
    rows.append([g,num(a.fz_mean),num(100*a.breach_rate,3),num(a.z2),num(b.fz_mean),num(100*b.breach_rate,3),num(b.z2)])
table('study2_allarms','Historical yen: all main-arm score and risk summaries','tab:yenarms',
      ['Arm','FZ0$_{97.5}$','Breach \\%','$Z_{2,97.5}$','FZ0$_{99}$','Breach \\%','$Z_{2,99}$'],rows,
      'Same 6,043 evaluation dates for each arm and tail level.')
yc=pd.read_csv(run/'crisis.csv').pivot(index=['alpha','shock'],columns='group',values='fz_mean')
table('study2_crisis','Historical yen: inherited sixty-day crisis windows','tab:yencrisis',
      ['Level','Starting date','A0 FZ0','A2 FZ0','A2--A0'],
      [[f'{100*(1-i[0]):g}\\%',i[1],num(r.A0),num(r.A2),num(r.A2-r.A0)] for i,r in yc.iterrows()],
      'Only the four inherited windows fully contained in the historical evaluation are retained; no yen-specific event dates were added.')
dm=pd.read_csv(SRC/'confirm_daily_means.csv')
fig,ax=plt.subplots(figsize=(9,3.7))
for a,color in [(.025,'#135E79'),(.01,'#B15C2E')]:
    w=dm[(dm['set']=='industries')&(dm.alpha==a)].sort_values('date')
    ax.plot(pd.to_datetime(w.date),(w.A2-w.A0).cumsum(),label=f'{100*(1-a):g}% level',color=color,lw=1.3)
ax.axhline(0,color='black',lw=.7); ax.set_ylabel('Cumulative FZ0 difference (A2 - A0)'); ax.legend(frameon=False)
fig.tight_layout()
for ext in ('pdf','svg','png'): fig.savefig(FIG/('study1_cumulative.'+ext),dpi=180)
plt.close(fig)
dd=pd.read_csv(s2/'descriptive_daily.csv')
fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
for ax,a,color in zip(axes,[.025,.01],['#135E79','#B15C2E']):
    w=dd[dd.alpha==a]
    dates=pd.to_datetime(w.date)
    ax.plot(dates,w.d_A2_A0.cumsum(),color=color,lw=1.2)
    ax.fill_between(dates,0,1,where=w.appreciation_state,transform=ax.get_xaxis_transform(),color='#8AB6C2',alpha=.22)
    ax.axhline(0,color='black',lw=.7)
    ax.set_ylabel(f'{100*(1-a):g}% cumulative difference')
axes[-1].set_xlabel('Evaluation date')
fig.tight_layout()
for ext in ('pdf','svg','png'): fig.savefig(FIG/('study2_cumulative.'+ext),dpi=180)
plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(9,3.7))
for ax,a in zip(axes,[.025,.01]):
    r=am[am.alpha==a]
    yy=r['mean'].to_numpy(); err=np.vstack([yy-r.ci_low,r.ci_high-yy])
    ax.errorbar([0,1],yy,yerr=err,fmt='o',color='#135E79',capsize=5)
    ax.axhline(0,color='black',lw=.7); ax.set_xticks([0,1],['Appreciation','Other days']); ax.set_title(f'{100*(1-a):g}%')
axes[0].set_ylabel('Mean FZ0 difference (A2 - A0)')
fig.tight_layout()
for ext in ('pdf','svg','png'): fig.savefig(FIG/('study2_states.'+ext),dpi=180)
plt.close(fig)
print(f'Generated {len(list(TAB.glob("*.tex")))} tables and 3 figures from saved results.')
