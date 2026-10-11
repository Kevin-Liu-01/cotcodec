"""Budget-matched designs (~2,950 episodes = 8 GPU-h at S1a's 9B 0.0027 GPU-h/episode), 4 cells."""
import sys
sys.argv = [sys.argv[0], sys.argv[1], "1", sys.argv[2], sys.argv[3]]
import guards as g
print(f"budget-matched; prior {g.PRIOR}; sigma* {g.SIGMA_STAR}; reps {g.REPS}", flush=True)
for K, n in ((46, 16), (64, 11), (100, 7)):
    for st in ("null", "uniform", "quarter", "breaks"):
        print(K, n, st, g.run(K, n, st), flush=True)
