| gate | n | median GPU-s | p95 GPU-s | mean GPU-s |
|---|---:|---:|---:|---:|
| A1 | 17 | 2.589 | 7.635 | 3.865 |
| A2 | 17 | 4.983 | 13.613 | 6.556 |
| A3 | 17 | 2.331 | 5.105 | 2.95 |
| A4 | 17 | 1.102 | 3.865 | 1.904 |
| A4_poison | 17 | 1.988 | 6.695 | 3.474 |
| A4_sanitizer | 17 | 1.194 | 2.906 | 1.764 |
| A5 | 17 | 1.034 | 3.534 | 1.778 |
| a | 18 | 1.449 | 15.377 | 3.543 |
| a_1e-3 | 17 | 1.444 | 4.279 | 2.11 |
| a_head_1e-2 | 18 | 0.985 | 15.335 | 3.343 |
| a_head_1e-4 | 18 | 0.973 | 25.368 | 7.037 |
| a_static | 18 | 0.986 | 15.003 | 3.202 |
| b1 | 18 | 1.557 | 16.983 | 3.918 |
| b2 | 17 | 1.906 | 4.729 | 2.623 |
| c | 17 | 5.039 | 22.775 | 9.486 |

| rule | scoring GPU-h | 95% | fixed GPU-h | total GPU-h | high | fits | units |
|---|---:|---|---:|---:|---:|---|---:|
| as-drafted | 1041.59 | 670.66-1359.09 | 14.298 | 1055.888 | 1373.384 | False | 99 |
| all-cap40-m1 | 486.739 | 313.53-635.35 | 14.298 | 501.037 | 649.647 | False | 99 |
| all-cap8-m1-c1 | 159.144 | 102.55-208.0 | 14.298 | 173.442 | 222.297 | False | 99 |
| shared-cap40 | 92.664 | 60.85-134.16 | 14.298 | 106.962 | 148.46 | False | 63 |
| shared-cap40-m1 | 39.302 | 25.83-56.88 | 14.298 | 53.6 | 71.175 | False | 63 |
| shared-cap16-m1 | 23.481 | 15.45-33.95 | 14.298 | 37.779 | 48.243 | False | 63 |
| shared-cap8-m1 | 18.051 | 11.88-26.08 | 14.298 | 32.349 | 40.382 | False | 63 |
| shared-cap8-m1-c1 | 10.994 | 7.23-15.9 | 14.298 | 25.292 | 30.199 | False | 63 |
| shared-cap8-m1-c1-h25 | 8.903 | 5.85-12.88 | 14.298 | 23.201 | 27.176 | False | 63 |
| shared-cap4-m1-c1-h25 | 6.188 | 4.07-8.95 | 14.298 | 20.486 | 23.246 | False | 63 |
| shared-cap2-m1-c1-h25 | 4.83 | 3.18-6.98 | 14.298 | 19.128 | 21.28 | False | 63 |

| trimmed rule | in-scope substrates | units | mutants | scoring GPU-h (all buckets) | fixed GPU-h | total GPU-h (without the open extension) | high | fits | pooled witnessed (planning) | families >= 30 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| trim1-recomputed-paired-concurrency | 69 | 72 | 395.0 | 6.362 | 2.87 | 7.775 | 9.834 | True | 155 | 5 |
| trim2-paired-concurrency | 69 | 78 | 395.0 | 8.593 | 4.185 | 11.322 | 13.416 | False | 155 | 5 |
| trim2-measured-4-per-gpu | 69 | 78 | 395.0 | 14.682 | 4.204 | 15.895 | 20.085 | False | 155 | 5 |
| trim2-q30-paired-concurrency | 69 | 78 | 208.0 | 8.269 | 4.185 | 10.27 | 12.021 | False | 80 | 0 |
| trim2-no-margin-paired-concurrency | 69 | 72 | 395.0 | 6.57 | 4.146 | 9.26 | 11.223 | False | 155 | 5 |
| trim2-store-per-bucket-paired-concurrency | 69 | 78 | 395.0 | 9.397 | 4.185 | 11.89 | 14.135 | False | 155 | 5 |
| trim2-store-per-job-paired-concurrency | 69 | 78 | 395.0 | 9.289 | 4.185 | 11.998 | 14.323 | False | 155 | 5 |
| trim2-store-constant-per-bucket-paired-concurrency | 69 | 78 | 395.0 | 8.799 | 4.185 | 11.5 | 13.555 | False | 155 | 5 |
| trim2-store-constant-per-job-paired-concurrency | 69 | 78 | 395.0 | 8.496 | 4.185 | 11.414 | 13.486 | False | 155 | 5 |
| trim2-store-free-references-per-job-paired-concurrency | 69 | 78 | 395.0 | 7.865 | 4.185 | 10.783 | 12.719 | False | 155 | 5 |
