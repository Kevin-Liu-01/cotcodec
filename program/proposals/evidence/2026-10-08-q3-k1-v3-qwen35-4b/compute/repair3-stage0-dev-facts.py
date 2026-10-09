"""K1 v3 repair under D52: model-free stage-0 facts on the DEVELOPMENT partition (no model is run).

What it computes, per controlled family (entity-controlled question x pair) of the unseen stratum
(14 pairs) and the seen stratum (6 pairs), at each of the four needle block alignments:
- needle tokens N, unmasked tokens |N^M| (rule E, the overlap mask), the literal blocks (rule E or the
  near rule F, matches to either question), |N^LF| at r = 1 and 2, |N^PRE| (tokens before the first
  E-or-F literal block; also E only), and the forward-distance profile of the unmasked tokens from the
  nearest preceding literal block (PRE, 1-2, 3-5, 6-11, 12+ blocks);
- the evaluable shares under the draft's per-family 32-token rule and the coverage of the repaired,
  pooled pre-literal statistic (every family with at least one complete pre-literal block, weighted by
  its pre-literal tokens);
- a model-free answer-sentence proxy: the English passage sentence with the largest word overlap with
  the question plus the correct option, carried to the needle language by sentence index when the
  needle passage splits into the same number of sentences; its share of each evidence set bounds the
  sensitivity kappa of LF and PRE when the indexer's excess sits on that sentence only;
- the link structure of the controlled set (questions and controlled questions per link).

Inputs: Belebele jsonl files (eng, jpn, kor, ben, tam, ell, heb, kat, tha, hin, khm), the
Qwen3.5-4B-Base tokenizer.json (sha256 fe000e3e..., as the lane-862 receipt) and the stop lists built
on the host from K1's haystack sources (host_stoplists.py). The split is K1's
split_passage_ids(seed=42) and the anchor rule the dense pre-check's english_anchors, both imported
from the repository. Output: counts, shares and per-family integers only (no text).
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from collections import Counter

from tokenizers import Tokenizer

from harness.dense_headroom_data import english_anchors
from harness.translation_supervised_indexer import split_passage_ids

BELEBELE, TOKP, STOPP, OUT = sys.argv[1:5]
TOK = Tokenizer.from_file(TOKP)
assert hashlib.sha256(open(TOKP, "rb").read()).hexdigest().startswith("fe000e3ed39ed12b")
STOPS = json.load(open(STOPP))
LANGS = {"en": "eng_Latn", "ja": "jpn_Jpan", "ko": "kor_Hang", "bn": "ben_Beng", "ta": "tam_Taml",
         "el": "ell_Grek", "he": "heb_Hebr", "ka": "kat_Geor", "th": "tha_Thai", "hi": "hin_Deva", "km": "khm_Khmr"}
UNSEEN = ["bn", "el", "he", "ja", "ka", "ko", "ta"]       # S2's pair order
SEEN = ["th", "hi", "km"]
NOSPACE = {"ja", "ko", "th", "km", "zh"}
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
BINS = ("PRE", "1-2", "3-5", "6-11", "12+")


def encode(text):
    e = TOK.encode(text, add_special_tokens=False)
    return list(e.ids), list(e.offsets)


_SYM = {}


def symbol_only(i):
    if i not in _SYM:
        t = TOK.decode([i])
        _SYM[i] = False if "�" in t else not any(ch.isalnum() for ch in t)
    return _SYM[i]


rows = {}
for l, f in LANGS.items():
    for line in open(f"{BELEBELE}/{f}.jsonl"):
        r = json.loads(line)
        rows.setdefault((r["link"], int(r["question_number"])), {})[l] = r
keys = sorted(k for k, v in rows.items() if set(v) == set(LANGS))
split = split_passage_ids(sorted({k[0] for k in keys}), seed=42)
dkeys = [k for k in keys if k[0] in split.development]
ctrl = [k for k in dkeys if not any(english_anchors(rows[k]["en"]["question"], rows[k]["en"]["flores_passage"]).values())]
per_link = Counter(k[0] for k in dkeys)
per_link_ctrl = Counter(k[0] for k in ctrl)
link_profile = Counter((per_link[l], per_link_ctrl.get(l, 0)) for l in per_link)

# ---- sentence proxy for the question-relevant region --------------------------------------------
SENT_END = {"ja": r"(?<=[。！？])", "bn": r"(?<=[।?!])\s+", "hi": r"(?<=[।?!])\s+", "km": r"(?<=[។?!])\s*",
            "th": None}
EN_STOP = set("the a an of to in and or is are was were be been for on at by with from as that this it its which who what when where how why did does do not no than then there their they he she his her has have had can could would should will may might about into over after before more most any all some such".split())


def sentences(text, lang):
    if lang == "th":
        return None
    pat = SENT_END.get(lang, r"(?<=[.!?;])\s+")
    parts = [s for s in re.split(pat, text.strip()) if s.strip()]
    return parts


def answer_sentence(k):
    r = rows[k]["en"]
    sents = sentences(r["flores_passage"], "en")
    ans = r[f"mc_answer{r['correct_answer_num']}"]
    qw = {w.lower() for w in WORD.findall(r["question"] + " " + ans) if w.lower() not in EN_STOP and len(w) > 2}
    scores = [len(qw & {w.lower() for w in WORD.findall(s)}) for s in sents]
    return int(max(range(len(sents)), key=lambda i: (scores[i], -i))), len(sents)


ANS = {k: answer_sentence(k) for k in ctrl}


def sentence_char_spans(text, lang, n_en):
    parts = sentences(text, lang)
    if parts is None or len(parts) != n_en:
        return None
    spans, pos = [], 0
    for p in parts:
        a = text.find(p, pos)
        spans.append((a, a + len(p)))
        pos = a + len(p)
    return spans


# ---- literal rules -------------------------------------------------------------------------------

def make_rules(ids_key, ng_key, n_ids, n_ng):
    stop = {l: set(STOPS[l][ids_key]["ids"][:n_ids]) for l in LANGS}
    ngstop = {l: set(STOPS[l][ng_key]["ngrams"][:n_ng]) for l in LANGS}
    return stop, ngstop


def content(ids, langs, stop):
    s = set().union(*(stop[x] for x in langs))
    return {i for i in ids if i not in s and not symbol_only(i)}


def ngrams(word, n, ngstop_l):
    return {word[i:i + n] for i in range(len(word) - n + 1)
            if any(ch.isalpha() for ch in word[i:i + n]) and word[i:i + n] not in ngstop_l}


ENC = {}


def enc(text):
    if text not in ENC:
        ENC[text] = encode(text)
    return ENC[text]


def family(k, needle_l, mn_l, cx_l, offset, stop, ngstop, use_f=True):
    ptext = rows[k][needle_l]["flores_passage"]
    pids, pspans = enc(ptext)
    q_mn, q_cx = rows[k][mn_l]["question"], rows[k][cx_l]["question"]
    qmn_ids = enc("\n\n" + q_mn + "\n")[0]
    qcx_ids = enc("\n\n" + q_cx + "\n")[0]
    O = (set(pids) & content(qmn_ids, (needle_l, mn_l), stop)) | (set(pids) & content(qcx_ids, (needle_l, cx_l), stop))
    N = len(pids)
    blk = [(i + offset) // 4 for i in range(N)]
    nb = blk[-1] + 1
    emask = [pids[i] in O for i in range(N)]
    fmask = [False] * N
    if use_f:
        pn = 2 if needle_l in NOSPACE else 4
        qg = set()
        for qt, ql in ((q_mn, mn_l), (q_cx, cx_l)):
            n = 2 if ql in NOSPACE else 4
            if n != pn:
                continue
            for m in WORD.finditer(qt):
                w = m.group(0)
                wid = enc(" " + w)[0]
                if any(i not in stop[ql] and not symbol_only(i) for i in wid):
                    qg |= ngrams(w.lower(), n, ngstop[ql])
        for m in WORD.finditer(ptext):
            if ngrams(m.group(0).lower(), pn, ngstop[needle_l]) & qg:
                a, b = m.start(), m.end()
                for i, (c0, c1) in enumerate(pspans):
                    if c0 < b and c1 > a and not emask[i]:
                        fmask[i] = True
    mblocks = {blk[i] for i in range(N) if emask[i]}
    lblocks = sorted({blk[i] for i in range(N) if emask[i] or fmask[i]})
    first = lblocks[0] if lblocks else nb
    unmasked = [i for i in range(N) if blk[i] not in mblocks]
    # forward distance (blocks) from the nearest preceding literal block, None = before the first
    prev = {}
    last = None
    lset = set(lblocks)
    for b in range(nb):
        prev[b] = None if last is None else b - last
        if b in lset:
            last = b
    dist = Counter()
    for i in unmasked:
        d = prev[blk[i]] if blk[i] not in lset else 0
        if blk[i] < first:
            dist["PRE"] += 1
        elif d == 0:
            dist["lit"] += 1          # an unmasked token in a near-literal block
        elif d <= 2:
            dist["1-2"] += 1
        elif d <= 5:
            dist["3-5"] += 1
        elif d <= 11:
            dist["6-11"] += 1
        else:
            dist["12+"] += 1

    def lf(r):
        return [i for i in range(N) if all(abs(blk[i] - b) > r for b in lblocks)]

    lf2, lf1 = lf(2), lf(1)
    pre = [i for i in range(N) if blk[i] < first]
    # complete pre-literal blocks (all four token slots inside the passage)
    pre_blocks = Counter(blk[i] for i in pre)
    pre_complete = sum(1 for b, c in pre_blocks.items() if c == 4)
    out = dict(N=N, nM=len(unmasked), nLF2=len(lf2), nLF1=len(lf1), nPRE=len(pre), nPRE_blocks=pre_complete,
               nPRE_E=sum(1 for i in range(N) if blk[i] < (min(mblocks) if mblocks else nb)),
               n_lit=len(lblocks), n_E=len(mblocks), nb=nb, dist=dict(dist))
    # answer-sentence shares
    a_idx, n_en = ANS[k]
    spans = sentence_char_spans(ptext, needle_l, n_en)
    if spans is not None:
        c0, c1 = spans[a_idx]
        inA = [pspans[i][0] < c1 and pspans[i][1] > c0 for i in range(N)]
        out["A"] = dict(M=sum(inA[i] for i in unmasked), LF2=sum(inA[i] for i in lf2), PRE=sum(inA[i] for i in pre),
                        N=sum(inA))
    return out


def families(offset, stop, ngstop, use_f=True):
    fams = []
    for stratum, langs in (("unseen", UNSEEN), ("seen", SEEN)):
        for X in langs:
            for k in ctrl:
                fams.append((stratum, "en>" + X, k, family(k, "en", "en", X, offset, stop, ngstop, use_f)))
                fams.append((stratum, X + ">en", k, family(k, X, X, "en", offset, stop, ngstop, use_f)))
    return fams


def summarise(fams, stratum):
    F = [f for s, _, _, f in fams if s == stratum]
    n = len(F)
    pooled_pre = [f for f in F if f["nPRE_blocks"] >= 1]
    tot_m = sum(f["nM"] for f in F)
    d = Counter()
    for f in F:
        d.update(f["dist"])
    res = dict(
        families=n,
        mask_excluded_share=sum(f["nM"] < 32 for f in F) / n,
        lf_r2_evaluable_share=sum(f["nLF2"] >= 32 for f in F) / n,
        lf_r1_evaluable_share=sum(f["nLF1"] >= 32 for f in F) / n,
        pre_evaluable_share_32=sum(f["nPRE"] >= 32 for f in F) / n,
        pre_E_only_evaluable_share_32=sum(f["nPRE_E"] >= 32 for f in F) / n,
        pre_any_complete_block_share=len(pooled_pre) / n,
        pre_tokens_share_of_unmasked=sum(f["nPRE"] for f in F) / tot_m,
        lf2_tokens_share_of_unmasked=sum(f["nLF2"] for f in F) / tot_m,
        median_pre_tokens=statistics.median(f["nPRE"] for f in F),
        mean_pre_tokens=statistics.fmean(f["nPRE"] for f in F),
        median_unmasked_tokens=statistics.median(f["nM"] for f in F),
        median_lf2_tokens=statistics.median(f["nLF2"] for f in F),
        mean_literal_blocks=statistics.fmean(f["n_lit"] for f in F),
        unmasked_token_distance_profile={b: d.get(b, 0) / tot_m for b in BINS + ("lit",)},
    )
    G = [f for f in F if "A" in f and f["nM"] > 0]
    if G:
        aM = statistics.fmean(f["A"]["M"] / f["nM"] for f in G)
        aLF = statistics.fmean(f["A"]["LF2"] / f["nLF2"] for f in G if f["nLF2"] >= 32)
        GP = [f for f in G if f["nPRE_blocks"] >= 1]
        pre_w = sum(f["A"]["PRE"] for f in GP) / max(1, sum(f["nPRE"] for f in GP))
        res["answer_sentence"] = dict(
            families_with_alignment=len(G), share_aligned=len(G) / n,
            mean_share_of_unmasked_in_answer_sentence=aM,
            mean_share_of_lf2_in_answer_sentence=aLF,
            pooled_share_of_pre_in_answer_sentence=pre_w,
            kappa_LF2_concentrated=aLF / aM,
            kappa_PRE_pooled_concentrated=pre_w / aM)
    per_pair = {}
    for s, p, _, f in fams:
        if s != stratum:
            continue
        d_ = per_pair.setdefault(p, Counter())
        d_["n"] += 1
        d_["pre32"] += f["nPRE"] >= 32
        d_["pre_any"] += f["nPRE_blocks"] >= 1
        d_["lf2"] += f["nLF2"] >= 32
        d_["nM"] += f["nM"]; d_["nPRE"] += f["nPRE"]; d_["nLF2"] += f["nLF2"]
    res["per_pair"] = {p: dict(pre32=round(v["pre32"] / v["n"], 3), pre_any=round(v["pre_any"] / v["n"], 3),
                               lf2=round(v["lf2"] / v["n"], 3), mean_nM=round(v["nM"] / v["n"], 1),
                               mean_nPRE=round(v["nPRE"] / v["n"], 1), mean_nLF2=round(v["nLF2"] / v["n"], 1))
                       for p, v in sorted(per_pair.items())}
    return res


out = dict(
    partition="development", links=len(split.development), questions=len(dkeys), controlled_questions=len(ctrl),
    controlled_links=len({k[0] for k in ctrl}),
    link_profile_n_questions_n_controlled={f"{a},{b}": c for (a, b), c in sorted(link_profile.items())},
    stoplists_sha256=hashlib.sha256(open(STOPP, "rb").read()).hexdigest(),
    variants={})
VARIANTS = {
    "registered_proxy: ids100 and ngrams200 of 1,000 haystack documents, E+F": ("1000", "1000", 100, 200, True),
    "refuter_proxy: ids100 and ngrams200 of 400 documents, E+F": ("400", "400", 100, 200, True),
    "ids100 of 1,000 documents, E only": ("1000", "1000", 100, 200, False),
    "ids200 of 1,000 documents, E+F": ("1000", "1000", 200, 200, True),
    "ids400 of 1,000 documents, E+F": ("1000", "1000", 400, 200, True),
}
per_family_dump = None
for name, (ik, gk, ni, ng, use_f) in VARIANTS.items():
    stop, ngstop = make_rules(ik, gk, ni, ng)
    by_off = {}
    for offset in (0, 1, 2, 3):
        fams = families(offset, stop, ngstop, use_f)
        by_off[offset] = {s: summarise(fams, s) for s in ("unseen", "seen")}
        if per_family_dump is None and offset == 0:
            per_family_dump = [dict(stratum=s, pair=p, link=k[0], q=k[1], nM=f["nM"], nLF2=f["nLF2"], nPRE=f["nPRE"],
                                    nPRE_blocks=f["nPRE_blocks"], A=f.get("A"))
                               for s, p, k, f in fams]
        print(name, offset, json.dumps({s: {kk: round(v, 3) for kk, v in by_off[offset][s].items() if isinstance(v, float)} for s in ("unseen",)}), file=sys.stderr, flush=True)
    out["variants"][name] = by_off
# link ids are public Belebele URLs; keep only a digest-based index in the dump
lmap = {l: i for i, l in enumerate(sorted({d["link"] for d in per_family_dump}))}
for d in per_family_dump:
    d["link"] = lmap[d["link"]]
out["per_family_registered_proxy_offset0"] = per_family_dump
json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
