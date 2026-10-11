MAIN
Census of all 106 pool tasks, n = 4 (cap 6.10 GPU-h). Nulls:

| Null structure | census true D (pp) | PRESENT_HARM | PRESENT_BENEFIT | SMALL | INCONCLUSIVE | 95% coverage of the census D | SMALL_POP (population, with guard) | v2's rule: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| homogeneous (no effect) | 0.00 | 0.029 | 0.025 | 0.971 | 0.004 | 0.946 | 0.963 | 0.958 |
| task-specific logit perturbation N(0, 1) | -0.02 | 0.058 | 0.062 | 0.924 | 0.009 | 0.947 | 0.843 | 0.802 |
| reshuffle of 10% of tasks | 0.00 | 0.121 | 0.125 | 0.817 | 0.007 | 0.944 | 0.497 | 0.551 |
| reshuffle of 30% of tasks | 0.00 | 0.218 | 0.221 | 0.624 | 0.011 | 0.948 | 0.037 | 0.051 |

Alternatives (relative layout effect RD on the census; the absolute census D is about 0.29 x RD):

| Structure | RD | census true D (pp) | PRESENT_HARM | SMALL | SMALL when the census truth is beyond a margin | 95% coverage | SMALL_POP | v2's rule: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| uniform logit shift | -0.10 | -2.87 | 0.707 | 0.386 | n/a | 0.947 | 0.364 | 0.487 |
| uniform logit shift | -0.15 | -4.30 | 0.958 | 0.068 | 0.027 | 0.947 | 0.060 | 0.136 |
| uniform logit shift | -0.20 | -5.73 | 0.999 | 0.003 | 0.003 | 0.949 | 0.002 | 0.017 |
| uniform logit shift | -0.30 | -8.60 | 1.000 | 0.000 | 0.000 | 0.947 | 0.000 | 0.000 |
| proportional, every task | -0.10 | -2.87 | 0.651 | 0.330 | n/a | 0.949 | 0.330 | 0.414 |
| proportional, every task | -0.15 | -4.31 | 0.920 | 0.051 | 0.051 | 0.948 | 0.052 | 0.107 |
| proportional, every task | -0.20 | -5.74 | 0.990 | 0.003 | 0.003 | 0.947 | 0.002 | 0.015 |
| proportional, every task | -0.30 | -8.61 | 1.000 | 0.000 | 0.000 | 0.942 | 0.000 | 0.000 |
| proportional, a quarter of tasks | -0.10 | -2.87 | 0.636 | 0.382 | 0.014 | 0.951 | 0.292 | 0.354 |
| proportional, a quarter of tasks | -0.15 | -4.30 | 0.877 | 0.132 | 0.014 | 0.948 | 0.070 | 0.126 |
| proportional, a quarter of tasks | -0.20 | -5.74 | 0.962 | 0.042 | 0.007 | 0.948 | 0.014 | 0.034 |
| complete breaks | -0.10 | -2.86 | 0.633 | 0.434 | 0.012 | 0.951 | 0.266 | 0.351 |
| complete breaks | -0.15 | -4.29 | 0.849 | 0.188 | 0.009 | 0.951 | 0.088 | 0.138 |
| complete breaks | -0.20 | -5.73 | 0.952 | 0.062 | 0.005 | 0.954 | 0.022 | 0.041 |
| complete breaks | -0.30 | -8.59 | 0.998 | 0.003 | 0.001 | 0.947 | 0.001 | 0.002 |
| mixed-sign perturbation, mean shifted | -0.15 | -4.31 | 0.924 | 0.109 | 0.017 | 0.945 | 0.061 | 0.116 |
| mixed-sign perturbation, mean shifted | -0.30 | -8.61 | 1.000 | 0.000 | 0.000 | 0.942 | 0.000 | 0.000 |
BYK
By task count and episodes (census frame; 'at -15%' is the range over the five alternative structures):

| Task set | K | n | cap GPU-h | census SE of D (pp, null) | SMALL, homogeneous null | SMALL, perturbation null | SMALL, 10% reshuffle | PRESENT_HARM at RD -15% | PRESENT_HARM at RD -20% | max SMALL when beyond a margin | SMALL_POP, homogeneous null |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| census_all_106 | 106 | 4 | 6.10 | 1.16 | 0.971 | 0.924 | 0.817 | 0.849-0.958 | 0.952-0.999 | 0.051 | 0.963 |
| census_all_106 | 106 | 6 | 9.03 | 0.95 | 0.995 | 0.976 | 0.895 | 0.911-0.995 | 0.976-1.000 | 0.051 | 0.993 |
| census_all_106 | 106 | 8 | 11.97 | 0.82 | 1.000 | 0.993 | 0.925 | 0.944-0.999 | 0.986-1.000 | 0.072 | 1.000 |
| without_dev_89 | 89 | 4 | 5.15 | 1.26 | 0.946 | 0.895 | 0.761 | 0.819-0.928 | 0.936-0.995 | 0.056 | 0.932 |
| confirm_only_62 | 62 | 4 | 3.67 | 1.44 | 0.876 | 0.802 | 0.628 | 0.726-0.864 | 0.865-0.981 | 0.051 | 0.858 |
| confirm_only_62 | 62 | 8 | 7.08 | 1.02 | 0.994 | 0.957 | 0.808 | 0.840-0.986 | 0.935-1.000 | 0.059 | 0.988 |
| v2_K26_like_confirm_informative | 26 | 16 | 5.98 | 1.50 | 0.904 | 0.665 | 0.437 | 0.887-1.000 | 0.956-1.000 | 0.031 | 0.001 |

The K = 26 row is v2's kind of set (26 confirm tasks solved at least once in S1a), shown under v3's census rule for comparison: there the population-frame SMALL with the concentration guard is 0.001 and v2's own rule 0.002 at the null, and a direction-free 10% reshuffle gives PRESENT_HARM 0.46 because the selected tasks regress (census true D -2.9 pp): the selection effect the census avoids. Its RD targets are on a set with mean success near 0.6, so its absolute effects are about twice the census's. n = 6 and 8 at K = 106 cap above 8 GPU-h (9.03 and 11.97) and are shown only to size the value of reruns.
