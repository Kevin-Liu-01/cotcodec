"""G3 sizing (EXPLORATORY, run on the Mac from the pilot's text-free records): a crude block-pool
simulation of the main math phase at k seeds per question. Step time per 32 tokens is
a + b * running + c * context (Mtok), fitted by eye to binned pilot step times (jobs 1498, 1500);
lengths are resampled from the pilot per question (others from the pooled pilot lengths);
preemption recomputes at the pilot's prefill rate. Run from a directory holding
<model>-fp32-math/records.json. Not part of the analysis."""
import json, numpy as np, math, sys
def lengths(m, k, rng, scale=1.0):
    rec = json.load(open(f"{m}/records.json"))["requests"]
    byq = {}
    for r in rec: byq.setdefault(r["question_index"], []).append(r["completion_len"])
    pool = [r["completion_len"] for r in rec]
    out = []
    for q in range(134):
        for s in range(k):
            L = rng.choice(byq[q]) if q in byq else rng.choice(pool)
            L = min(int(L*scale), 32768)
            out.append((600, L))
    return out
def sim(reqs, blocks, bsz, a, b, c, prefill_rate, max_seqs=512, chunk=32):
    waiting = list(range(len(reqs)))  # FCFS
    gen = [0]*len(reqs); running = []; t = 0.0; preempt = 0; done = 0; recompute_tok = 0
    def need(i): return math.ceil((reqs[i][0]+gen[i]+chunk)/bsz) + 3
    tokens = 0
    while done < len(reqs):
        # admit
        used = sum(need(i) for i in running)
        while waiting and len(running) < max_seqs:
            i = waiting[0]
            if used + need(i) > blocks - 1: break
            waiting.pop(0); running.append(i); used += need(i)
            if gen[i] > 0:
                t += (reqs[i][0]+gen[i]) / prefill_rate; recompute_tok += reqs[i][0]+gen[i]
            else:
                t += reqs[i][0] / prefill_rate
        # preempt newest while over capacity
        while used > blocks - 1 and len(running) > 1:
            j = running.pop(); used -= need(j); waiting.insert(0, j); preempt += 1
        B = len(running); S = sum(reqs[i][0]+gen[i] for i in running)
        dt = (a + b*B + c*S/1e6) / 1000 * chunk
        t += dt
        for i in list(running):
            step = min(chunk, reqs[i][1]-gen[i]); gen[i] += step; tokens += step
            if gen[i] >= reqs[i][1]: running.remove(i); done += 1
    return t, tokens, preempt, recompute_tok
cfgs = {
 ("qwen3.5-4b-fp32-math","fp32"): (3733, 528, 6.1, 0.036, 9.0, 37900),
 ("qwen3.5-4b-fp32-math","16bit"): (7248, 272, 6.1, 0.018, 9.0, 37900),
 ("qwen3.5-9b-fp32-math","fp32"): (3137, 528, 7.8, 0.038, 10.4, 27700),
 ("qwen3.5-9b-fp32-math","16bit"): (6090, 272, 7.8, 0.019, 10.4, 27700),
}
for k in (2, 3, 4):
  for (m, arm), (bl, bs, a, b, c, pr) in cfgs.items():
    for scale in ((1.0, 1.25) if arm == "16bit" else (1.0,)):
        rng = np.random.default_rng(0)
        reqs = lengths(m, k, rng, scale)
        t, tok, pre, rc = sim(reqs, bl, bs, a, b, c, pr)
        print(f"k={k} {m[:10]} {arm} len x{scale}: wall {t:.0f} s, tokens {tok/1e6:.2f}M, {tok/t:.0f} tok/s, preempt {pre}, recompute {rc/1e6:.2f}M")
