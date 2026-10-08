"""Synthesis power approximations for K1 v3 (normal approximations; not the registered simulation).
Seeded Monte Carlo (numpy seed 42) for the decision rule on xi with the combined interval."""
import numpy as np, math
from scipy import stats
rng=np.random.default_rng(42)
def xi_oc(true_xi, sd_cl, n_cl=70, infl=1.12, seed_sd=1.0, R=20000, true_rel=None):
    se_cl=sd_cl/math.sqrt(n_cl)*infl
    # simulate point = true + N(0,se_cl) + mean of 3 seed effects; s_seed from 3 draws
    seeds=rng.normal(0,seed_sd,(R,3)); clus=rng.normal(0,se_cl,R)
    point=true_xi+clus+seeds.mean(1); s_seed=seeds.std(1,ddof=1)
    var=se_cl**2+s_seed**2/3
    df=var**2/(se_cl**4/(n_cl-1)+(s_seed**2/3)**2/2)
    t=stats.t.ppf(0.995,df); hw=t*np.sqrt(var)
    go=(point>=10)&(point-hw>0)
    neg=(point<=5)&(point+hw<10)&(hw<=5)
    return go.mean(), neg.mean(), float(np.median(hw))
print('xi operating characteristics, one target (xi_rel conditions assumed to agree), 70 effective clusters, masking SE x1.12, seed SD 1')
for sd in (6,10,13.4,16):
    row=[]
    for tx in (0,2.5,5,9,10,11,12):
        g,n,h=xi_oc(tx,sd); row.append(f'xi={tx}: GO {g:.2f} NEG {n:.2f}')
    print(f' cluster SD {sd}: median HW {xi_oc(0,sd)[2]:.2f}; '+'; '.join(row))
# H2b pass probability (normal approx), ICC from development: 280 cells / 20 clusters, se 7.0006
sig2=4900.0
se_dev=7.000556; m_dev=14
v_cm=(se_dev*math.sqrt(20))**2
rho=(v_cm/sig2-1/m_dev)/(1-1/m_dev)
print(f'\nH2b: development ICC estimate {rho:.3f} (cluster-mean SD {math.sqrt(v_cm):.1f} points)')
def h2b_pass(true, cells, clusters):
    m=cells/clusters; v=sig2*(rho+(1-rho)/m); se=math.sqrt(v/clusters)
    t=stats.t.ppf(0.995,clusters-1); hw=t*se
    # pass: lower bound > 0 and point >= 5
    return stats.norm.cdf((true-hw)/se) if hw>5 else stats.norm.cdf((true-5)/se), se, hw
for cells,clusters,label in ((300,112,'K1 v1/v2 rule: 300 audit cells'),(2000,122,'2,000 audit cells'),(4600,122,'4,600 audit cells (all CX)'),(4000,366,'2,000 audit + 2,000 primary cells')):
    out=[]
    for true in (5,8.6,10,14):
        p,se,hw=h2b_pass(true,cells,clusters); out.append(f'true {true}: {p:.2f}')
    print(f' {label}: se {se:.2f}, 99% HW {hw:.2f}; '+'; '.join(out))
# per-layer NEGATIVE veto false-fire probability at true xi=0 everywhere (8 layers, layer SE = 1.5x macro SE, correlation 0.5 between layers)
for sd in (10,13.4):
    se=sd/math.sqrt(70)*1.12*1.5; R=200000
    cov=np.full((8,8),0.5*se**2); np.fill_diagonal(cov,se**2)
    z=rng.multivariate_normal(np.zeros(8),cov,R)
    t=stats.t.ppf(0.995,69); fire=((z>=10)&(z-t*se>0)).any(1).mean()
    # power to fire when one layer has true 15 (macro diluted to ~1.9)
    z2=z.copy(); z2[:,0]+=15; fire2=((z2>=10)&(z2-t*se>0)).any(1).mean()
    print(f'\nper-layer veto (cluster SD {sd}, layer SE {se:.2f}): P(fires | all layers 0) {fire:.4f}; P(fires | one layer at 15) {fire2:.2f}')
# lexical bound under a linear mixture: floor caps literal share lambda with lam*G_lex+(1-lam)*1 >= 0.5 at G_lex=0.237
lam=(1-0.5)/(1-0.237); print(f'\nliteral share bound from the unmasked floor: lambda <= {lam:.3f}; unmasked LEX xi 9.55 -> at most {lam*9.55:.2f} points of xi')
print(f'masked gate |LEX xi| <= 2.5 -> at most {lam*2.5:.2f} points of xi from a literal component')
