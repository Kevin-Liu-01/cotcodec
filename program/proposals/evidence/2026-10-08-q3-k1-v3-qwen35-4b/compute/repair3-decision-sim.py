"""K1 v3 repair under D52, simulation S3: the decision rules of the third repair on measured inputs.

S3 extends S2 (repair-decision-sim.py, imported, its statistics validated against the registered K1
code) where wave 2 found S2's inputs assumed rather than measured:

1. Design (measured): the controlled questions sit in passage clusters as on the development text
   (110 controlled of 224 questions in 66 of 122 links; stage-0 facts, repair3-stage0-dev-facts.json).
   The audit links (230 questions in 122 links, K1) take numbers of controlled questions in the
   development link profile's proportions given their number of questions (113 controlled questions
   in 67 links; which links, design seed 42). S2 drew controlled questions independently of passage
   (115 in 89 clusters).
2. Evidence sizes (measured): every simulated family takes |N^M|, |N^LF| (r = 2) and |N^PRE| of a
   development family of the same pair (the same development question across pairs); a family with
   |N^M| below 32 is excluded (development rate 1.5 percent, S2 assumed 10).
3. LF and PRE are statistics, not xi^M plus N(0, 0.4 or 0.8): each is computed from per-family,
   per-layer, per-seed recalls on its own families with the cluster bootstrap and the layer-resolved
   seed term. The family-level noise of a subset of n_X of a family's n_M unmasked tokens is the
   family's masked noise plus an independent part with variance (n_M / n_X - 1) times the family-level
   variance (nested block sampling; all family-level noise treated as sampling noise, the
   conservative direction). LF uses families with |N^LF| >= 32 (development 0.67); PRE is the
   repaired pooled statistic: families with at least one complete pre-literal block (development
   0.53-0.67), each weighted by its pre-literal tokens (17 percent of the unmasked tokens).
4. Sensitivity kappa (bounded, not assumed): LF and PRE see kappa_X of the indexer's loss. Even
   spread gives 1; the measured answer-sentence bound (the loss sits only on the English answer
   sentence carried by sentence index) gives LF 0.74-0.77 and pooled PRE 1.15-1.17 on the
   development text. Rows use 1 / 1 (even) or 0.74 / 1.0 (measured bound, PRE capped at 1), and
   one stress row S1's 0.68 / 0.53.
5. Non-additive generators: besides S2's additive model, a multiplicative model (the indexer keeps
   a factor r_q of its target headroom on a question in an unseen script, r_p on a passage in an
   unseen script and r_m when the two scripts differ; null r_m = 1) and a floor-saturating additive
   model (the expected indexer recall cannot fall below random).
6. Decision rules: S2's repaired rules with PRE removed (what the draft would register, since PRE
   fails its 40 percent fallback on the development text), and the third repair's rules
   (registration "Decision rules"): GO adds the pooled PRE condition, both directions (points at
   least 5, 99 percent lower bounds above 0), the direction floor (99 percent lower bound of G^M(MN)
   at least 0.5 in each direction) and the log-retention co-statistic (99 percent lower bound above
   0); NEGATIVE as S2's repaired rules with LF and PRE computed as statistics.
7. Seeds: three, or five through the seed top-up (decision 81 as revised).

Modes: `validate` (S2's K1 validation on the new design, and this file's generic pair statistics
against S2's read_target), `run <out.json>` (resumable: rows keyed by scenario and seeded from it).
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("s2", os.path.join(HERE, "repair-decision-sim.py"))
s2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s2)
k = s2.k
FACTS = json.load(open(os.environ.get("S3_FACTS", os.path.join(HERE, "repair3-stage0-dev-facts.json"))))
RAND, G_RET, NP = s2.RAND, s2.G_RET, s2.NP
UNSEEN, UE, UX, SEEN = np.array(s2.UNSEEN), np.array(s2.UE), np.array(s2.UX), np.array(s2.SEEN)
PAIR_NAMES = ([f"{x}>en" for x in ("bn", "el", "he", "ja", "ka", "ko", "ta")]
              + [f"en>{x}" for x in ("bn", "el", "he", "ja", "ka", "ko", "ta")]
              + [f"{x}>en" for x in ("th", "hi", "km")] + [f"en>{x}" for x in ("th", "hi", "km")])
B = s2.B
LOG_FLOOR = 0.05

# ----------------------------------------------------------------------------- design (measured)
PROFILE = {tuple(int(v) for v in key.split(",")): c for key, c in FACTS["link_profile_n_questions_n_controlled"].items()}


def clustered_design(seed: int = 42):
    """Proportional allocation: among the audit links with a given number of questions (1 or 2), the
    numbers of controlled questions follow the development link profile in proportion (largest
    remainders); which links get which number is drawn with the design seed."""
    rng = np.random.default_rng(seed)
    n_q_link = np.bincount(s2.Q_CL, minlength=s2.N_CL)
    ctrl = []
    for nq in (1, 2):
        links = np.flatnonzero(n_q_link == nq)
        opts = sorted((c, w) for (a, c), w in PROFILE.items() if a == nq)
        share = np.array([w for _, w in opts], float) / sum(w for _, w in opts) * links.size
        alloc = np.floor(share).astype(int)
        for i in np.argsort(-(share - alloc))[: links.size - alloc.sum()]:
            alloc[i] += 1
        n_c = np.repeat([c for c, _ in opts], alloc)
        rng.shuffle(n_c)
        for link, c in zip(links, n_c):
            qs = np.flatnonzero(s2.Q_CL == link)
            ctrl.extend(sorted(rng.choice(qs, int(c), replace=False).tolist()))
    ctrl_q = np.array(sorted(ctrl))
    return ctrl_q, np.unique(s2.Q_CL[ctrl_q])


def install_design(ctrl_q, links):
    s2.CTRL_Q, s2.LINKS = ctrl_q, links
    s2.N_CLU = links.size
    s2.W = k._cluster_weights(s2.N_CLU, B, k.BOOTSTRAP_SEED)
    s2.QIDX = {int(q): i for i, q in enumerate(ctrl_q)}
    s2.CLU_OF_Q = np.searchsorted(links, s2.Q_CL[ctrl_q])


install_design(*clustered_design(int(os.environ.get("S3_DESIGN_SEED", "42"))))

# ----------------------------------------------------------------------------- evidence sizes (measured)
_PF = FACTS["per_family_registered_proxy_offset0"]
DEV_Q = sorted({(f["link"], f["q"]) for f in _PF})
EVID = {}
for f in _PF:
    EVID[(f["pair"], (f["link"], f["q"]))] = (f["nM"], f["nLF2"], f["nPRE"], f["nPRE_blocks"])
_rngd = np.random.default_rng(42)
DEV_OF_Q = _rngd.integers(0, len(DEV_Q), s2.CTRL_Q.size)        # audit controlled question -> dev question


def family_evidence(pairs, qs):
    ev = np.array([EVID[(PAIR_NAMES[p], DEV_Q[DEV_OF_Q[q]])] for p, q in zip(pairs, qs)], float)
    return ev   # (F, 4): nM, nLF2, nPRE, nPRE_blocks


def build_families(rng):
    pairs, qs = np.meshgrid(np.arange(NP), np.arange(s2.CTRL_Q.size), indexing="ij")
    pairs, qs = pairs.ravel(), qs.ravel()
    ev = family_evidence(pairs, qs)
    keep = ev[:, 0] >= 32
    return pairs[keep], qs[keep], ev[keep]


# ----------------------------------------------------------------------------- generation

def retention(sc):
    """(NP, 2) multiplicative retention; leg 0 = MN, 1 = CX."""
    ret = np.ones((NP, 2))
    for st, px, pe in (("u", UX, UE), ("s", s2.SX, s2.SE)):
        rq, rp, rm = sc.get(f"r_q_{st}", 1.0), sc.get(f"r_p_{st}", 1.0), sc.get(f"r_m_{st}", 1.0)
        for p in pe:    # English needle: MN en/en; CX q in X
            ret[p] = (1.0, rq * rm)
        for p in px:    # X needle: MN q X, p X; CX q en, p X
            ret[p] = (rq * rp, rp * rm)
    return ret


def generate3(rng, sc, n_seeds, se_scale, pairs, qs, ev):
    nq = s2.CTRL_Q.size
    m = sc["H"] / s2.H_DEV_CX
    F = pairs.size
    en = s2.EN_NEEDLE[pairs]
    clu = s2.CLU_OF_Q[qs]
    direction = en.astype(int)
    hpair = s2.H_PAIR[pairs] / s2.H_PAIR[s2.UNSEEN].mean(axis=0)
    H = m * s2.H_LAYER[:, None, :] * hpair[None, :, :]
    hbar = H.mean(axis=0, keepdims=True)
    a_q = rng.normal(0, 6, nq)
    eta = rng.normal(0, 4, (F, 2)); eta_en = rng.normal(0, 4, nq); eta[en, 0] = eta_en[qs[en]]
    eta_l = rng.normal(0, 3, (8, F, 2)); eta_l_en = rng.normal(0, 3, (8, nq)); eta_l[:, en, 0] = eta_l_en[:, qs[en]]
    tgt = np.clip(RAND + H + H / np.maximum(hbar, 1e-9) * (a_q[qs][None, :, None] + eta[None]) + eta_l, 0, 100)
    sd_cl, sd_f = 7.0 * se_scale, 9.0 * se_scale
    NU = s2.NU[:, None, None]

    def shared_en(shape_f, shape_q):
        x = rng.normal(0, 1, shape_f)
        xe = rng.normal(0, 1, shape_q)
        x[..., en, 0] = xe[..., qs[en]]
        return x

    def draw():
        u = rng.normal(0, 1, (s2.N_CLU, 2, 2)); ul = rng.normal(0, 1, (8, s2.N_CLU, 2, 2))
        cl = np.take_along_axis(u[clu], direction[:, None, None], axis=2)[..., 0]
        cll = np.take_along_axis(ul[:, clu], direction[None, :, None, None], axis=3)[..., 0]
        w = shared_en((F, 2), (nq,)); wl = shared_en((8, F, 2), (8, nq))
        return sd_cl * (cl[None] + s2.LAMBDA_L * cll) * NU, sd_f * (w[None] + s2.LAMBDA_L * wl) * NU

    def fam_extra():    # an independent copy of the family-level components (per seed for v)
        w = shared_en((F, 2), (nq,)); wl = shared_en((8, F, 2), (8, nq))
        v = rng.normal(0, s2.SD_V, (n_seeds, 8, F, 2)); ve = rng.normal(0, s2.SD_V, (n_seeds, 8, nq))
        v[:, :, en, 0] = ve[:, :, qs[en]]
        return (sd_f * (w[None] + s2.LAMBDA_L * wl) * NU)[None] + v

    model = sc.get("model", "additive")
    eff = s2.effect_matrix(sc)[:, pairs, :]
    ret = retention(sc)[pairs]                                            # (F, 2)
    f_lf = np.maximum(ev[:, 0] / np.maximum(ev[:, 1], 1.0) - 1.0, 0.0)[None, None, :, None]
    f_pre = np.maximum(ev[:, 0] / np.maximum(ev[:, 2], 1.0) - 1.0, 0.0)[None, None, :, None]
    shared_cl, shared_f = draw()
    ex_shared = {"lf": fam_extra(), "pre": fam_extra()}
    s0 = sc["seed_sd"] * 8.0 / math.sqrt(1.125 * float((s2.NU ** 2).sum()))
    out = {}
    for t_i, tname in enumerate(("hs", "mp")):
        own_cl, own_f = draw()
        mix = (lambda a, b: a) if t_i == 0 else (lambda a, b: 0.7 * a + math.sqrt(0.51) * b)
        noise = mix(shared_cl, own_cl) + mix(shared_f, own_f)
        tgt_t = RAND + (1.0 if tname == "hs" else 0.97) * (tgt - RAND)
        full = RAND + G_RET * (tgt_t - RAND)
        if model == "multiplicative":
            mean = RAND + G_RET * ret[None] * (tgt_t - RAND)
        elif model == "floor":
            mean = np.maximum(RAND, full - eff)
        else:
            mean = full - eff
        loss = full - mean
        d = rng.normal(0, 1, (n_seeds, 8)) * s0 * s2.NU[None, :]
        dd = rng.normal(0, 1, (n_seeds, 8, 2)) * 0.5 * s0 * s2.NU[None, :, None]
        v = rng.normal(0, s2.SD_V, (n_seeds, 8, F, 2)); ve = rng.normal(0, s2.SD_V, (n_seeds, 8, nq))
        v[:, :, en, 0] = ve[:, :, qs[en]]
        seed_cx = np.zeros((n_seeds, 8, F, 2))
        seed_cx[..., 1] = d[:, :, None] + dd[:, :, direction]
        base = noise[None] + v + seed_cx
        ex_own = {"lf": fam_extra(), "pre": fam_extra()}
        res = {}
        for kind, kap, rlit, f_x in (("M", 1.0, 1.0, None), ("LF", sc.get("kappa_lf", 1.0), sc.get("r_lf", 0.0), f_lf),
                                     ("PRE", sc.get("kappa_pre", 1.0), sc.get("r_pre", 0.0), f_pre)):
            ind = (full - kap * loss)[None] + base
            if f_x is not None:
                key = kind.lower()
                ind = ind + np.sqrt(f_x) * mix(ex_shared[key], ex_own[key])
            ind[..., 0] += rlit * sc.get("b_lit", 0.0)
            res[kind] = np.clip(ind, 0, 100)
        out[tname] = (res, np.clip(tgt_t, 0, 100))
    return out


# ----------------------------------------------------------------------------- statistics

def pstats(ind, tgt, pairs, qs, wfam):
    """Weighted pair-cluster sums (K1's form: cluster x pair sums, macro over pairs, replicate ratio of
    weighted sums). ind (S, 8, F, 2), tgt (8, F, 2), wfam (F,) >= 0. Returns layer-mean pair means
    pi, pt (2 legs, NP), bootstrap bi, bt (2, B, NP), per-seed per-layer pm_ind (S, 8, NP, 2)."""
    clu = s2.CLU_OF_Q[qs]
    Mx = s2.cell_matrix(pairs, clu)
    wsum = s2.sums_cp(wfam, Mx)                              # (C, NP)
    wc = s2.W @ wsum                                         # (B, NP)
    cnt = wsum.sum(axis=0)
    ind_l = ind.mean(axis=0).mean(axis=0)                     # (F, 2) seed and layer mean
    tgt_l = tgt.mean(axis=0)
    V = np.stack([ind_l.T, tgt_l.T]) * wfam                  # (2 kinds, 2 legs, F)
    S = s2.sums_cp(V, Mx)                                     # (2, 2, C, NP)
    with np.errstate(invalid="ignore", divide="ignore"):
        P = S.sum(axis=2) / cnt
        Bv = np.tensordot(s2.W, S.reshape(-1, s2.N_CLU, NP), axes=([1], [1]))   # (B, 4, NP)
        Bv = np.moveaxis(Bv, 0, 1).reshape(2, 2, B, NP) / wc
        oh = np.zeros((pairs.size, NP)); oh[np.arange(pairs.size), pairs] = wfam / cnt[pairs]
    pm_ind = np.moveaxis(np.moveaxis(ind, 2, -1) @ oh, -2, -1)   # (S, 8, NP, 2)
    pm_tgt = np.moveaxis(np.moveaxis(tgt, 1, -1) @ oh, -2, -1)   # (8, NP, 2)
    return dict(pi=P[0], pt=P[1], bi=Bv[0], bt=Bv[1], pm_ind=pm_ind, pm_tgt=pm_tgt)


def stat_xi(st, pset, sign=None):
    pi, pt, bi, bt = st["pi"], st["pt"], st["bi"], st["bt"]
    ex_p = (pi[0] - pi[1]) - (pt[0] - pt[1])
    ex_b = (bi[0] - bi[1]) - (bt[0] - bt[1])
    ex_sl = (st["pm_ind"][..., 0] - st["pm_ind"][..., 1]) - (st["pm_tgt"][None, ..., 0] - st["pm_tgt"][None, ..., 1])
    pset = np.asarray(pset)
    pt_ = float(ex_p[pset].mean()); bt_ = ex_b[:, pset].mean(axis=1)
    contrib = ex_sl[:, :, pset].mean(axis=2) / 8.0
    v, df = s2.layer_resolved(contrib)
    return s2.interval(pt_, float(bt_.std(ddof=1)), v, df)


def stat_log(st, pset):
    """Log-retention co-statistic: macro over pairs of log G(MN) - log G(CX), G on pair-condition means
    (floor 0.05); seed term by the delta method on the per-layer, per-seed contributions."""
    pi, pt, bi, bt, pm = st["pi"], st["pt"], st["bi"], st["bt"], st["pm_ind"]
    pset = np.asarray(pset)
    hp = pt - RAND
    hb = np.maximum(bt - RAND, k.HEADROOM_FLOOR_POINTS)
    g = np.maximum((pi - RAND) / hp, LOG_FLOOR)
    gb = np.maximum((bi - RAND) / hb, LOG_FLOOR)
    point = float((np.log(g[0, pset]) - np.log(g[1, pset])).mean())
    rep = (np.log(gb[0][:, pset]) - np.log(gb[1][:, pset])).mean(axis=1)
    c = (((pm[..., pset, 0] - RAND) / hp[0, pset]) / g[0, pset] - ((pm[..., pset, 1] - RAND) / hp[1, pset]) / g[1, pset]).mean(axis=2) / 8.0
    v, df = s2.layer_resolved(c)
    return s2.interval(point, float(rep.std(ddof=1)), v, df)


def floor_dir(st, pset):
    hb = np.maximum(st["bt"] - RAND, k.HEADROOM_FLOOR_POINTS)
    gb = (st["bi"] - RAND) / hb
    return float(np.percentile(gb[0][:, np.asarray(pset)].mean(axis=1), 0.5))


def read3(data, pairs, qs, ev, sc, n_seeds):
    res, tgt = data
    out = {}
    r = s2.read_target(res["M"], tgt, pairs, qs, sc, n_seeds, None)
    stM = pstats(res["M"], tgt, pairs, qs, np.ones(pairs.size))
    r["log"] = stat_log(stM, UNSEEN)
    r["floor_E"], r["floor_X"] = floor_dir(stM, UE), floor_dir(stM, UX)
    w_lf = (ev[:, 1] >= 32).astype(float)
    w_pre = np.where(ev[:, 3] >= 1, ev[:, 2], 0.0)
    w_pre32 = (ev[:, 2] >= 32).astype(float)
    r["lf"] = stat_xi(pstats(res["LF"], tgt, pairs, qs, w_lf), UNSEEN)
    r["pre"] = stat_xi(pstats(res["PRE"], tgt, pairs, qs, w_pre), UNSEEN)
    r["pre32"] = stat_xi(pstats(res["PRE"], tgt, pairs, qs, w_pre32), UNSEEN)
    return r


# ----------------------------------------------------------------------------- rules

def verdicts3(reads, sc):
    tau = (5.0 / sc["H"], 10.0 / sc["H"])

    def neg(r, pre_key="pre", pre_rule="band"):
        xi, rel = r["xi"]["lr"], r["xi_rel"]["lr"]
        ok = (abs(xi["point"]) <= 5 and xi["lo"] > -10 and xi["hi"] < 10 and xi["hw"] <= 5
              and abs(rel["point"]) <= tau[0] and rel["lo"] > -tau[1] and rel["hi"] < tau[1]
              and r["floor_lb"] >= 0.5)
        lab = []
        if abs(r["xi_E"]["lr"]["point"]) > 5 or abs(r["xi_X"]["lr"]["point"]) > 5:
            lab.append("DIRECTION")
        e = r["xi_E"]["lr"]
        if not (e["lo"] > -10 and e["hi"] < 10):
            lab.append("ENGLISH_NEEDLE")
        if abs(r["seen"]["lr"]["point"]) > 5:
            lab.append("SEEN")
        for L in r["layer"]:
            iv = L["rel"]
            if L["evaluable"] and abs(iv["point"]) >= 0.2 and (iv["lo"] > 0 or iv["hi"] < 0):
                lab.append("LAYER"); break
        lit = [abs(r["lf"]["point"]) > 5]
        if pre_key and pre_rule == "band":
            lit.append(abs(r[pre_key]["point"]) > 5)
        elif pre_key:     # PRE blocks only when it is outside the band and its interval excludes 0
            iv = r[pre_key]
            lit.append(abs(iv["point"]) > 5 and (iv["lo"] > 0 or iv["hi"] < 0))
        if any(lit):
            lab.append("LITERAL")
        return ok and not lab, lab

    def go_w2(r, pre_key=None):
        xi, rel = r["xi"]["lr"], r["xi_rel"]["lr"]
        ok = xi["point"] >= 10 and xi["lo"] > 0 and rel["lo"] > 0 and r["lf"]["point"] >= 5
        return ok and (pre_key is None or r[pre_key]["point"] >= 5)

    def go3(r, pre_lb=False, need=("dir", "floor", "log", "pre")):
        lab = []
        if not go_w2(r):
            return False, lab
        if "pre" in need and not (r["pre"]["point"] >= 5 and (not pre_lb or r["pre"]["lo"] > 0)):
            lab.append("LITERAL_CHANNEL")
        if "dir" in need:
            e, x = r["xi_E"]["lr"], r["xi_X"]["lr"]
            if not (e["point"] >= 5 and e["lo"] > 0 and x["point"] >= 5 and x["lo"] > 0):
                lab.append("DIRECTION_SPLIT")
        if "floor" in need and not (r["floor_E"] >= 0.5 and r["floor_X"] >= 0.5):
            lab.append("DIRECTION_FLOOR")
        if "log" in need and not r["log"]["lo"] > 0:
            lab.append("SCALE")
        return not lab, lab

    variants = {
        "wave2_registered_pre_dropped": (lambda r: (go_w2(r), []), lambda r: neg(r, None)),
        "wave2_with_pre32": (lambda r: (go_w2(r, "pre32"), []), lambda r: neg(r, "pre32")),
        "repair3": (lambda r: go3(r), lambda r: neg(r)),
        "repair3_pre_lb": (lambda r: go3(r, pre_lb=True), lambda r: neg(r)),
        "repair3_neg_pre_significant": (lambda r: go3(r), lambda r: neg(r, pre_rule="signif")),
        "repair3_without_pre": (lambda r: go3(r, need=("dir", "floor", "log")), lambda r: neg(r)),
        "repair3_without_direction_floor_log": (lambda r: go3(r, need=("pre",)), lambda r: neg(r)),
    }
    out = {}
    for name, (gf, nf) in variants.items():
        gos = [gf(r) for r in reads.values()]
        go = any(g[0] for g in gos)
        negs = [nf(r) for r in reads.values()]
        out[name] = dict(go=go, neg=(not go) and all(n[0] for n in negs),
                         labels=sorted({l for n in negs for l in n[1]} | ({l for g in gos for l in g[1]} if not go else set())))
    return out


def one(args):
    seed, sc, n_seeds, se_scale = args
    rng = np.random.default_rng(seed)
    pairs, qs, ev = build_families(rng)
    data = generate3(rng, sc, n_seeds, se_scale, pairs, qs, ev)
    reads = {t: read3(d, pairs, qs, ev, sc, n_seeds) for t, d in data.items()}
    hs = reads["hs"]
    diag = dict(xi=hs["xi"]["lr"]["point"], hw=hs["xi"]["lr"]["hw"], se_cl=hs["xi"]["lr"]["se_cl"],
                xi_E=hs["xi_E"]["lr"]["point"], xi_X=hs["xi_X"]["lr"]["point"], rel=hs["xi_rel"]["lr"]["point"],
                log=hs["log"]["point"], log_hw=hs["log"]["hw"], lf=hs["lf"]["point"], lf_hw=hs["lf"]["hw"],
                pre=hs["pre"]["point"], pre_hw=hs["pre"]["hw"], pre32_hw=hs["pre32"]["hw"],
                floor_E=hs["floor_E"], floor_X=hs["floor_X"], floor_lb=hs["floor_lb"])
    return verdicts3(reads, sc), diag


def run_row(sc, n_seeds, se_scale, reps, pool):
    tag = json.dumps(sc, sort_keys=True) + f"|{n_seeds}|{se_scale}|s3"
    seeds = [zlib.crc32(tag.encode()) * 100003 + i for i in range(reps)]
    res = pool.map(one, [(s, sc, n_seeds, se_scale) for s in seeds], chunksize=2)
    out = {}
    for name in res[0][0]:
        lab = {}
        for r in res:
            for l in r[0][name]["labels"]:
                lab[l] = lab.get(l, 0) + 1
        out[name] = dict(P_GO=float(np.mean([r[0][name]["go"] for r in res])),
                         P_NEG=float(np.mean([r[0][name]["neg"] for r in res])),
                         label_rates={l: c / reps for l, c in sorted(lab.items())})
        out[name]["P_decisive"] = out[name]["P_GO"] + out[name]["P_NEG"]
    out["diagnostics_hs_median"] = {key: float(np.median([r[1][key] for r in res])) for key in res[0][1]}
    out["diagnostics_hs_median"]["sd_xi"] = float(np.std([r[1]["xi"] for r in res]))
    out["diagnostics_hs_median"]["sd_pre"] = float(np.std([r[1]["pre"] for r in res]))
    out["diagnostics_hs_median"]["sd_lf"] = float(np.std([r[1]["lf"] for r in res]))
    return out


def validate():
    """(a) S2's K1-estimator interval against the registered K1 code on this design; (b) this file's
    weighted pair statistics with unit weights against S2's read_target on the same draws."""
    rep = dict(s2_k1_validation=s2.validate())
    rng = np.random.default_rng(11)
    worst = 0.0
    for trial in range(3):
        pairs, qs, ev = build_families(rng)
        sc = dict(H=30.0, seed_sd=1.5, gamma_u=4.0 * trial, alpha_u=2.0)
        res, tgt = generate3(rng, sc, 3, 1.5, pairs, qs, ev)["hs"]
        r = s2.read_target(res["M"], tgt, pairs, qs, sc, 3, None)
        st = pstats(res["M"], tgt, pairs, qs, np.ones(pairs.size))
        for key, ps in (("xi", UNSEEN), ("xi_E", UE), ("xi_X", UX), ("seen", SEEN)):
            mine = stat_xi(st, ps)
            for f in ("point", "se_cl", "v_seed", "hw"):
                worst = max(worst, abs(mine[f] - r[key]["lr"][f]))
        worst = max(worst, abs(floor_dir(st, UNSEEN) - r["floor_lb"]))
    rep["generic_vs_read_target_max_abs_difference"] = worst
    rep["design"] = dict(controlled_questions=int(s2.CTRL_Q.size), clusters=int(s2.N_CLU))
    return rep


def plan():
    rows = []
    ME = dict(kappa_lf=0.74, kappa_pre=1.0)          # measured answer-sentence bound
    # A: additive null and alternatives, both kappa settings at H 30; H 20 / 40 with the measured bound
    for H in (20.0, 30.0, 40.0):
        for s in ((0.5, 1.0, 2.0, 3.0) if H == 30.0 else (1.0, 2.0, 3.0)):
            for g in (0.0, 5.0, 7.5, 10.0, 12.0, 15.0):
                if g == 7.5 and H != 30.0:
                    continue
                rows.append(("A", dict(H=H, seed_sd=s, gamma_u=g, **ME), 3, s2.SE_MID))
    for s in (1.0, 2.0):
        for g in (0.0, 12.0, 15.0):
            rows.append(("A_even_kappa", dict(H=30.0, seed_sd=s, gamma_u=g), 3, s2.SE_MID))
    # B: identification scenarios at H 30 (40 for the multiplicative nulls), seed SD 1
    base = dict(H=30.0, seed_sd=1.0, **ME)
    for name, extra in (
        ("mult_null_r0.2_H40", dict(H=40.0, model="multiplicative", r_q_u=0.2, r_p_u=0.2)),
        ("mult_null_r0.35_H40", dict(H=40.0, model="multiplicative", r_q_u=0.35, r_p_u=0.35)),
        ("mult_null_r0.5_H40", dict(H=40.0, model="multiplicative", r_q_u=0.5, r_p_u=0.5)),
        ("mult_null_r0.7_H40", dict(H=40.0, model="multiplicative", r_q_u=0.7, r_p_u=0.7)),
        ("mult_null_r0.85_H40", dict(H=40.0, model="multiplicative", r_q_u=0.85, r_p_u=0.85)),
        ("mult_null_r0.35_H30", dict(model="multiplicative", r_q_u=0.35, r_p_u=0.35)),
        ("mult_null_rq0.3_only", dict(H=40.0, model="multiplicative", r_q_u=0.3)),
        ("mult_null_rp0.3_only", dict(H=40.0, model="multiplicative", r_p_u=0.3)),
        ("mult_null_rq0.5_rp0.2_H40", dict(H=40.0, model="multiplicative", r_q_u=0.5, r_p_u=0.2)),
        ("mult_alt_rm0.6", dict(model="multiplicative", r_m_u=0.6)),
        ("mult_alt_rm0.5", dict(model="multiplicative", r_m_u=0.5)),
        ("mult_alt_rm0.6_rq0.8_rp0.8", dict(model="multiplicative", r_m_u=0.6, r_q_u=0.8, r_p_u=0.8)),
        ("floor_null_alpha20_beta20_H30", dict(model="floor", alpha_u=20.0, beta_u=20.0)),
        ("floor_null_alpha25_beta25_H40", dict(H=40.0, model="floor", alpha_u=25.0, beta_u=25.0)),
        ("floor_null_alpha15_beta30_H30", dict(model="floor", alpha_u=15.0, beta_u=30.0)),
        ("alpha6", dict(alpha_u=6.0)), ("alpha10", dict(alpha_u=10.0)), ("beta10", dict(beta_u=10.0)),
        ("gamma12_alpha6", dict(gamma_u=12.0, alpha_u=6.0)),
        ("layer3_total_failure", dict(layer_extra=(0, 0.8))),
        ("layer31_15pts", dict(layer_extra=(7, 15.0 / (s2.H_LAYER[7, 1] * 30.0 / s2.H_DEV_CX)))),
        ("seen_excess8", dict(gamma_s=8.0)),
        ("spill_plus10_gamma0_ell3", dict(b_lit=9.9, r_lf=1.0, r_pre=-0.1)),
        ("spill_plus6_gamma5_ell3", dict(gamma_u=5.0, b_lit=6.0, r_lf=1.0, r_pre=-0.3)),
        ("spill_plus10_gamma0_ell3_H40", dict(H=40.0, b_lit=9.9, r_lf=1.0, r_pre=-0.1)),
        ("spill_plus15_gamma0_ell3", dict(b_lit=15.0, r_lf=1.0, r_pre=-0.1)),
        ("gamma10_displacement_minus8", dict(gamma_u=10.0, b_lit=-8.0, r_lf=0.0, r_pre=0.07)),
        ("gamma7.5_displacement_minus4", dict(gamma_u=7.5, b_lit=-4.0, r_lf=0.0, r_pre=0.05)),
        ("gamma0_displacement_minus3.6", dict(b_lit=-3.6, r_lf=0.0, r_pre=0.0)),
        ("gamma7.5_antispill", dict(gamma_u=7.5, b_lit=-5.3, r_lf=0.52, r_pre=-0.09)),
        ("gamma8_displacement_minus4_s1_concentrated", dict(gamma_u=8.0, b_lit=-4.0, r_lf=0.0, r_pre=0.05, kappa_lf=0.68, kappa_pre=0.53)),
        ("gamma12_s1_concentrated", dict(gamma_u=12.0, kappa_lf=0.68, kappa_pre=0.53)),
        ("gamma12_measured_bound", dict(gamma_u=12.0)),
    ):
        rows.append(("B:" + name, {**base, **extra}, 3, s2.SE_MID))
    # C: noise scale at H 30
    for se in (s2.SE_LOW, s2.SE_HIGH):
        for s in (1.0, 2.0):
            for g in (0.0, 12.0):
                rows.append(("C", dict(H=30.0, seed_sd=s, gamma_u=g, **ME), 3, se))
    # D: five seeds (the seed top-up)
    for H in (20.0, 30.0, 40.0):
        for s in (1.0, 2.0, 3.0):
            for g in (0.0, 5.0, 12.0, 15.0):
                rows.append(("D5", dict(H=H, seed_sd=s, gamma_u=g, **ME), 5, s2.SE_MID))
    order = {"B": 0, "A": 1, "C": 2, "D": 3}
    return sorted(rows, key=lambda r: order[r[0][0]])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "validate":
        print(json.dumps(validate(), indent=1, default=float))
        return
    reps = int(os.environ.get("S3_REPS", "400"))
    reps_b = int(os.environ.get("S3_REPS_B", "800"))
    path = sys.argv[2]
    only = os.environ.get("S3_ONLY")
    out = json.load(open(path)) if os.path.exists(path) else {
        "parameters": dict(B=B, reps=reps, reps_table_B=reps_b, design_seed=int(os.environ.get("S3_DESIGN_SEED", "42")),
                           controlled_questions=int(s2.CTRL_Q.size), clusters=int(s2.N_CLU),
                           g=G_RET, log_floor=LOG_FLOOR, facts_sha256=None), "rows": []}
    done = {(r["table"], json.dumps(r["scenario"], sort_keys=True), r["n_seeds"], r["se_scale"]) for r in out["rows"]}
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        for table, sc, n_seeds, se in plan():
            if only and not table.startswith(only):
                continue
            key = (table, json.dumps(sc, sort_keys=True), n_seeds, se)
            if key in done:
                continue
            n_rep = reps_b if table.startswith("B") else reps
            r = run_row(sc, n_seeds, se, n_rep, pool)
            out["rows"].append(dict(table=table, scenario=sc, n_seeds=n_seeds, se_scale=se, reps=n_rep, result=r))
            brief = {v: (round(r[v]["P_GO"], 3), round(r[v]["P_NEG"], 3)) for v in ("wave2_registered_pre_dropped", "repair3")}
            d = r["diagnostics_hs_median"]
            print(table, json.dumps(sc, sort_keys=True), n_seeds, se, json.dumps(brief),
                  f"xi {d['xi']:.2f} se {d['se_cl']:.2f} hw {d['hw']:.2f} pre_hw {d['pre_hw']:.2f} lf_hw {d['lf_hw']:.2f}", flush=True)
            with open(path, "w") as fh:
                json.dump(out, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
