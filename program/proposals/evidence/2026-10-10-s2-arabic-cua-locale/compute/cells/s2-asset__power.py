from scipy import stats
import math, itertools
def mde(K, S, R, s2r, s2s_unpaired, s2tau, alpha=0.05, power=0.8):
    var_t = s2tau + 2*s2s_unpaired/S + 2*s2r/(S*R)
    se = math.sqrt(var_t/K)
    m = stats.t.ppf(1-alpha/2, K-1) + stats.t.ppf(power, K-1)
    return 100*m*se
print("K S R | s2r s2s s2tau | MDE pp")
for K,S,R in [(18,4,2),(18,5,5),(18,8,4),(18,10,4),(18,4,10),(36,4,4),(54,4,2),(60,4,4),(100,2,2)]:
    row=[]
    for s2r in (0.043,0.0625):
        for s2s in (0.0,0.01):
            for s2tau in (0.0,0.0025,0.0117):
                row.append(f"{mde(K,S,R,s2r,s2s,s2tau):5.1f}")
    print(K,S,R,'|',' '.join(row))
# threshold sigma_tau for 5pp at infinite replication, K=18
m = stats.t.ppf(0.975,17)+stats.t.ppf(0.8,17)
print("sigma_tau max for 5pp MDE at K=18, infinite reps:", 5/m*math.sqrt(18))
# episodes per locale needed for 5pp at K=18, s2tau=0, s2s=0
for s2r in (0.043,0.0625):
    nK = 2*s2r/((0.05/m)**2)
    print("s2r",s2r,"episodes per locale per arm needed (K=18, no heterogeneity):", math.ceil(nK), "per task", math.ceil(nK/18))
# K needed with S*R=8 and s2tau=0.0117, s2r=0.043
for K in range(18,200):
    if mde(K,4,2,0.043,0.0,0.0117) <= 5.0: print("K needed (S4R2, s2r .043, s2tau .0117):",K); break
for K in range(18,200):
    if mde(K,4,2,0.043,0.0,0.0025) <= 5.0: print("K needed (S4R2, s2r .043, s2tau .0025):",K); break
for K in range(18,200):
    if mde(K,4,2,0.043,0.0,0.0) <= 5.0: print("K needed (S4R2, s2r .043, s2tau 0):",K); break
print("--- K_eff = 7 (controls + thread-repair only off the floor)")
for S,R in [(4,2),(10,4)]:
    print(S,R,[round(mde(7,S,R,s2r,s2s,s2t),1) for s2r in (0.043,0.0625) for s2s in (0,0.01) for s2t in (0,0.0025,0.0117)])
# cost arithmetic
P_s1a = 0.002701/((11.77+11.80)/2)
P_gpu = 1/(2.55*3600)*370/300
print("P_s1a GPU-h/step", P_s1a, "P_gpu", P_gpu)
def cost(n_pix, n_a11y, steps, P, margin=1.0, ctx=1.0):
    return (n_pix + 1.5*n_a11y)*steps*P*margin*ctx
for name,(npx,na) in {"dossier 864":(432,432),"powered 2160+108":(2160,108),"relay floor pilot 144+18":(162,0)}.items():
    print(name, "low", round(cost(npx,na,24,P_gpu),2), "central", round(cost(npx,na,24,P_s1a,1.2),2), "high", round(cost(npx,na,36,P_s1a,1.2,1.3),2))
