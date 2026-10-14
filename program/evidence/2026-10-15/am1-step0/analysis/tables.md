# AM1 Step 0 analysis tables (exploratory)

## A/A identity

| Mode | Sampling | Reference | Other | Compared | Identical tokens | Rate [95% CP] | Identical tokens and log-prob bits | Clusters all identical |
|---|---|---|---|---:|---:|---|---:|---:|
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/greedy-all-shuffled | 4096 | 4096 | 1.00000 [0.99910, 1.00000] | 4096 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/greedy-single | 96 | 96 | 1.00000 [0.96230, 1.00000] | 96 | 15 of 15 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/greedy-throttled-c8 | 512 | 512 | 1.00000 [0.99282, 1.00000] | 512 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/greedy-warm-cold | 512 | 512 | 1.00000 [0.99282, 1.00000] | 512 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/greedy-warm-hit | 512 | 512 | 1.00000 [0.99282, 1.00000] | 512 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-a/smoke | 16 | 16 | 1.00000 [0.79409, 1.00000] | 16 | 9 of 9 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-b/greedy-all-canonical | 4096 | 4096 | 1.00000 [0.99910, 1.00000] | 4096 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-b/smoke | 16 | 16 | 1.00000 [0.79409, 1.00000] | 16 | 9 of 9 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-c/greedy-all-canonical | 4096 | 4096 | 1.00000 [0.99910, 1.00000] | 4096 | 16 of 16 |
| batch_invariant | greedy | bi-a/greedy-all-canonical | bi-c/smoke | 16 | 16 | 1.00000 [0.79409, 1.00000] | 16 | 9 of 9 |
| batch_invariant | sampled | bi-a/sampled-canonical | bi-a/sampled-shuffled | 1024 | 1024 | 1.00000 [0.99640, 1.00000] | 1024 | 16 of 16 |
| batch_invariant | sampled | bi-a/sampled-canonical | bi-b/sampled-canonical | 1024 | 1024 | 1.00000 [0.99640, 1.00000] | 1024 | 16 of 16 |
| default | greedy | default-a/greedy-all-canonical | default-a/greedy-all-shuffled | 4096 | 4093 | 0.99927 [0.99786, 0.99985] | 4045 | 13 of 16 |
| default | greedy | default-a/greedy-all-canonical | default-a/greedy-single | 96 | 93 | 0.96875 [0.91138, 0.99351] | 24 | 13 of 15 |
| default | greedy | default-a/greedy-all-canonical | default-a/greedy-throttled-c8 | 512 | 498 | 0.97266 [0.95455, 0.98497] | 80 | 9 of 16 |
| default | greedy | default-a/greedy-all-canonical | default-a/smoke | 16 | 14 | 0.87500 [0.61652, 0.98449] | 4 | 7 of 9 |
| default | greedy | default-a/greedy-all-canonical | default-b/greedy-all-canonical | 4096 | 4096 | 1.00000 [0.99910, 1.00000] | 4095 | 16 of 16 |
| default | greedy | default-a/greedy-all-canonical | default-b/smoke | 16 | 14 | 0.87500 [0.61652, 0.98449] | 4 | 7 of 9 |
| default | sampled | default-a/sampled-canonical | default-a/sampled-shuffled | 1024 | 1022 | 0.99805 [0.99296, 0.99976] | 898 | 15 of 16 |
| default | sampled | default-a/sampled-canonical | default-b/sampled-canonical | 1024 | 1024 | 1.00000 [0.99640, 1.00000] | 987 | 16 of 16 |
| cross-mode | greedy | bi-a/greedy-all-canonical | default-a/greedy-all-canonical | 4096 | 4096 | 1.00000 [0.99910, 1.00000] | 4094 | 16 of 16 |
| cross-mode | sampled | bi-a/sampled-canonical | default-a/sampled-canonical | 1024 | 1024 | 1.00000 [0.99640, 1.00000] | 985 | 16 of 16 |

## Throughput by pass

| Session | Pass | BI | Status | Requests | Wall s | Req/s | Computed prompt tok/s | Output tok/s | Cached share |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| bi-a | greedy-all-canonical | True | complete | 4096 of 4096 | 22.6 | 181.4 | 26056 | 2203 | 0.645 |
| bi-a | greedy-all-shuffled | True | complete | 4096 of 4096 | 24.2 | 169.5 | 25210 | 2059 | 0.632 |
| bi-a | greedy-single | True | complete | 96 of 96 | 26.9 | 3.6 | 1033 | 42 | 0.277 |
| bi-a | greedy-throttled-c8 | True | complete | 512 of 512 | 18.5 | 27.7 | 6307 | 320 | 0.436 |
| bi-a | greedy-warm-cold | True | complete | 512 of 512 | 4.5 | 112.6 | 25028 | 1382 | 0.443 |
| bi-a | greedy-warm-hit | True | complete | 512 of 512 | 1.3 | 407.6 | 3392 | 5003 | 0.979 |
| bi-a | sampled-canonical | True | complete | 1024 of 1024 | 7.7 | 133.0 | 26000 | 1680 | 0.519 |
| bi-a | sampled-shuffled | True | complete | 1024 of 1024 | 8.1 | 127.2 | 24860 | 1607 | 0.519 |
| bi-a | smoke | True | complete | 16 of 16 | 0.8 | 20.8 | 8781 | 271 | 0.108 |
| bi-b | greedy-all-canonical | True | complete | 4096 of 4096 | 22.6 | 181.4 | 26064 | 2204 | 0.645 |
| bi-b | sampled-canonical | True | complete | 1024 of 1024 | 7.6 | 134.7 | 26325 | 1701 | 0.519 |
| bi-b | smoke | True | complete | 16 of 16 | 0.7 | 22.5 | 9535 | 294 | 0.108 |
| bi-c | greedy-all-canonical | True | complete | 4096 of 4096 | 57.8 | 70.9 | 28664 | 861 | 0.000 |
| bi-c | smoke | True | complete | 16 of 16 | 0.7 | 23.3 | 11042 | 304 | 0.000 |
| default-a | greedy-all-canonical | False | complete | 4096 of 4096 | 17.1 | 240.2 | 34506 | 2918 | 0.645 |
| default-a | greedy-all-shuffled | False | complete | 4096 of 4096 | 17.9 | 228.7 | 34019 | 2777 | 0.632 |
| default-a | greedy-single | False | complete | 96 of 96 | 8.7 | 11.0 | 3190 | 132 | 0.277 |
| default-a | greedy-throttled-c8 | False | complete | 512 of 512 | 7.3 | 70.1 | 15951 | 802 | 0.436 |
| default-a | sampled-canonical | False | complete | 1024 of 1024 | 5.7 | 180.6 | 35300 | 2281 | 0.519 |
| default-a | sampled-shuffled | False | complete | 1024 of 1024 | 5.9 | 175.0 | 34208 | 2211 | 0.519 |
| default-a | smoke | False | complete | 16 of 16 | 0.4 | 35.6 | 15078 | 508 | 0.108 |
| default-b | greedy-all-canonical | False | complete | 4096 of 4096 | 17.2 | 238.7 | 34281 | 2899 | 0.645 |
| default-b | sampled-canonical | False | complete | 1024 of 1024 | 5.7 | 179.3 | 35052 | 2265 | 0.519 |
| default-b | smoke | False | complete | 16 of 16 | 0.4 | 43.1 | 18248 | 615 | 0.108 |

## Batch-invariant over default wall time (matched passes)

| BI session | Default session | Pass | BI wall s | Default wall s | Ratio |
|---|---|---|---:|---:|---:|
| bi-a | default-a | greedy-all-canonical | 22.6 | 17.1 | 1.324 |
| bi-a | default-a | greedy-all-shuffled | 24.2 | 17.9 | 1.349 |
| bi-a | default-a | greedy-single | 26.9 | 8.7 | 3.088 |
| bi-a | default-a | greedy-throttled-c8 | 18.5 | 7.3 | 2.529 |
| bi-a | default-a | sampled-canonical | 7.7 | 5.7 | 1.358 |
| bi-a | default-a | sampled-shuffled | 8.1 | 5.9 | 1.376 |
| bi-b | default-b | greedy-all-canonical | 22.6 | 17.2 | 1.315 |
| bi-b | default-b | sampled-canonical | 7.6 | 5.7 | 1.332 |

Engine start (s): bi-a 92.4, default-a 62.8, bi-b 37.9, default-b 26.2, bi-c 61.5

## Cost of the 256-subset tables (greedy-all-canonical passes)

| Session | BI | Wall s | GPU-s per question (2 arms) | GPU-s per table | 200-question study, GPU-h |
|---|---|---:|---:|---:|---:|
| bi-a | True | 22.6 | 2.82 | 1.41 | 0.157 |
| bi-b | True | 22.6 | 2.82 | 1.41 | 0.157 |
| bi-c | True | 57.8 | 7.23 | 3.61 | 0.401 |
| default-a | False | 17.1 | 2.13 | 1.07 | 0.118 |
| default-b | False | 17.2 | 2.15 | 1.07 | 0.119 |

## Demo tables (batch-invariant reference pass; crude containment utility)

| Question | Type | Arm | Gold in pool | Distinct replies | Mean u | u(full) | u(empty) | Constant | Order>=2 share | AND/OR baseline | LOO regret min/mean/max | Shapley regret min/mean/max |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| 6e984301 | temporal-reasoning | retrieved | 2 | 15 | 0.012 | 0 | 0 | False | 0.937 | 0.333 | 0/0.97/1 (70) | 0/0.00/0 (2) |
| 6e984301 | temporal-reasoning | gold | 2 | 9 | 0.004 | 0 | 0 | False | 0.969 | 0.333 | 0/0.00/0 (70) | 0/0.00/0 (5) |
| gpt4_70e84552 | temporal-reasoning | retrieved | 2 | 27 | 0.055 | 0 | 0 | False | 0.843 | 0.333 | 0/0.91/1 (35) | 0/0.00/0 (1) |
| gpt4_70e84552 | temporal-reasoning | gold | 2 | 26 | 0.074 | 0 | 0 | False | 0.879 | 0.333 | 0/0.90/1 (70) | 1/1.00/1 (1) |
| 09ba9854 | multi-session | retrieved | 2 | 38 | 0.438 | 1 | 0 | False | 0.175 | 0.333 | 0/0.11/1 (35) | 0/0.00/0 (1) |
| 09ba9854 | multi-session | gold | 2 | 40 | 0.250 | 1 | 0 | False | 0.333 | 0.333 | 0/0.00/0 (15) | 0/0.00/0 (15) |
| e6041065 | multi-session | retrieved | 2 | 13 | 0.449 | 1 | 0 | False | 0.167 | 0.333 | 0/0.09/1 (35) | 0/0.00/0 (1) |
| e6041065 | multi-session | gold | 2 | 13 | 0.438 | 1 | 0 | False | 0.190 | 0.333 | 0/0.14/1 (35) | 0/0.00/0 (2) |
| 618f13b2 | knowledge-update | retrieved | 2 | 8 | 0.457 | 1 | 0 | False | 0.142 | 0.333 | 0/0.00/0 (5) | 0/0.00/0 (1) |
| 618f13b2 | knowledge-update | gold | 2 | 5 | 0.500 | 1 | 0 | False | 0.000 | 0.333 | 0/0.00/0 (35) | 0/0.00/0 (35) |
| 6aeb4375 | knowledge-update | retrieved | 2 | 7 | 0.496 | 1 | 0 | False | 0.015 | 0.333 | 0/0.00/0 (35) | 0/0.00/0 (10) |
| 6aeb4375 | knowledge-update | gold | 2 | 7 | 0.477 | 1 | 0 | False | 0.080 | 0.333 | 0/0.06/1 (35) | 0/0.00/0 (1) |
| 25e5aa4f | single-session-user | retrieved | 0 | 1 | 0.000 | 0 | 0 | True |  |  |  |  |
| 25e5aa4f | single-session-user | gold | 1 | 2 | 0.000 | 0 | 0 | True |  | 0.000 |  |  |
| 3d86fd0a | single-session-user | retrieved | 1 | 3 | 0.500 | 1 | 0 | False | 0.000 | 0.000 | 0/0.00/0 (35) | 0/0.00/0 (35) |
| 3d86fd0a | single-session-user | gold | 1 | 2 | 0.500 | 1 | 0 | False | 0.000 | 0.000 | 0/0.00/0 (35) | 0/0.00/0 (35) |
