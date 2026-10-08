"""K1 v3 synthesis cost model. Rates from the cost cell (k1v3_cost.py), which come from
K1 v2 probe 543 and dense pre-check v2 lane 862; native-8K factor added by synthesis."""
import math, json
A=231.60738/440; B=122.64946/280; C=41.88710/160          # lane 862 per-unit S+MC, MC, S (proxy contexts, mean ~6.6K tokens)
P04=659716; P4=2560*512+2560*128+2560*4+4+128+128          # indexer params (0.6B, 4B)
save_rate=3.2821545591577888/(18*P04*3*4/1e6)               # s per MB (probe 543)
def save_layer(n): return n*P4*12/1e6*save_rate
NATIVE=1.20   # native 8,192-token contexts vs re-tokenised proxy (mean ~6.6K): per-unit factor (cost cell: +15%)
SC={'central':dict(teach=0.97,tgt=0.015,idx=0.0028,S=C*NATIVE,SMC=A*NATIVE,MC=B*NATIVE,Sp=C,SMCp=A,MCp=B,sm=1.0,kl=0.455),
    'high':   dict(teach=1.40,tgt=0.026,idx=0.0049,S=1.3*C*NATIVE,SMC=0.90*NATIVE,MC=0.66*NATIVE,Sp=1.3*C,SMCp=0.90,MCp=0.66,sm=1.3,kl=0.91)}
L=8; BATCH=4
def step(s,n): return s['teach']+L*BATCH*(s['tgt']+n*s['idx'])
def limit(P): return max(5, math.ceil(1.2*1.15*P/60+3))
def cap(g,P): lm=limit(P); return lm, math.ceil(g*lm/60*100-1e-9)/100
def design(q=230, X=10, cs=5, tr=2, twins=2000, prim_twins=0, n_idx=18, dq=20):
    out={}
    for k,s in SC.items():
        cx=2*X*q; mn=(1+X)*q; ml=200; trs=2*tr*q; css=2*cs*q+cs*q
        main_S = cx+mn+ml+trs+css
        st=step(s,n_idx); st6=step(s,6)
        sv=7*L*save_layer(n_idx)*s['sm']; rd=L*save_layer(n_idx)*s['sm']; kl=64*s['kl']
        main=300+610*st+sv+kl+rd+main_S*s['S']
        ext=300+1220*st6+13*L*save_layer(6)*s['sm']+rd+(cx+mn+ml)*s['S']
        smoke=120+60+47+12*st+6*st6+2*L*save_layer(n_idx)*s['sm']+4*s['kl']+24*(s['SMC']+s['S']+s['MC'])+24*(s['SMCp']+s['MCp'])
        dev=120+47+ (2*X*dq)*s['SMC'] + ((1+X)*dq + (1+X)*dq + 2*tr*dq)*s['S'] + (2*2*X*dq)*s['MC']
        h2=120+47+2*(twins+prim_twins)*s['MC']
        r0=120+60+40*st+4*L*save_layer(n_idx)*s['sm']; r1=120+60+25*st+2*L*save_layer(n_idx)*s['sm']; r2=120+60+15*st+2*L*save_layer(n_idx)*s['sm']+rd
        jobs={'probe-4b':None,'smoke':smoke,'dev-prestep':dev,'h2-gate':h2,'R0':r0,'R1':r1,'R2':r2,'main':main,'extension':ext}
        rows={}; tot=0; use=0
        for j,P in jobs.items():
            if P is None: rows[j]=(None,15,0.25); tot+=0.25; use+=0.1; continue
            lm,c=cap(1,P); rows[j]=(round(P/60,1),lm,c); tot+=c
            if j!='extension': use+=P/3600
        out[k]=dict(rows=rows,total_caps=round(tot,2),expected_use_no_ext=round(use,2),ext_use=round(ext/3600,2),
                    step=round(st,2),step6=round(st6,2),train_min=round(610*st/60,1),main_S=main_S,
                    use_if_dev_stop=round((0.1+smoke/3600+dev/3600),2),use_if_h2_stop=round((0.1+(smoke+dev+h2)/3600),2))
    return out
designs={'S3 (registered draft)':{}, 'S3 without CS':dict(cs=0), 'S3 without CS and TR':dict(cs=0,tr=0),
         'S3 + 2,000 primary H2 cells (owner option)':dict(prim_twins=2000), 'S3 single LR (6 idx)':dict(n_idx=6),
         'S3 with 4,600 audit twins':dict(twins=4600)}
res={n:design(**kw) for n,kw in designs.items()}
print(json.dumps(res,indent=1))
