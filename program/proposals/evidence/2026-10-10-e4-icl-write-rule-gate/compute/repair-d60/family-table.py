#!/usr/bin/env python3
"""E4 gate repair (D60), CPU check F1: the family table under the teacher's real tokenizer.

Builds every family's usable item set from hand-written word lists and seeded
generators, and checks each answer against the teacher's own tokenizer
(fla-hub/transformer-1.3B-100B, revision d6f66f4181fa669e5863327815b44533e3a395e7,
tokenizer.json sha256 fc4f0bd70b3709312d9d1d9e5ba674794b6bc5abc17429897a540f93882f25fc).

Answer rule (registration v2, "Families"): the answer must be exactly one token
appended to the prompt's own tokens, checked on the full string, because the
tokenizer has no pre-tokenizer (BPE runs over the whole normalised string):
  enc(prompt + answer_text) == enc(prompt) + [one id].
Word answers follow "output:" as " word" (one "▁word" token). The tokenizer
has no "▁<digit>" token and no merge of "▁" with a digit, so digit
answers are tokenized deliberately: the digit-family prompt ends with "output: "
(its last token is the bare "▁", id 28705, exactly as before any number in
pretraining text) and the answer is the bare digit token.

Each family must supply, per Step-2 episode, 8 demonstrations + N_FIT fitting
+ 8 scoring queries with mutually distinct inputs (lookup families: 8 bound
names under three templates). The registered floor is 60 usable inputs
(N_FIT = 24 needs 40 per episode; 60 leaves room for varied episodes).
The script also records prompt lengths in tokens (zero-shot probe and 8-shot
prompt) for the cost model.

Usage: uv run --no-project --offline --with tokenizers==0.22.2 python family-table.py <tokenizer.json> <out.json>
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys

import numpy as np
from tokenizers import Tokenizer

N_DEMO, N_FIT, N_SCORE = 8, 24, 8
FLOOR = 60
LABELS_NEEDED = {"A1": 8, "A2": 8, "A3": 2, "A4": 4, "A5": 2}  # distinct labels an episode draws

# ---- hand-written word lists (MIT, this repository) ----
NOUNS = """cat dog bird fish horse cow pig sheep goat duck frog bear lion tiger wolf fox deer mouse rat snake
book pen cup bowl plate spoon fork knife chair table door window wall floor roof house car bus train boat
ship plane bike road street park tree flower leaf river lake hill mountain island beach forest field farm
garden school church bank shop market hotel office room bed lamp clock phone desk box bag hat shoe shirt
coat dress ring key bell ball game song story letter word name friend girl boy king queen doctor nurse
teacher student farmer baker singer player writer painter driver pilot cook judge""".split()
ADJ_POS = """good great happy nice kind warm bright clean safe calm brave smart rich fresh sweet strong healthy
lucky gentle honest proud quiet friendly helpful pleasant lovely beautiful wonderful excellent perfect
cheerful polite generous joyful peaceful charming elegant graceful glad fine fair free easy wise noble""".split()
ADJ_NEG = """bad sad angry cold dark dirty dangerous cruel weak poor sick rude ugly lazy stupid evil awful
terrible horrible nasty bitter boring broken guilty harsh hostile lonely mean messy painful selfish
sour stale tired toxic unfair unhappy upset wicked wrong worse dull grim gross false hard""".split()
ANIMALS = """cat dog bird fish horse cow pig sheep goat duck frog bear lion tiger wolf fox deer mouse rat snake
rabbit monkey eagle owl shark whale dolphin camel zebra horse donkey turtle spider bee ant crab chicken
goose swan parrot penguin""".split()
TOOLS = """hammer saw drill knife axe shovel rake wrench screwdriver needle scissors brush broom ladder rope
chain nail screw bolt pump hose bucket pan pot kettle spoon fork lamp torch pencil ruler tape glue
clamp chisel file sickle anvil lever wheel""".split()
COLOURS = """red blue green yellow black white brown pink purple orange grey gold silver violet""".split()  # one spelling of grey
NUMWORDS = """one two three four five six seven eight nine ten eleven twelve twenty thirty hundred""".split()
LABEL_WORDS = """foo bar apple river stone cloud table piano rocket candle forest silver tiger window
garden pepper marble anchor""".split()
SYMBOLS = list("#@%&*+=?!$")
LETTERS_UP = list("ABCD")


def syllable_names(rng: np.random.Generator, n: int) -> list[str]:
    cons, vow = list("bdfgklmnprstvz"), list("aeiou")
    out = set()
    while len(out) < n:
        k = int(rng.integers(2, 4))
        out.add("".join(cons[int(rng.integers(len(cons)))] + vow[int(rng.integers(len(vow)))] for _ in range(k)))
    return sorted(out)


class Tok:
    def __init__(self, path: str):
        self.t = Tokenizer.from_file(path)

    def enc(self, s: str) -> list[int]:
        return self.t.encode(s, add_special_tokens=False).ids

    def answer_id(self, prompt: str, answer: str) -> int | None:
        a, b = self.enc(prompt), self.enc(prompt + answer)
        if len(b) == len(a) + 1 and b[: len(a)] == a:
            return b[-1]
        return None


def demo_block(pairs, digit: bool) -> str:
    sep = " " if not digit else " "
    return "".join(f"input: {x}\noutput:{sep}{y}\n" for x, y in pairs)


# Step-2 probe templates of the lookup families: three for fitting (24 probes), one for scoring (8 probes)
LOOKUP_TEMPLATES = {
    "A1": ["input: {x}\noutput: ", "the number of {x} is ", "{x} stands for the number ", "{x} has the number "],
    "A2": ["input: {x}\noutput:", "the colour of {x} is", "{x} stands for the colour", "{x} has the colour"],
}


def check_family(tok: Tok, items: list[tuple[str, str]], digit: bool, context_pairs, templates=None) -> tuple[list, list]:
    """Keep items whose answer is one appended token in the zero-shot and in an 8-shot context
    (for lookup families: under every Step-2 probe template)."""
    ok, bad = [], []
    ctx = demo_block(context_pairs, digit)
    tpls = templates or (["input: {x}\noutput: "] if digit else ["input: {x}\noutput:"])
    for x, y in items:
        good = True
        for tpl in tpls:
            p0 = tpl.format(x=x)
            a0 = y if p0.endswith(" ") else " " + y
            i0 = tok.answer_id(p0, a0)
            i8 = tok.answer_id(ctx + p0, a0)
            good = good and (i0 is not None and i0 == i8)
        (ok if good else bad).append((x, y))
    return ok, bad


def main() -> int:
    tok = Tok(sys.argv[1])
    rng = np.random.default_rng(42)
    fams: dict[str, dict] = {}

    def add(fid, cls, mapping, varies, items, digit, inputs_of=None, note=""):
        fams[fid] = {"class": cls, "mapping": mapping, "varies_by_episode": varies, "digit_answers": digit,
                     "raw_items": items, "note": note, "inputs_of": inputs_of}

    nouns = sorted(set(NOUNS))
    add("F1", "FF", "lowercase word to capitalised word", "no", [(w, w.capitalize()) for w in nouns], False)
    add("F2", "FF", "word to its last letter", "no", [(w, w[-1]) for w in nouns], False)
    two_digit = [str(n) for n in range(10, 100)]
    add("F3", "FF", "two-digit number to its first digit", "no", [(n, n[0]) for n in two_digit], True)
    add("F4", "FF", "word to its first letter", "no", [(w, w[0]) for w in nouns], False)
    plural = {w: (w + "es" if w.endswith(("s", "x", "ch", "sh")) else w + "s") for w in nouns
              if not w.endswith(("y", "f", "fe")) and w not in ("sheep", "deer", "fish", "mouse", "goose")}
    add("F5", "FF", "regular singular noun to plural", "no", sorted(plural.items()), False)
    # latent-parameter families: items are listed per latent value; the usable set is the inputs whose
    # answer passes the tokenizer check for every latent value (so the latent never changes the item set)
    distinct2 = [n for n in two_digit if n[0] != n[1]]
    add("L1", "LP", "two-digit number to its digit at position p", "p in {1,2}",
        {p: [(n, n[p - 1]) for n in distinct2] for p in (1, 2)}, True)
    cats = [("animal", sorted(set(ANIMALS))), ("colour", COLOURS), ("tool", sorted(set(TOOLS)))]
    trip = []
    for _ in range(400):
        ws = [c[1][int(rng.integers(len(c[1])))] for c in cats]
        order = rng.permutation(3)
        trip.append(([ws[i] for i in order], {cats[i][0]: ws[i] for i in range(3)}))
    add("L2", "LP", "three words (one animal, one colour, one tool, shuffled) to the word of category c",
        "c in {animal, colour, tool}",
        {c: [(" ".join(t), d[c]) for t, d in trip] for c, _ in cats}, False)
    lists3 = []
    for _ in range(400):
        ws = list(rng.choice(nouns, size=3, replace=False))
        lists3.append(ws)
    add("L3", "LP", "list of three words to the word at position p", "p in {1,2,3}",
        {p: [(" ".join(ws), ws[p - 1]) for ws in lists3] for p in (1, 2, 3)}, False)
    long_nouns = [w for w in nouns if len(w) >= 3]
    add("L4", "LP", "word to its i-th letter", "i in {1,2,3}",
        {i: [(w, w[i - 1]) for w in long_nouns] for i in (1, 2, 3)}, False)
    dl = ["".join(map(str, rng.permutation(10)[:3])) for _ in range(400)]
    add("L5", "LP", "three distinct digits (space-separated) to the digit at position p", "p in {1,2,3}",
        {p: [(" ".join(d), d[p - 1]) for d in dl] for p in (1, 2, 3)}, True)
    names = syllable_names(rng, 400)
    add("A1", "LA", "nonce name to a single digit, fresh binding per episode (8 names, distinct digits); "
        "probes are the 8 bound names under three templates", "binding",
        {d: [(nm, str(d)) for nm in names] for d in range(10)}, True)
    add("A2", "LA", "nonce word to colour word, fresh binding per episode; probes as A1", "binding",
        {c: [(nm, c) for nm in names] for c in COLOURS}, False)
    at = sorted(set(ANIMALS)) + sorted(set(TOOLS))
    add("A3", "LA", "animal or tool word to one of two symbols; symbol pair and assignment drawn per episode",
        "labels", {s: [(w, s) for w in at] for s in SYMBOLS}, False)
    a4 = sorted(set(ANIMALS)) + sorted(set(TOOLS)) + COLOURS + NUMWORDS
    add("A4", "LA", "animal, tool, colour or number word to one of the letters A-D, category-to-letter "
        "permuted per episode", "labels", {L: [(w, L) for w in a4] for L in LETTERS_UP}, False)
    sent = sorted(set(ADJ_POS)) + sorted(set(ADJ_NEG))
    add("A5", "LA", "positive or negative adjective to one of two unrelated label words drawn per episode "
        "(semantically-unrelated labels)", "labels", {L: [(w, L) for w in sent] for L in LABEL_WORDS}, False)

    out = {"tokenizer_sha256": hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(),
           "rule": "enc(prompt + answer) == enc(prompt) + [one id], in a zero-shot prompt and after an 8-shot block",
           "n_demo": N_DEMO, "n_fit": N_FIT, "n_score": N_SCORE, "floor_usable_inputs": FLOOR, "families": {}}
    for fid, f in fams.items():
        digit = f["digit_answers"]
        raw = f["raw_items"]
        if isinstance(raw, dict):  # per latent value / label: an input is usable only if every variant passes
            variants = {}
            for key, items in raw.items():
                ctx = items[:8]
                ok, bad = check_family(tok, items, digit, ctx, LOOKUP_TEMPLATES.get(fid))
                variants[str(key)] = {"ok": {x for x, _ in ok}, "n_bad": len(bad),
                                      "bad_examples": [y for _, y in bad[:5]]}
            labels_ok = [k for k, v in variants.items() if len(v["ok"]) >= FLOOR]
            if f["class"] == "LA":  # a label whose answer is not one token is removed from the label set
                keep = labels_ok if len(labels_ok) >= LABELS_NEEDED[fid] else []
            else:  # every latent value must survive, or the family changes
                keep = list(variants) if len(labels_ok) == len(variants) else []
            inputs = sorted(set.intersection(*[variants[k]["ok"] for k in keep])) if keep else []
            n_usable = len(inputs)
            detail = {k: {"n_ok": len(v["ok"]), "n_bad": v["n_bad"], "bad_examples": v["bad_examples"]}
                      for k, v in variants.items()}
            items_for_len = next(iter(raw.values()))
        else:
            ok, bad = check_family(tok, raw, digit, raw[:8])
            n_usable = len({x for x, _ in ok})
            detail = {"n_ok": len(ok), "n_bad": len(bad), "bad_examples": [y for _, y in bad[:8]]}
            labels_ok = None
            items_for_len = raw
        # prompt lengths (tokens, with BOS) for the cost model
        zs, eight = [], []
        for j in range(min(64, len(items_for_len) - 8)):
            x, y = items_for_len[j + 8]
            p0 = f"input: {x}\noutput:" + (" " if digit else "")
            zs.append(len(tok.enc(p0)) + 1)
            eight.append(len(tok.enc(demo_block(items_for_len[j:j + 8], digit) + p0)) + 1)
        lookup = f["class"] == "LA" and fid in ("A1", "A2")
        need = N_DEMO if lookup else N_DEMO + N_FIT + N_SCORE
        out["families"][fid] = {
            "class": f["class"], "mapping": f["mapping"], "varies_by_episode": f["varies_by_episode"],
            "digit_answers": digit, "usable_inputs": n_usable, "per_episode_inputs_needed": need,
            "meets_floor": bool(n_usable >= max(FLOOR, need)),
            "labels_or_latents_passing_floor": labels_ok, "check_detail": detail,
            "zero_shot_prompt_tokens": {"mean": round(float(np.mean(zs)), 2), "max": int(max(zs))},
            "eight_shot_prompt_tokens": {"mean": round(float(np.mean(eight)), 2), "max": int(max(eight))},
        }
    fl = out["families"]
    built = [k for k, v in fl.items() if v["meets_floor"]]
    out["summary"] = {
        "families_listed": len(fl), "families_built": len(built), "built": built,
        "episode_specific_built": [k for k in built if fl[k]["class"] in ("LP", "LA")],
        "fixed_function_built": [k for k in built if fl[k]["class"] == "FF"],
        "dropped": [k for k in fl if k not in built],
        "zero_shot_prompt_tokens_max_over_families": max(v["zero_shot_prompt_tokens"]["max"] for v in fl.values()),
        "eight_shot_prompt_tokens_max_over_families": max(v["eight_shot_prompt_tokens"]["max"] for v in fl.values()),
        "zero_shot_prompt_tokens_mean_over_families": round(float(np.mean([v["zero_shot_prompt_tokens"]["mean"] for v in fl.values()])), 2),
        "eight_shot_prompt_tokens_mean_over_families": round(float(np.mean([v["eight_shot_prompt_tokens"]["mean"] for v in fl.values()])), 2),
    }
    # tokenizer facts the registration relies on
    vocab = tok.t.get_vocab()
    out["tokenizer_facts"] = {
        "space_token_id": vocab.get("▁"),
        "space_digit_tokens_present": [d for d in "0123456789" if ("▁" + d) in vocab],
        "digit_tokens": {d: vocab.get(d) for d in "0123456789"},
        "enc('input: 47\\noutput: 4')": tok.enc("input: 47\noutput: 4"),
        "enc('input: 47\\noutput: ')": tok.enc("input: 47\noutput: "),
        "enc('input: cat\\noutput: Cat')": tok.enc("input: cat\noutput: Cat"),
    }
    text = json.dumps(out, indent=1, sort_keys=True)
    out["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    for k, v in fl.items():
        print(k, v["class"], "usable", v["usable_inputs"], "need", v["per_episode_inputs_needed"], "ok" if v["meets_floor"] else "DROP",
              "zs", v["zero_shot_prompt_tokens"], "8s", v["eight_shot_prompt_tokens"],
              (v["check_detail"] if not isinstance(v["check_detail"], dict) or "n_ok" in v["check_detail"] else {kk: (vv["n_ok"], vv["bad_examples"][:3]) for kk, vv in v["check_detail"].items()}))
    print(json.dumps(out["summary"], indent=1))
    print(json.dumps(out["tokenizer_facts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
