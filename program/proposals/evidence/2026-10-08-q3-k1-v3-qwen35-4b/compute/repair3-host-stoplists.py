"""K1 v3 repair under D52: stop lists for the literal rules, from K1's haystack sources (host CPU).

Rule E's stop list is "the 100 most frequent token ids of the development haystack of the needle
language" and rule F's n-gram stop list "the 200 most frequent n-grams of the development haystack of
that language". The v3 bundle builder does not exist, so the development haystack is proxied by the
first N documents of K1's haystack source per language (FineWeb-2 test file; the FineWeb shard for
English), each cut at 8,000 characters. N = 400 (the wave-2 feasibility refuter's proxy) and 1,000
(about one development partition's haystack: 122 needles x 8K tokens). Output: ranked ids (top 400)
and ranked n-grams (top 400) per language and N. No model is run.
"""
import glob
import json
import re
import sys
from collections import Counter

import pyarrow.parquet as pq
from tokenizers import Tokenizer

RAW, TOKP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TOK = Tokenizer.from_file(TOKP)
FW2 = {"ja": "jpn_Jpan", "ko": "kor_Hang", "bn": "ben_Beng", "ta": "tam_Taml", "el": "ell_Grek",
       "he": "heb_Hebr", "ka": "kat_Geor", "th": "tha_Thai", "hi": "hin_Deva", "km": "khm_Khmr"}
NOSPACE = {"ja", "ko", "th", "km", "zh"}
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
out = {}
for lang in ["en"] + list(FW2):
    path = glob.glob(f"{RAW}/fineweb/*.parquet")[0] if lang == "en" else sorted(glob.glob(f"{RAW}/fineweb-2/{FW2[lang]}/*.parquet"))[0]
    texts = []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1000, columns=["text"]):
        texts = [t[:8000] for t in batch.column(0).to_pylist()]
        break
    n = 2 if lang in NOSPACE else 4
    res = {}
    for ndocs in (400, 1000):
        c, g = Counter(), Counter()
        for t in texts[:ndocs]:
            c.update(TOK.encode(t, add_special_tokens=False).ids)
            for w in WORD.findall(t.lower()):
                for i in range(len(w) - n + 1):
                    g[w[i:i + n]] += 1
        res[str(ndocs)] = dict(
            docs=len(texts[:ndocs]), tokens=sum(c.values()),
            ids=[i for i, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:400]],
            ngrams=[x for x, _ in sorted(g.items(), key=lambda kv: (-kv[1], kv[0]))[:400]])
    out[lang] = res
    print(lang, {k: (v["docs"], v["tokens"]) for k, v in res.items()}, file=sys.stderr, flush=True)
json.dump(out, open(OUT, "w"))
