# Analytic paired-MDE for a within-task locale contrast, task-clustered.
# Per-task difference d_k = mean_R(B) - mean_R(A); Var(d_k) = tau2 + 2*s2/R
# s2 = mean within-cell Bernoulli variance = D/2 (D = rerun discordance rate; S1a D_w 0.125, D_b 0.113)
# tau2 = variance of true task-specific locale effects (unknown; S1a's harness analogue X_c 0.008-0.015)
# Inference: paired t on K task means (df=K-1), two-sided alpha .05, power .80.
from scipy import stats
import math
def mde(K,R,tau2,D):
    s2=D/2; se=math.sqrt((tau2+2*s2/R)/K)
    return (stats.t.ppf(0.975,K-1)+stats.t.ppf(0.80,K-1))*se
def tost_se_needed(K,margin=0.05):
    return margin/(stats.t.ppf(0.95,K-1)+stats.t.ppf(0.90,K-1))
print("MDE (pp), D=0.12 (S1a floor)")
print("K   R  " + "  ".join(f"tau2={t:<6}" for t in [0,0.0025,0.005,0.01,0.015]))
for K in [18,32,48,64,96,113]:
    for R in [2,4,8,16,1e9]:
        row=[f"{100*mde(K,R,t,0.12):6.1f}    " for t in [0,0.0025,0.005,0.01,0.015]]
        print(f"{K:<3} {('inf' if R>1e6 else int(R)):<3}", " ".join(row))
print()
# Smallest K for MDE<=5pp
for tau2 in [0,0.0025,0.005,0.01,0.015]:
    out=[]
    for R in [4,8,16,32]:
        K=next((k for k in range(3,2000) if mde(k,R,tau2,0.12)<=0.05),None); out.append(f"R={R}:K>={K}")
    print(f"tau2={tau2}: "+", ".join(out))
print()
# TOST at +/-5pp, true delta=0: needed SE and K
for tau2 in [0,0.005,0.01]:
    for R in [8,16]:
        K=next(k for k in range(3,3000) if math.sqrt((tau2+0.12/R)/k)<=tost_se_needed(k))
        print(f"TOST +/-5pp 80% power, tau2={tau2}, R={R}: K>={K}")
print()
# 3-cell vs 2x2 efficiency for the mirror contrast (rerun component only), equal episodes N
# 3 cells, n per cell: var(arRTL-arLTR) per task = 2 s2/n, episodes 3n
# 2x2 main effect: 0.5[(enRTL-en)+(arRTL-arLTR)]: var = s2/n, episodes 4n
print("episode-matched variance ratio, 3-cell conditional contrast vs 2x2 main effect (no interaction):", (2/1)*(4/3)/ (4/4) / (4/3) )
s2=0.06
for N in [432*2]:
    n3=N/3/18; n4=N/4/18
    print("N",N,"per task-cell reruns 3-cell",round(n3,1),"var",2*s2/n3," | 2x2",round(n4,1),"var main",s2/n4, "var interaction", 4*s2/n4)
