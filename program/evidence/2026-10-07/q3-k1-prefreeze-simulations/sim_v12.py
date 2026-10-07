"""HOLD (V2, tolerance +1) and V1 (-5) trigger rates on 100 English ML prompts, 2 targets x 3 seeds."""
import numpy as np
rng = np.random.default_rng(5)
N = 200000
for sp, ss, sm in ((6, 4, 0.5), (10, 6, 1.0), (3, 2, 0.3)):
    for b in (-4, -3, -2, -1.5, -1, -0.5, 0):
        P = rng.normal(0, sp / 10, (N, 2, 1))          # prompt component shared by a target's seeds
        Sd = rng.normal(0, np.sqrt(ss**2 / 100 + sm**2), (N, 2, 3))
        d = b + P + Sd                                  # mean(R_ind - R_T) per target and seed
        hold = (d > 1.0).any(axis=(1, 2)).mean()
        v1_fail_any_target = (d < -5.0).any(axis=2).any(axis=1).mean()
        print(f"prompt_sd={sp} seedxprompt_sd={ss} seed_main_sd={sm} true_bias={b:+.1f}: "
              f"P(HOLD)={hold:.3f} P(some target fails V1)={v1_fail_any_target:.3f}")
