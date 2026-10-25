"""Auditable topic-5 selector replay. No base forecast is re-estimated here."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json, math, time, hashlib, sys
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm
P=Path(__file__).resolve().parent
ALPHA=.01
MARKETS=['sp500','shanghai_comp','bovespa','bsesn','eurostoxx50','hsi','ixic','mxx','nikkei']
METHODS=['EW_all','MCS','WL_MCS','Age_006','Age_0006']

def fz(y,q,e,a=.01):
    return -1.0*(y<=q)*(q-y)/(a*e)+q/e+np.log(-e)-1

def smooth(x):
    y=x.copy(); y[0]=0
    return lfilter([.06],[1,-.94],y,axis=0)

def bstar(x):
    """Port of np 0.60-18 b.star, including its exact CB expression."""
    # Explicit replay extension: a constant loss series has no identifiable ACF.
    # Drop it ONLY for bandwidth estimation; retain all models in selection.
    x=x[:,np.ptp(x,axis=0)>1e-12]
    if x.shape[1]==0:return 2.
    n,m=x.shape; kn=max(5,math.ceil(math.log10(n)))
    mm=math.ceil(math.sqrt(n))+kn; cap=math.ceil(min(3*math.sqrt(n),n/3))
    x=x-x.mean(0); cov=np.array([(x[:n-k]*x[k:]).sum(0)/n for k in range(mm+1)])
    rho=cov[1:]/cov[0]; crit=norm.ppf(.975)*np.sqrt(np.log10(n)/n)
    out=[]
    for j in range(m):
        ins=np.abs(rho[:,j])<crit
        runs=[k+1 for k in range(mm-kn+1) if ins[k:k+kn].all()]
        sig=np.flatnonzero(np.abs(rho[:,j])>crit)+1
        mh=runs[0] if runs else (int(sig[-1]) if len(sig) else 1)
        M=min(2*mh,mm); ks=np.arange(1,M+1); lam=np.where(ks/M<.5,1,2*(1-ks/M))
        g=2*np.sum(lam*ks*cov[1:M+1,j]); lr=cov[0,j]+2*np.sum(lam*cov[1:M+1,j])
        dc=4/3*lr**2
        out.append(min(cap,np.cbrt(2*g*g/dc)*np.cbrt(n)))
    ans=max(out)
    return 2. if ans<1.99 else float(ans)

def block_indices(n,b,B=1000,u=None):
    """Reproduce rugarch 1.5-4 circular blocks, even noninteger nblock semantics.
    R indices/dimensions truncate fractional values; zero rows are dropped by R indexing.
    For experimental age selection b is explicitly ceiled to an integer beforehand.
    """
    s=math.ceil(n/b)
    if u is None: u=np.fromfile(P/'r_seed123_uniform.bin',dtype='<f8')
    starts=np.floor(u[:s*B].reshape((s,B),order='F')*n).astype(int)
    width=int(b); pos=(np.arange(s)[:,None]*b+np.arange(width)[None,:]).astype(int).ravel()
    ix=(starts[:,None,:]+np.arange(width)[None,:,None]).reshape(-1,B)%n
    good=pos<n
    return ix[good].T

def means_from_indices(x,ix,w=None):
    B,N=ix.shape
    cells=(np.arange(B)[:,None]*len(x)+ix).ravel()
    vals=np.full(B*N,1/N) if w is None else np.tile(w,B)
    counts=np.bincount(cells,weights=vals,minlength=B*len(x)).reshape(B,len(x))
    return counts@x

def select(mu,U,alpha=.25,full=False):
    """Range MCS statistic, rugarch elimination rule; U is centered bootstrap means.
    Under age weighting this is an experimental stationary-null bootstrap selector.
    """
    m=len(mu); v=(U*U).mean(0); cov=U.T@U/len(U)
    var=np.maximum(v[:,None]+v[None,:]-2*cov,0)
    # Stable direct variance for almost deterministic contrasts; avoid cancellation.
    ii,jj=np.where(var<1e-12)
    if len(ii):var[ii,jj]=np.mean((U[:,ii]-U[:,jj])**2,axis=0)
    np.fill_diagonal(var,1)
    sd=np.sqrt(var); sd[sd<1e-14]=np.inf
    zd=(mu[:,None]-mu[None,:])/sd
    zb=np.abs((U[:,:,None]-U[:,None,:])/sd)
    active=list(range(m)); removed=[]; ps=[]
    while len(active)>1:
        a=np.array(active); tr=np.abs(zd[np.ix_(a,a)]).max()
        bt=zb[:,a][:,:,a].max(axis=(1,2)); p=float(np.mean(bt>tr)); ps.append(p)
        if p>=alpha and not full: return a,ps
        d=mu[a]-mu[a].mean(); ub=U[:,a]-U[:,a].mean(1,keepdims=True)
        vv=np.sqrt((ub*ub).mean(0)); ts=np.divide(d,vv,out=np.zeros_like(d),where=vv>1e-14)
        rm=int(np.argmax(ts)); removed.append(active.pop(rm))
    if not full:return np.array(active),ps
    removed+=active; ps.append(1.); ps=np.maximum.accumulate(ps)
    start=np.flatnonzero(ps>=alpha)[0]
    return np.array(removed[start:]),ps.tolist()

def load_market(m,tau='0.01'):
    stem=P/f'data__results__{m}_tau_{tau}'
    read=lambda suffix:pd.read_csv(str(stem)+'__'+suffix+'.csv')
    q=read('VaR_oos_ev'); e=read('ES_oos_ev'); loss=read('db_loss_oos').to_numpy()
    y=read('r_t_oos_full').to_numpy().ravel(); dates=read('dates').iloc[:,0].to_numpy()
    sets={kind:[np.array([int(v)-1 for v in s.strip().split(';')],int) for s in Path(str(stem)+'__'+name+'.txt').read_text().splitlines()] for kind,name in [('MCS','MCS_est_included'),('WL_MCS','MCS_est_included_w')]}
    return q,e,loss,y,dates,sets

def validate():
    out=[]
    for m in MARKETS:
        q,e,loss,y,dates,ss=load_market(m)
        err=float(np.max(np.abs(fz(y[:,None],q.to_numpy(),e.to_numpy())-loss)))
        row={'market':m,'N':len(y),'start':dates[0],'end':dates[-1],'fz_max_error':err}
        for method,col in [('MCS','MCS-Comb'),('WL_MCS','WL-MCS-Comb')]:
            sets=ss[method][-len(y):]
            q2=np.array([q.iloc[t,s].mean() for t,s in enumerate(sets)])
            e2=np.array([e.iloc[t,s].mean() for t,s in enumerate(sets)])
            row[method+'_q_max_error']=float(np.max(np.abs(q2-q[col])))
            row[method+'_e_max_error']=float(np.max(np.abs(e2-e[col])))
        out.append(row)
    pd.DataFrame(out).to_csv(P/'published_reconstruction.csv',index=False)
    ref=pd.read_csv(P/'reference_results.csv'); rr=[]
    for row in ref.itertuples():
        x=pd.read_csv(P/f'reference_loss_{row.origin}.csv').to_numpy()
        if row.kind=='wl':x=smooth(x)
        k=bstar(x); ix=block_indices(len(x),k); bm=means_from_indices(x,ix)
        rb=pd.read_csv(P/f'reference_bootmeans_{row.origin}_{row.kind}.csv').to_numpy()
        incl,ps=select(x.mean(0),bm-x.mean(0),full=True)
        original=np.array([int(z)-1 for z in row.included.split(';')]); rp=np.array([float(z) for z in row.pvalues.split(';')])
        rec={'origin':row.origin,'kind':row.kind,'block_error':k-row.block,'boot_n':ix.shape[1],'bootmean_max_error':float(np.max(np.abs(bm-rb))),'set_match':bool(set(incl)==set(original)),'p_max_error':float(np.max(np.abs(np.array(ps)-rp)))}
        # Separate test against stored author's historical selected set.
        *_,ss=load_market('sp500','0.025'); author=ss['MCS' if row.kind=='raw' else 'WL_MCS'][row.origin-1]
        rec['author_saved_set_match']=bool(set(incl)==set(author)); rec['reference_set']=';'.join(str(i+1) for i in sorted(incl));rec['author_set']=';'.join(str(i+1) for i in sorted(author))
        rr.append(rec)
    pd.DataFrame(rr).to_csv(P/'core_validation.csv',index=False)
    print('RECONSTRUCTION',json.dumps(out),flush=True);print('CORE',json.dumps(rr),flush=True)
    assert max(z['fz_max_error'] for z in out)<1e-9
    assert all(z['set_match'] and z['bootmean_max_error']<1e-8 and z['p_max_error']<1e-9 for z in rr)

def run_replay(window=250,B=1000,markets=MARKETS,tag='',integer=False):
    started=time.time(); manifest=[]
    u=np.fromfile(P/'r_seed123_uniform.bin',dtype='<f8')
    for market in markets:
        qf,ef,loss,y,dates,author=load_market(market)
        q=qf.iloc[:,:32].to_numpy(); e=ef.iloc[:,:32].to_numpy(); xall=loss[:,:32]
        assert np.isfinite(q).all() and np.isfinite(e).all() and np.isfinite(xall).all()
        records=[]; diag=[]; selections={}
        for t in range(window,len(y)):
            if (t-window)%5==0:
                x=xall[t-window:t]; z=smooth(x); k=bstar(x); kw=bstar(z)
                if integer:k=math.ceil(k);kw=math.ceil(kw)
                br=means_from_indices(x,block_indices(window,k,B,u)); bw=means_from_indices(z,block_indices(window,kw,B,u))
                selections={'EW_all':np.arange(32),'MCS':select(x.mean(0),br-x.mean(0))[0], 'WL_MCS':select(z.mean(0),bw-z.mean(0))[0]}
                ix=block_indices(window,math.ceil(k),B,u)
                for name,lam in ([] if integer else [('Age_006',.06),('Age_0006',.006)]):
                    w=(1-lam)**np.arange(window-1,-1,-1);w/=w.sum()
                    bm=means_from_indices(x,ix,w)
                    selections[name]=select(w@x,bm-x.mean(0))[0]
                for name,s in selections.items():
                    diag.append({'market':market,'window':window,'t':t,'date':dates[t],'method':name,'size':len(s),'models':';'.join(str(v) for v in sorted(s)),'block_raw':k,'block_wl':kw})
            for name,s in selections.items():
                qq=q[t,s].mean(); ee=e[t,s].mean(); hit=int(y[t]<=qq)
                records.append({'market':market,'window':window,'t':t,'date':dates[t],'method':name,'q':qq,'e':ee,'y':y[t],'fz':float(fz(y[t],qq,ee)),'pinball':float((.01-hit)*(y[t]-qq)),'hit':hit,'es_residual':float(ee-qq+hit*(qq-y[t])/.01),'size':len(s)})
        stem=f'replay_w{window}_{market}{tag}'
        pd.DataFrame(records).to_csv(P/(stem+'.csv'),index=False);pd.DataFrame(diag).to_csv(P/(stem+'_selection.csv'),index=False)
        manifest.append({'market':market,'window':window,'B':B,'n_eval':len(y)-window,'elapsed_total':time.time()-started})
        print('DONE',manifest[-1],flush=True)
    (P/f'replay_w{window}{tag}_manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':
    task=sys.argv[1]
    if task=='validate':validate()
    elif task=='replay':run_replay(int(sys.argv[2]) if len(sys.argv)>2 else 250)
    elif task=='integer':run_replay(250,tag='_integer',integer=True)
