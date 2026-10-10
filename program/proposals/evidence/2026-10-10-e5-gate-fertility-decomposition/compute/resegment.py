#!/usr/bin/env python3
"""S4: feasibility of the registered re-segmentation rule on both subjects' real tokenizers.

CPU only, no model. Implements, in pure Python and without the `tokenizers`
library:

* the canonical encoder of the m-a-p/1.3B-100B-GatedDeltaNet-pure tokenizer
  (SentencePiece-style BPE, 32,000 pieces, Prepend/Replace '▁' normalizer, no
  pre-tokenizer; merges never cross a '▁' boundary, which this script checks);
* the canonical encoder of the RWKV World tokenizer used by
  fla-hub/rwkv7-1.5B-world (greedy longest match over UTF-8 bytes,
  rwkv_vocab_v20230424.txt, parsed with ast.literal_eval, never eval);
* the registered refinement rule R(f, seed): every canonical token of the
  retention span is split into one or more in-vocabulary pieces (byte-fallback
  pieces excluded on the m-a-p tokenizer), by adding one internal boundary at a
  time chosen uniformly among all boundaries that keep every piece in the
  vocabulary, until the span has round(f x N) pieces (N canonical tokens);
* the registered boundary-only rule B(seed): adjacent canonical tokens inside
  one whitespace word are re-bounded at a different in-vocabulary split point,
  so the token count is unchanged (f = 1 exactly) and the boundaries are not
  canonical.

The stand-in text is the CC0 arXiv abstracts in this bundle's snapshots/ (the
registered corpus is WikiText-103, which is not on this machine; abstracts are
denser in rare words, so the achievable fertility measured here is a
conservative estimate for WikiText).

Usage: python resegment.py <map_tokenizer.json> <rwkv_vocab.txt> <snapshots-dir> <out.json>
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path

SEEDS = (42, 43, 44)
TARGETS = (1.5, 2.0, 2.7)
SPAN_TOKENS = 512  # canonical retention-span length on the m-a-p tokenizer (registration)


# --------------------------------------------------------------------------- m-a-p (BPE)
class MapBPE:
    def __init__(self, path: Path) -> None:
        tok = json.loads(path.read_text(encoding="utf-8"))
        model = tok["model"]
        self.vocab: dict[str, int] = model["vocab"]
        self.ranks = {tuple(m): i for i, m in enumerate(model["merges"])}
        self.cross_boundary_merges = sum(
            1 for a, b in model["merges"] if b.startswith("▁") and not set(a) <= {"▁"})
        self.normal = {p for p in self.vocab if not (p.startswith("<0x") and p.endswith(">"))
                       and p not in ("<unk>", "<s>", "</s>")}

    def _bpe(self, chunk: str) -> list[str]:
        parts = list(chunk)
        while len(parts) > 1:
            best, best_rank = None, None
            for i in range(len(parts) - 1):
                r = self.ranks.get((parts[i], parts[i + 1]))
                if r is not None and (best_rank is None or r < best_rank):
                    best, best_rank = i, r
            if best is None:
                break
            parts[best:best + 2] = [parts[best] + parts[best + 1]]
        out: list[str] = []
        for p in parts:  # byte fallback for out-of-vocabulary characters
            out.extend([p] if p in self.vocab else [f"<0x{b:02X}>" for b in p.encode()])
        return out

    def encode(self, text: str) -> list[str]:
        norm = "▁" + text.replace(" ", "▁")
        chunks, cur = [], ""
        for ch in norm:
            if ch == "▁" and cur and not set(cur) <= {"▁"}:
                chunks.append(cur)
                cur = ""
            cur += ch
        if cur:
            chunks.append(cur)
        return [p for c in chunks for p in self._bpe(c)]

    @staticmethod
    def decode(pieces: list[str]) -> str:
        out = bytearray()
        for p in pieces:
            if p.startswith("<0x") and p.endswith(">"):
                out.append(int(p[3:-1], 16))
            else:
                out.extend(p.replace("▁", " ").encode())
        s = out.decode("utf-8", "replace")
        return s[1:] if s.startswith(" ") else s

    def units(self, piece: str) -> list[str]:
        return list(piece)

    def in_vocab(self, piece: str) -> bool:
        return piece in self.normal

    @staticmethod
    def is_word_start(piece: str) -> bool:
        return piece.startswith("▁")


# --------------------------------------------------------------------------- RWKV World (trie)
class RwkvWorld:
    def __init__(self, path: Path) -> None:
        self.vocab: dict[bytes, int] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            idx = int(line[:line.index(" ")])
            raw = ast.literal_eval(line[line.index(" "):line.rindex(" ")])
            b = raw.encode("utf-8") if isinstance(raw, str) else raw
            assert len(b) == int(line[line.rindex(" "):])
            self.vocab[b] = idx
        self.maxlen = max(len(b) for b in self.vocab)

    def encode(self, text: str) -> list[bytes]:
        src, i, out = text.encode("utf-8"), 0, []
        while i < len(src):
            for L in range(min(self.maxlen, len(src) - i), 0, -1):
                if src[i:i + L] in self.vocab:
                    out.append(src[i:i + L])
                    i += L
                    break
            else:
                raise ValueError("byte not in vocabulary")
        return out

    @staticmethod
    def decode(pieces: list[bytes]) -> str:
        return b"".join(pieces).decode("utf-8", "replace")

    @staticmethod
    def units(piece: bytes) -> list[bytes]:
        # split only at UTF-8 character boundaries
        chars = piece.decode("utf-8", "replace")
        if chars.encode("utf-8") != piece:
            return [piece]
        return [c.encode("utf-8") for c in chars]

    def in_vocab(self, piece: bytes) -> bool:
        return piece in self.vocab

    @staticmethod
    def is_word_start(piece: bytes) -> bool:
        return piece[:1] in (b" ", b"\n")


# --------------------------------------------------------------------------- rules
def refine(tok, canon: list, f: float, seed: int) -> tuple[list[list], int]:
    """Registered refinement rule R(f, seed). Returns pieces per canonical token and the shortfall."""
    rng = random.Random(seed)
    units = [tok.units(t) for t in canon]
    cuts: list[set[int]] = [set() for _ in canon]
    target_extra = round(f * len(canon)) - len(canon)
    join = (lambda us: "".join(us)) if isinstance(canon[0], str) else (lambda us: b"".join(us))

    def pieces(i: int) -> list:
        bounds = [0, *sorted(cuts[i]), len(units[i])]
        return [join(units[i][a:b]) for a, b in zip(bounds[:-1], bounds[1:])]

    def candidates(i: int) -> list[int]:
        bounds = [0, *sorted(cuts[i]), len(units[i])]
        out = []
        for a, b in zip(bounds[:-1], bounds[1:]):
            for p in range(a + 1, b):
                if tok.in_vocab(join(units[i][a:p])) and tok.in_vocab(join(units[i][p:b])):
                    out.append(p)
        return out

    cand = [candidates(i) for i in range(len(canon))]
    added = 0
    while added < target_extra:
        # uniform over all (token, boundary) moves: walk the per-token candidate counts
        total = sum(len(c) for c in cand)
        if total == 0:
            break
        r = rng.randrange(total)
        i = 0
        while r >= len(cand[i]):
            r -= len(cand[i])
            i += 1
        p = cand[i][r]
        cuts[i].add(p)
        cand[i] = candidates(i)
        added += 1
    return [pieces(i) for i in range(len(canon))], target_extra - added


def max_refinement(tok, canon: list) -> int:
    """Largest piece count reachable by in-vocabulary splitting (character level where allowed)."""
    total = 0
    for t in canon:
        us = tok.units(t)
        join = (lambda x: "".join(x)) if isinstance(t, str) else (lambda x: b"".join(x))
        # dynamic programme: maximum number of in-vocabulary pieces covering t
        best = [-1] * (len(us) + 1)
        best[0] = 0
        for j in range(1, len(us) + 1):
            for i in range(j):
                if best[i] >= 0 and tok.in_vocab(join(us[i:j])):
                    best[j] = max(best[j], best[i] + 1)
        total += max(best[-1], 1)
    return total


def boundary_only(tok, canon: list, seed: int) -> tuple[list, int, int]:
    """Registered boundary-only rule B(seed): re-bound adjacent in-word pairs, same count."""
    rng = random.Random(seed)
    out = list(canon)
    changed, eligible = 0, 0
    i = 0
    while i < len(out) - 1:
        a, b = out[i], out[i + 1]
        if tok.is_word_start(b):
            i += 1
            continue
        us = tok.units(a) + tok.units(b)
        join = (lambda x: "".join(x)) if isinstance(a, str) else (lambda x: b"".join(x))
        split_now = len(tok.units(a))
        alts = [p for p in range(1, len(us)) if p != split_now
                and tok.in_vocab(join(us[:p])) and tok.in_vocab(join(us[p:]))]
        if alts:
            eligible += 1
            p = alts[rng.randrange(len(alts))]
            out[i], out[i + 1] = join(us[:p]), join(us[p:])
            changed += 1
            i += 2
        else:
            i += 1
    return out, changed, eligible


def strr(pieces_per_token: list[list], canon: list, tok) -> float:
    """Single-token retention over whitespace words: share of words that are still one piece."""
    words, cur = [], []
    for t, ps in zip(canon, pieces_per_token):
        if tok.is_word_start(t) and cur:
            words.append(cur)
            cur = []
        cur.append(len(ps))
    if cur:
        words.append(cur)
    return sum(1 for w in words if sum(w) == 1) / len(words)


def passages(snap_dir: Path, map_tok: MapBPE) -> list[str]:
    abstracts = []
    for p in sorted(snap_dir.glob("arxiv.org_abs_*.json")):
        a = json.loads(p.read_text(encoding="utf-8"))["extract"].get("abstract", "")
        if a:
            abstracts.append(" ".join(a.split()))
    out, cur = [], ""
    for a in abstracts:
        cur = (cur + " " + a).strip()
        if len(map_tok.encode(cur)) >= SPAN_TOKENS:
            out.append(cur)
            cur = ""
    return out


def main() -> int:
    map_path, rwkv_path, snap_dir, out_path = (Path(a) for a in sys.argv[1:5])
    map_tok, rwkv = MapBPE(map_path), RwkvWorld(rwkv_path)
    texts = passages(snap_dir, map_tok)
    blob = map_path.read_bytes()
    result = {
        "inputs": {
            "map_tokenizer_sha256": hashlib.sha256(blob).hexdigest(),
            "map_tokenizer_git_blob_sha1": hashlib.sha1(b"blob %d\0" % len(blob) + blob).hexdigest(),
            "map_tokenizer_hf_oid_expected": "b667161bc937dfaed6f27e9e7849a664c3e869b3",
            "rwkv_vocab_sha256": hashlib.sha256(rwkv_path.read_bytes()).hexdigest(),
            "rwkv_vocab_sha256_expected_prefix": "e6dee3d4",
            "stand_in_text": "CC0 arXiv abstracts from this bundle's snapshots/, concatenated in file order into passages of at least 512 m-a-p tokens",
            "passages": len(texts),
            "passage_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in texts],
            "seeds": list(SEEDS), "targets": list(TARGETS),
        },
        "map_cross_boundary_merges": map_tok.cross_boundary_merges,
        "digits": {},
        "subjects": {},
    }
    for name, tok in (("m-a-p GDN-1.3B (BPE 32k)", map_tok), ("rwkv7-1.5B-world (World trie 65k)", rwkv)):
        codes = ["4821", "1000", "9999", "3570", "6142", "7777"]
        result["digits"][name] = {
            c: [p if isinstance(p, str) else p.decode() for p in tok.encode(f"The code for the old brass lantern is {c}.")][-6:]
            for c in codes}
        rows = []
        for text in texts:
            canon = tok.encode(text)
            assert tok.decode(canon) == text, "canonical decode mismatch"
            words = len(text.split())
            row = {"words": words, "canonical_tokens": len(canon),
                   "tokens_per_word": len(canon) / words,
                   "max_f": max_refinement(tok, canon) / len(canon), "targets": {}}
            for f in TARGETS:
                per_seed = []
                for seed in SEEDS:
                    pieces, short = refine(tok, canon, f, seed)
                    flat = [p for ps in pieces for p in ps]
                    assert tok.decode(flat) == text, "re-segmented decode mismatch"
                    per_seed.append({"realized_f": len(flat) / len(canon), "shortfall_pieces": short,
                                     "share_tokens_split": sum(1 for ps in pieces if len(ps) > 1) / len(canon),
                                     "strr": strr(pieces, canon, tok),
                                     "max_pieces_per_token": max(len(ps) for ps in pieces)})
                row["targets"][str(f)] = per_seed
            b_rows = []
            for seed in SEEDS:
                bnd, changed, eligible = boundary_only(tok, canon, seed)
                assert tok.decode(bnd) == text and len(bnd) == len(canon)
                b_rows.append({"tokens_rebounded_share": 2 * changed / len(canon), "eligible_pairs": eligible})
            row["boundary_only"] = b_rows
            row["canonical_strr"] = strr([[t] for t in canon], canon, tok)
            rows.append(row)
        summ = {"passages": len(rows),
                "tokens_per_word_mean": statistics.mean(r["tokens_per_word"] for r in rows),
                "canonical_strr_mean": statistics.mean(r["canonical_strr"] for r in rows),
                "max_f_min": min(r["max_f"] for r in rows), "max_f_mean": statistics.mean(r["max_f"] for r in rows),
                "boundary_only_rebounded_share_mean": statistics.mean(b["tokens_rebounded_share"] for r in rows for b in r["boundary_only"])}
        for f in TARGETS:
            cells = [s for r in rows for s in r["targets"][str(f)]]
            summ[f"f{f}"] = {
                "realized_f_min": min(c["realized_f"] for c in cells),
                "realized_f_max": max(c["realized_f"] for c in cells),
                "passages_with_shortfall": sum(1 for c in cells if c["shortfall_pieces"] > 0),
                "share_tokens_split_mean": statistics.mean(c["share_tokens_split"] for c in cells),
                "strr_mean": statistics.mean(c["strr"] for c in cells),
                "max_pieces_per_token": max(c["max_pieces_per_token"] for c in cells)}
        result["subjects"][name] = {"summary": summ, "passages": rows}
        print(name, json.dumps(summ, indent=1))
    Path(out_path).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
