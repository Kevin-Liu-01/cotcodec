**G1: published rates (AER 0.085 and 0.05), c 0-0.5** (6 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| near f = 0.0 | 1.00 | 1.00 / 0.00 / 0.00 | 1.00 / 0.00 / 0.00 |
| near f = 0.03 | 0.93 | 0.18 / 0.00 / 0.82 | 0.66 / 0.00 / 0.34 |
| near f = 0.06 | 0.85 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.1 | 0.76 | 0.00 / 0.00 / 1.00 | 0.00 / 0.98 / 0.02 |
| near f = 0.15 | 0.65 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.25 | 0.46 | 0.00 / 0.96 / 0.04 | 0.00 / 1.00 / 0.00 |
| near f = 0.4 | 0.21 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.7 | -0.07 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.0 | 1.00 | 1.00 / 0.00 / 0.00 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.91 | 0.00 / 0.00 / 1.00 | 0.23 / 0.00 / 0.77 |
| random f = 0.06 | 0.84 | 0.00 / 0.00 / 1.00 | 0.00 / 0.01 / 0.99 |
| random f = 0.1 | 0.74 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.15 | 0.62 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.42 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.18 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.07 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.509, mean P(correct) outside the tolerance zone 0.543, largest P(wrong decisive) 0.0; gold path 0.805, 0.859, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.842, 0.842, 0.01. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.768, 0.768, 0.0.

**G2: published rates, identical errors (c 1)** (3 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| near f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 1.00 / 0.00 / 0.00 |
| near f = 0.03 | 0.92 | 0.00 / 0.00 / 1.00 | 0.42 / 0.00 / 0.58 |
| near f = 0.06 | 0.85 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.1 | 0.76 | 0.00 / 0.00 / 1.00 | 0.00 / 0.83 / 0.17 |
| near f = 0.15 | 0.65 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.25 | 0.45 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.4 | 0.22 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.7 | -0.07 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.91 | 0.00 / 0.00 / 1.00 | 0.21 / 0.00 / 0.79 |
| random f = 0.06 | 0.83 | 0.00 / 0.00 / 1.00 | 0.00 / 0.02 / 0.98 |
| random f = 0.1 | 0.73 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.15 | 0.62 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.42 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.18 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.07 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.0, mean P(correct) outside the tolerance zone 0.0, largest P(wrong decisive) 0.0; gold path 0.78, 0.832, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.054, 0.053, 0.02. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.769, 0.769, 0.0.

**G3: band (AER 0.085-0.15), c 0-0.5** (10 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| near f = 0.0 | 1.00 | 0.20 / 0.00 / 0.80 | 1.00 / 0.00 / 0.00 |
| near f = 0.03 | 0.93 | 0.00 / 0.00 / 1.00 | 0.51 / 0.00 / 0.49 |
| near f = 0.06 | 0.86 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.1 | 0.77 | 0.00 / 0.03 / 0.97 | 0.00 / 0.59 / 0.41 |
| near f = 0.15 | 0.67 | 0.00 / 0.68 / 0.32 | 0.00 / 1.00 / 0.00 |
| near f = 0.25 | 0.48 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.4 | 0.25 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| near f = 0.7 | -0.03 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.0 | 1.00 | 0.23 / 0.00 / 0.77 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.92 | 0.00 / 0.00 / 1.00 | 0.16 / 0.00 / 0.84 |
| random f = 0.06 | 0.85 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.1 | 0.75 | 0.00 / 0.11 / 0.89 | 0.00 / 0.99 / 0.01 |
| random f = 0.15 | 0.63 | 0.00 / 0.77 / 0.23 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.44 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.21 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.03 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.502, mean P(correct) outside the tolerance zone 0.535, largest P(wrong decisive) 0.0; gold path 0.765, 0.816, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.522, 0.553, 0.005. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.753, 0.802, 0.0.

**G4: band edge (AER 0.15), identical errors (c 1)** (3 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| near f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.03 | 0.93 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.06 | 0.86 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.1 | 0.76 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.15 | 0.65 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.25 | 0.47 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.4 | 0.24 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| near f = 0.7 | -0.05 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.03 | 0.92 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.06 | 0.84 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.1 | 0.74 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.15 | 0.63 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.25 | 0.43 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.4 | 0.19 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.7 | -0.05 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |

Summary: band path mean P(decisive) 0.0, mean P(correct) outside the tolerance zone 0.0, largest P(wrong decisive) 0.0; gold path 0.0, 0.0, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.0, 0.0, 0.0. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.0, 0.0, 0.0.

**G5: beyond the band (AER 0.20 at c 0.5; 0.25 at c 1)** (2 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| near f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.45 / 0.00 / 0.55 |
| near f = 0.03 | 0.93 | 0.00 / 0.00 / 1.00 | 0.07 / 0.00 / 0.93 |
| near f = 0.06 | 0.86 | 0.00 / 0.47 / 0.53 | 0.00 / 0.00 / 1.00 |
| near f = 0.1 | 0.77 | 0.00 / 0.50 / 0.50 | 0.00 / 0.12 / 0.88 |
| near f = 0.15 | 0.67 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| near f = 0.25 | 0.49 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| near f = 0.4 | 0.27 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| near f = 0.7 | -0.01 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.41 / 0.00 / 0.58 |
| random f = 0.03 | 0.92 | 0.00 / 0.04 / 0.95 | 0.00 / 0.00 / 1.00 |
| random f = 0.06 | 0.85 | 0.00 / 0.50 / 0.50 | 0.00 / 0.01 / 0.98 |
| random f = 0.1 | 0.76 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.15 | 0.63 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.25 | 0.45 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.4 | 0.22 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.7 | -0.02 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |

Summary: band path mean P(decisive) 0.376, mean P(correct) outside the tolerance zone 0.367, largest P(wrong decisive) 0.045; gold path 0.323, 0.344, 0.0.

