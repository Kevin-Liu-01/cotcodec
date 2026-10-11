#!/usr/bin/env python3
"""P1: the measured NTREX-128 pool and the surface-cue controls of registration v2 (D68 repair).

Reads NTREX-128 (commit 468c6b69: newstest2019-src.eng, -ref.deu, -ref.zho-CN,
-ref.tha and DOCUMENT_IDS.tsv) from a local directory given on the command line.
Writes counts and rates only; no sentence text leaves the machine.

What it measures, for the v1 design (wave 1) and the v2 design side by side:

1. Pool. Eligible key sentences: digit-free in all four languages (Unicode Nd
   after NFKC) and 6 to 40 English words (proxy for the registered "8 to 60
   tokens in every language" until the 32K tokenizer exists). Test half: the
   documents with int(sha256("42:" + doc_id), 16) % 2 == 0 (the registered
   split, fixed here; the distribution over 200 other salts is reported for
   context only).

2. Surface filter.
   v1 (as registered in wave 1, approximated as reviewer 1 did): no shared
   NFKC-casefolded whitespace token and no shared Latin word of >= 4 letters.
   v2: no shared NFKC-casefolded whitespace token (raw or punctuation-stripped)
   and no shared letter 4-gram inside any word (Unicode letters, casefolded;
   the legacy contract's character-4-gram clause), against all eight keys.

3. Distractor keys.
   v1: 7 drawn uniformly from the eligible test half (resampled until the
   filter holds, at most 50 tries).
   v2a (first repair attempt, kept as a negative result): 7 drawn uniformly
   from the target key's surface stratum (length quintile x has quote x has ?
   or ! x comma count 0/1/2+), coarsened in a fixed order when fewer than 7
   pass the filter. It leaves the surface oracles far above chance (within-
   quintile length differences and the remaining punctuation still identify
   the target), so it is not registered.
   v2 (registered): a sliding surface block. The fact-language keys of the half
   are put in one total order by (the exact punctuation count vector over ", ?,
   !, :, ;, ( and ",", then length, then row id), with length = non-whitespace
   characters (registration v2: 32K-tokenizer tokens). The key set of a prompt
   is the block of 8 consecutive keys that contains the target at an offset
   drawn uniformly from 0..7 (clipped at the ends of the order). A distractor
   that fails the filter is replaced by the nearest unused key beyond either end
   of the block (alternating, at most 20 steps); else the target is not used in
   that cell. The target's rank inside its block is uniform, so no query-free
   key statistic singles it out, and the eight keys share punctuation class and
   nearly the same length, so a query's surface form carries little about
   which key is its translation.

4. Decoy query (v2a and v2). A surface twin of the real query: a sentence in
   the query language from the whole eligible NTREX pool (both halves), not
   from the rows of the eight keys (so not a translation of any key), passing
   the filter against all eight keys, with the same punctuation count vector,
   the same named-entity-shape count (capitalised words after the first, or
   runs of Latin letters inside Chinese or Thai) and a length within 5% of the
   real query's; the nearest in length is taken, ties at random. A prompt with
   no twin is not used in that cell. A model that matches on these surface
   features alone treats the decoy like the real query.

5. Surface oracles on the realized prompts (top-1 among 8; chance 1/8):
   len      key minimising |log((len(query) / r) / len(key))|, r the median
            query/key length ratio fitted on the development half;
   len+p    len + 0.5 x L1 distance of punctuation counts (", ?, !, :, ;, (, ,);
   central  query-free: the key whose length is closest to the median of the 8;
   clogit   a conditional-logit oracle over 10 surface features (log length
            ratio and its square, the 7 punctuation count differences and the
            named-entity-shape difference),
            fitted on development-half prompts built the same way and
            evaluated on test-half prompts (a stronger, learned surface
            oracle).
   The same oracles are run with the decoy in place of the real query
   (hit = picks the target key).

Seed 42 for every draw. Usage:
  instrument-pool-v2.py <ntrex_dir> <output.json>
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter

import numpy as np

FILES = {"eng": "ntrex_newstest2019-src.eng.txt", "deu": "ntrex_newstest2019-ref.deu.txt",
         "zho": "ntrex_newstest2019-ref.zho-CN.txt", "tha": "ntrex_newstest2019-ref.tha.txt"}
CROSS_SCRIPT = [("eng", "zho"), ("zho", "eng"), ("eng", "tha"), ("tha", "eng")]
SAME_SCRIPT = [("eng", "deu"), ("deu", "eng")]
PUNCT_CLASSES = ['"', "?", "!", ":", ";", "(", ","]
QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "「": '"', "」": '"',
                        "『": '"', "』": '"', "、": ","})
CAP = 500


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def has_digit(s):
    return any(unicodedata.category(c) == "Nd" for c in s)


def ws_tokens(s):
    return set(s.casefold().split())


def ws_tokens_stripped(s):
    return {re.sub(r"^\W+|\W+$", "", t) for t in ws_tokens(s)} - {""}


def latin_words4(s):
    return {w for w in re.findall(r"[^\W\d_]+", s.casefold()) if len(w) >= 4 and re.match(r"[a-zäöüß]", w)}


def letter_4grams(s):
    out = set()
    for w in re.findall(r"[^\W\d_]+", s.casefold()):
        for k in range(len(w) - 3):
            out.add(w[k:k + 4])
    return out


def length(s):
    return len(re.sub(r"\s+", "", s))


def ne_count(s):
    """Capitalised words after the first (Latin script) plus runs of ASCII letters inside non-Latin text."""
    words = s.split()
    cap = sum(1 for w in words[1:] if w[:1].isupper())
    latin_runs = len(re.findall(r"[A-Za-z]+", s)) if not re.match(r"^[\x00-\x7f\u00c0-\u024f\s\W]*$", s) else 0
    return float(cap if latin_runs == 0 else latin_runs)


def psig(s):
    s2 = s.translate(QUOTES)
    return np.array([s2.count(c) for c in PUNCT_CLASSES], float)


class Feats:
    def __init__(self, text):
        self.text = text
        self.ws = ws_tokens(text)
        self.wss = ws_tokens_stripped(text)
        self.w4 = latin_words4(text)
        self.g4 = letter_4grams(text)
        self.len = length(text)
        self.p = psig(text)
        self.ne = ne_count(text)
        self.pkey = tuple(int(v) for v in self.p)
        p = self.p
        self.stratum_full = (bool(p[0] > 0), bool(p[1] + p[2] > 0), int(min(p[6], 2)))
        self.cls = (bool(p[0] > 0), bool(p[1] + p[2] > 0), bool(p[3] + p[4] > 0), bool(p[5] > 0), int(min(p[6], 3)))


def ok_v1(q: Feats, k: Feats):
    return not (q.ws & k.ws) and not (q.w4 & k.w4)


def ok_v2(q: Feats, k: Feats):
    return not (q.ws & k.ws) and not (q.wss & k.wss) and not (q.g4 & k.g4)


DECOY_LEN_TOL = 0.05


def pick_decoy(rng, F, decoy_pool, fl, ql, q, keys, ok):
    """Surface-twin decoy in the query language, from the whole eligible NTREX pool (both halves) minus the rows
    of the eight keys: same punctuation count vector, same named-entity-shape count, length within 5% of the real
    query's, filter-clean against all eight keys; the nearest in length is taken (ties at random). None if no twin."""
    best, best_d = [], None
    for j in decoy_pool:
        if j in keys:
            continue
        dq = F[ql][j]
        if dq.pkey != q.pkey or dq.ne != q.ne:
            continue
        dist = abs(math.log(max(dq.len, 1) / max(q.len, 1)))
        if dist > DECOY_LEN_TOL:
            continue
        if best_d is not None and dist > best_d + 1e-12:
            continue
        if not all(ok(dq, F[fl][k]) for k in keys):
            continue
        if best_d is None or dist < best_d - 1e-12:
            best, best_d = [j], dist
        else:
            best.append(j)
    if not best:
        return None, None
    return rng.choice(best), best_d


def build_prompts(rng, F, half_ids, fl, ql, design, ratio, decoy_pool=None):
    """Return a list of prompt dicts for cell fl->ql over the given half."""
    pool = list(half_ids)
    lens = np.array([F[fl][i].len for i in pool])
    qs = np.quantile(lens, [0.2, 0.4, 0.6, 0.8])
    qbin = {i: int(np.searchsorted(qs, F[fl][i].len, side="right")) for i in pool}
    order = sorted(pool, key=lambda j: (F[fl][j].pkey, F[fl][j].len, j))
    pos = {j: k for k, j in enumerate(order)}
    ok = ok_v1 if design == "v1" else ok_v2
    prompts = []
    for i in pool:
        q = F[ql][i]
        if not ok(q, F[fl][i]):
            continue
        cand_all = [j for j in pool if j != i]
        rec = {"target": i}
        if design == "v1":
            found = None
            for _ in range(50):
                ds = rng.sample(cand_all, 7)
                if all(ok(q, F[fl][j]) for j in ds):
                    found = ds
                    break
            if found is None:
                continue
            rec["distractors"] = found
            rec["level"] = "uniform"
        elif design == "v2a":
            passing = [j for j in cand_all if ok(q, F[fl][j])]
            st = F[fl][i].stratum_full
            levels = [("full", lambda j: qbin[j] == qbin[i] and F[fl][j].stratum_full == st),
                      ("no_comma", lambda j: qbin[j] == qbin[i] and F[fl][j].stratum_full[:2] == st[:2]),
                      ("quote_only", lambda j: qbin[j] == qbin[i] and F[fl][j].stratum_full[0] == st[0]),
                      ("length_only", lambda j: qbin[j] == qbin[i])]
            found = None
            for name, pred in levels:
                members = [j for j in passing if pred(j)]
                if len(members) >= 7:
                    found = (name, rng.sample(members, 7))
                    break
            if found is None:
                continue
            rec["level"], rec["distractors"] = found
        else:
            n = len(order)
            p0 = pos[i]
            off = rng.randrange(8)
            start = min(max(p0 - off, 0), n - 8)
            block = order[start:start + 8]
            used = set(block)
            ds = []
            lo, hi = start - 1, start + 8
            failed = False
            for j in block:
                if j == i:
                    continue
                if ok(q, F[fl][j]):
                    ds.append(j)
                    continue
                rep = None
                for step in range(20):
                    side_hi = step % 2 == 0
                    k = hi if side_hi else lo
                    if side_hi:
                        hi += 1
                    else:
                        lo -= 1
                    if 0 <= k < n and order[k] not in used and ok(q, F[fl][order[k]]):
                        rep = order[k]
                        break
                if rep is None:
                    failed = True
                    break
                used.add(rep)
                ds.append(rep)
            if failed:
                continue
            rec["distractors"] = ds
            rec["level"] = "block_exact" if all(j in block for j in ds) else "block_with_replacement"
        if design != "v1":
            keys = [i] + rec["distractors"]
            dec, dd = pick_decoy(rng, F, decoy_pool if decoy_pool is not None else pool, fl, ql, q, keys, ok)
            if dec is None:
                continue
            rec["decoy"], rec["decoy_distance"] = dec, dd
            lk = [F[fl][k].len for k in keys]
            rec["key_length_spread"] = max(lk) / max(min(lk), 1)
        prompts.append(rec)
    rng.shuffle(prompts)
    return prompts[:CAP]


def features(F, fl, ql, qid, keys, ratio):
    q = F[ql][qid]
    rows = []
    for k in keys:
        kk = F[fl][k]
        lr = math.log(max(q.len / ratio, 1e-9) / max(kk.len, 1))
        rows.append([abs(lr), lr * lr] + list(np.abs(q.p - kk.p)) + [abs(q.ne - kk.ne)])
    return np.array(rows)


def oracle_hits(rng, F, fl, ql, prompts, ratio, w=None, use_decoy=False):
    hits = Counter()
    n = 0
    for pr in prompts:
        keys = [pr["target"]] + pr["distractors"]
        qid = pr["decoy"] if use_decoy else pr["target"]
        X = features(F, fl, ql, qid, keys, ratio)
        dl = X[:, 0]
        dp = X[:, 2:9].sum(1)
        for name, score in (("len", dl), ("len+p", dl + 0.5 * dp)):
            best = score.min()
            win = [k for k in range(8) if score[k] <= best + 1e-12]
            hits[name] += rng.choice(win) == 0
        ln = np.array([F[fl][k].len for k in keys], float)
        cen = np.abs(ln - np.median(ln))
        win = [k for k in range(8) if cen[k] <= cen.min() + 1e-12]
        hits["central"] += rng.choice(win) == 0
        if w is not None:
            s = X @ w
            win = [k for k in range(8) if s[k] >= s.max() - 1e-12]
            hits["clogit"] += rng.choice(win) == 0
        n += 1
    return {k: round(v / n, 4) for k, v in hits.items()}, n


def fit_clogit(F, fl, ql, prompts, ratio, iters=400, lr=0.5, l2=1e-3):
    Xs = [features(F, fl, ql, pr["target"], [pr["target"]] + pr["distractors"], ratio) for pr in prompts]
    Xs = np.stack(Xs)                   # (n, 8, f)
    mu = Xs.reshape(-1, Xs.shape[-1]).mean(0)
    sd = Xs.reshape(-1, Xs.shape[-1]).std(0) + 1e-9
    Z = (Xs - mu) / sd
    w = np.zeros(Z.shape[-1])
    for _ in range(iters):
        s = Z @ w
        s = s - s.max(1, keepdims=True)
        p = np.exp(s)
        p /= p.sum(1, keepdims=True)
        grad = (Z[:, 0, :] - (p[:, :, None] * Z).sum(1)).mean(0) - l2 * w
        w += lr * grad
    return w / sd, float((np.argmax(Z @ w, 1) == 0).mean())


def main() -> int:
    d, out_path = sys.argv[1], sys.argv[2]
    T = {k: [nfkc(l.rstrip("\n")) for l in open(f"{d}/{v}", encoding="utf-8")] for k, v in FILES.items()}
    doc = [l.strip() for l in open(f"{d}/ntrex_DOCUMENT_IDS.tsv", encoding="utf-8")]
    n = len(doc)
    digests = {}
    for k, v in list(FILES.items()) + [("doc_ids", "ntrex_DOCUMENT_IDS.tsv")]:
        digests[v] = hashlib.sha256(open(f"{d}/{v}", "rb").read()).hexdigest()
    elig = [i for i in range(n) if not any(has_digit(T[k][i]) for k in T) and 6 <= len(T["eng"][i].split()) <= 40]
    docs = sorted(set(doc))
    test_docs = {x for x in docs if int(hashlib.sha256(f"42:{x}".encode()).hexdigest(), 16) % 2 == 0}
    test = [i for i in elig if doc[i] in test_docs]
    dev = [i for i in elig if doc[i] not in test_docs]
    salts = sorted(sum(1 for i in elig if int(hashlib.sha256(f"{s}:{doc[i]}".encode()).hexdigest(), 16) % 2 == 0)
                   for s in range(200))
    F = {k: {i: Feats(T[k][i]) for i in elig} for k in T}
    res = {"script": "instrument-pool-v2.py", "ntrex_files_sha256": digests, "sentences": n, "documents": len(docs),
           "eligible_all": len(elig), "test_half_documents": len(test_docs), "test_half_eligible": len(test),
           "dev_half_eligible": len(dev),
           "test_half_eligible_over_200_salts_context_only": {"min": salts[0], "median": salts[100], "max": salts[-1]},
           "proxies": {"length": "non-whitespace characters (registration v2: 32K-tokenizer tokens)",
                       "eligibility_length": "6-40 English words (registration: 8-60 tokens in every language)"},
           "cells": {}}
    for fl, ql in CROSS_SCRIPT + SAME_SCRIPT:
        ratio = float(np.median([F[ql][i].len / max(F[fl][i].len, 1) for i in dev]))
        cell = {"length_ratio_query_over_key_dev": round(ratio, 3)}
        for design in ("v1", "v2a", "v2"):
            rng = random.Random(f"42:{design}:{fl}->{ql}")
            pr_test = build_prompts(rng, F, test, fl, ql, design, ratio, decoy_pool=elig)
            pr_dev = build_prompts(rng, F, dev, fl, ql, design, ratio, decoy_pool=elig)
            w, dev_fit = fit_clogit(F, fl, ql, pr_dev, ratio) if len(pr_dev) >= 50 else (None, None)
            orc, nn = oracle_hits(rng, F, fl, ql, pr_test, ratio, w)
            entry = {"prompts_test_half": nn, "prompts_dev_half": len(pr_dev), "oracle_top1_real_query": orc,
                     "clogit_dev_fit_top1": None if dev_fit is None else round(dev_fit, 4)}
            if design in ("v2a", "v2"):
                entry["stratum_levels"] = dict(Counter(p["level"] for p in pr_test))
                entry["key_length_spread_median"] = round(float(np.median([p["key_length_spread"] for p in pr_test])), 4)
                orc_d, _ = oracle_hits(rng, F, fl, ql, pr_test, ratio, w, use_decoy=True)
                entry["oracle_top1_decoy_query"] = orc_d
                entry["decoy_distance_median"] = round(float(np.median([p["decoy_distance"] for p in pr_test])), 4)
                entry["eligible_queried_sentences_uncapped"] = sum(
                    1 for i in test if ok_v2(F[ql][i], F[fl][i]))
            cell[design] = entry
        res["cells"][f"{fl}->{ql}"] = cell
        print(fl, ql, json.dumps(cell), flush=True)
    xs = [f"{a}->{b}" for a, b in CROSS_SCRIPT]
    for design in ("v1", "v2a", "v2"):
        for key in ("len", "len+p", "central", "clogit"):
            vals = [res["cells"][c][design]["oracle_top1_real_query"].get(key) for c in xs]
            if all(v is not None for v in vals):
                res.setdefault("cross_script_pooled_equal_weight", {}).setdefault(design, {})[f"real_{key}"] = round(float(np.mean(vals)), 4)
        if design in ("v2a", "v2"):
            for key in ("len", "len+p", "central", "clogit"):
                vals = [res["cells"][c][design]["oracle_top1_decoy_query"].get(key) for c in xs]
                if all(v is not None for v in vals):
                    res["cross_script_pooled_equal_weight"][design][f"decoy_{key}"] = round(float(np.mean(vals)), 4)
    res["chance"] = 0.125
    res["note"] = ("Character-level proxies, not the 32K tokenizer; a model need not use these cues, but the v2 "
                   "builder must keep them near chance on the sealed manifest (registration v2, builder gate B-SURF).")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print(json.dumps(res["cross_script_pooled_equal_weight"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
