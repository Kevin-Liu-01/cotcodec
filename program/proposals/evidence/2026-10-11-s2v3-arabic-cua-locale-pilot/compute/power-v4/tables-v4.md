
Census of all 106 candidates, n = 4 in the 2x2, n_pl = 2 (cap 6.83 GPU-h):

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.024 | 0.975 | 0.024 | 0.970 | 0.048 | 0.006 | 0.024 | 0.015 | 0.587 | 0.950 |
| task-specific perturbation N(0, 1), both cells | generic | -0.00 | 0.059 | 0.929 | 0.059 | 0.934 | 0.103 | 0.016 | 0.024 | 0.029 | 0.389 | 0.950 |
| reshuffle of 10% of tasks, both cells | generic | -0.02 | 0.129 | 0.816 | 0.129 | 0.863 | 0.218 | 0.036 | 0.025 | 0.068 | 0.079 | 0.949 |
| reshuffle of 30% of tasks, both cells | generic | -0.04 | 0.222 | 0.629 | 0.222 | 0.768 | 0.341 | 0.095 | 0.023 | 0.143 | 0.000 | 0.950 |
| uniform -15%, mirror and placebo alike | generic | -4.31 | 0.961 | 0.066 | 0.961 | 0.034 | 0.960 | 0.003 | 0.027 | 0.014 | 0.640 | 0.949 |
| complete breaks -15%, both alike | generic | -4.35 | 0.859 | 0.181 | 0.859 | 0.135 | 0.840 | 0.019 | 0.024 | 0.076 | 0.093 | 0.950 |
| mirror uniform -10%, placebo none | specific | -2.87 | 0.708 | 0.380 | 0.708 | 0.274 | 0.702 | 0.015 | 0.287 | 0.218 | 0.267 | 0.954 |
| mirror uniform -15%, placebo none | specific | -4.31 | 0.961 | 0.066 | 0.961 | 0.034 | 0.960 | 0.003 | 0.555 | 0.474 | 0.107 | 0.949 |
| mirror uniform -20%, placebo none | specific | -5.74 | 0.998 | 0.004 | 0.998 | 0.002 | 0.998 | 0.000 | 0.795 | 0.741 | 0.034 | 0.947 |
| mirror proportional -15%, placebo none | specific | -4.32 | 0.920 | 0.051 | 0.920 | 0.047 | 0.919 | 0.005 | 0.508 | 0.434 | 0.091 | 0.951 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.34 | 0.881 | 0.126 | 0.881 | 0.105 | 0.871 | 0.011 | 0.432 | 0.472 | 0.083 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.35 | 0.860 | 0.181 | 0.860 | 0.130 | 0.841 | 0.019 | 0.373 | 0.490 | 0.091 | 0.950 |
| mirror mixed-sign -15%, placebo none | specific | -4.30 | 0.928 | 0.101 | 0.928 | 0.062 | 0.921 | 0.007 | 0.501 | 0.491 | 0.099 | 0.955 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.31 | 0.960 | 0.065 | 0.960 | 0.034 | 0.960 | 0.003 | 0.377 | 0.473 | 0.072 | 0.953 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.62 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.588 | 0.503 | 0.109 | 0.949 |

The 105 tasks admitted under checker invariance, n_pl = 2:

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.024 | 0.962 | 0.024 | 0.965 | 0.049 | 0.004 | 0.023 | 0.012 | 0.574 | 0.951 |
| task-specific perturbation N(0, 1), both cells | generic | 0.02 | 0.056 | 0.915 | 0.056 | 0.933 | 0.106 | 0.013 | 0.023 | 0.027 | 0.376 | 0.953 |
| reshuffle of 10% of tasks, both cells | generic | 0.07 | 0.113 | 0.808 | 0.113 | 0.873 | 0.204 | 0.038 | 0.020 | 0.062 | 0.076 | 0.953 |
| reshuffle of 30% of tasks, both cells | generic | 0.16 | 0.201 | 0.619 | 0.201 | 0.784 | 0.334 | 0.091 | 0.027 | 0.140 | 0.000 | 0.953 |
| uniform -15%, mirror and placebo alike | generic | -4.21 | 0.949 | 0.067 | 0.949 | 0.041 | 0.949 | 0.004 | 0.026 | 0.014 | 0.615 | 0.951 |
| complete breaks -15%, both alike | generic | -4.16 | 0.839 | 0.192 | 0.839 | 0.149 | 0.818 | 0.021 | 0.023 | 0.076 | 0.094 | 0.950 |
| mirror uniform -10%, placebo none | specific | -2.81 | 0.661 | 0.397 | 0.661 | 0.309 | 0.656 | 0.015 | 0.261 | 0.195 | 0.287 | 0.950 |
| mirror uniform -15%, placebo none | specific | -4.21 | 0.949 | 0.067 | 0.949 | 0.041 | 0.949 | 0.004 | 0.528 | 0.444 | 0.128 | 0.951 |
| mirror uniform -20%, placebo none | specific | -5.61 | 0.998 | 0.004 | 0.998 | 0.002 | 0.998 | 0.000 | 0.771 | 0.706 | 0.034 | 0.952 |
| mirror proportional -15%, placebo none | specific | -4.22 | 0.902 | 0.053 | 0.902 | 0.050 | 0.901 | 0.005 | 0.484 | 0.411 | 0.107 | 0.951 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.20 | 0.873 | 0.121 | 0.873 | 0.102 | 0.862 | 0.013 | 0.404 | 0.437 | 0.094 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.16 | 0.833 | 0.189 | 0.833 | 0.151 | 0.812 | 0.021 | 0.343 | 0.447 | 0.093 | 0.947 |
| mirror mixed-sign -15%, placebo none | specific | -4.19 | 0.911 | 0.115 | 0.911 | 0.077 | 0.903 | 0.010 | 0.459 | 0.442 | 0.106 | 0.948 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.21 | 0.951 | 0.064 | 0.951 | 0.038 | 0.949 | 0.004 | 0.381 | 0.472 | 0.071 | 0.945 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.41 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.557 | 0.478 | 0.125 | 0.946 |

Census of 106, n_pl = 4 (cap 7.57 GPU-h):

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.025 | 0.970 | 0.025 | 0.971 | 0.048 | 0.005 | 0.023 | 0.022 | 0.822 | 0.950 |
| task-specific perturbation N(0, 1), both cells | generic | -0.02 | 0.058 | 0.927 | 0.058 | 0.935 | 0.102 | 0.013 | 0.027 | 0.061 | 0.564 | 0.947 |
| reshuffle of 10% of tasks, both cells | generic | 0.00 | 0.128 | 0.808 | 0.128 | 0.863 | 0.224 | 0.034 | 0.025 | 0.122 | 0.149 | 0.945 |
| reshuffle of 30% of tasks, both cells | generic | 0.01 | 0.222 | 0.626 | 0.222 | 0.769 | 0.342 | 0.095 | 0.024 | 0.212 | 0.000 | 0.946 |
| uniform -15%, mirror and placebo alike | generic | -4.31 | 0.957 | 0.065 | 0.957 | 0.037 | 0.956 | 0.003 | 0.026 | 0.027 | 0.848 | 0.951 |
| complete breaks -15%, both alike | generic | -4.29 | 0.854 | 0.187 | 0.854 | 0.137 | 0.833 | 0.022 | 0.026 | 0.141 | 0.166 | 0.944 |
| mirror uniform -10%, placebo none | specific | -2.88 | 0.698 | 0.386 | 0.698 | 0.279 | 0.696 | 0.011 | 0.388 | 0.408 | 0.376 | 0.952 |
| mirror uniform -15%, placebo none | specific | -4.31 | 0.957 | 0.065 | 0.957 | 0.037 | 0.956 | 0.003 | 0.721 | 0.744 | 0.126 | 0.951 |
| mirror uniform -20%, placebo none | specific | -5.75 | 0.998 | 0.004 | 0.998 | 0.001 | 0.998 | 0.000 | 0.925 | 0.938 | 0.026 | 0.951 |
| mirror proportional -15%, placebo none | specific | -4.31 | 0.917 | 0.053 | 0.917 | 0.048 | 0.914 | 0.006 | 0.630 | 0.664 | 0.114 | 0.954 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.31 | 0.876 | 0.128 | 0.876 | 0.103 | 0.865 | 0.012 | 0.531 | 0.678 | 0.108 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.29 | 0.849 | 0.192 | 0.849 | 0.141 | 0.831 | 0.019 | 0.452 | 0.689 | 0.115 | 0.946 |
| mirror mixed-sign -15%, placebo none | specific | -4.33 | 0.932 | 0.101 | 0.932 | 0.060 | 0.925 | 0.008 | 0.632 | 0.737 | 0.105 | 0.944 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.31 | 0.961 | 0.063 | 0.961 | 0.032 | 0.961 | 0.003 | 0.482 | 0.693 | 0.083 | 0.955 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.63 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.752 | 0.778 | 0.135 | 0.953 |

K_min = 62 (the confirm split), n_pl = 2:

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.027 | 0.879 | 0.027 | 0.904 | 0.053 | 0.006 | 0.021 | 0.007 | 0.280 | 0.946 |
| task-specific perturbation N(0, 1), both cells | generic | 0.01 | 0.051 | 0.807 | 0.051 | 0.855 | 0.091 | 0.015 | 0.022 | 0.013 | 0.140 | 0.952 |
| reshuffle of 10% of tasks, both cells | generic | -0.03 | 0.125 | 0.635 | 0.125 | 0.751 | 0.205 | 0.039 | 0.025 | 0.059 | 0.014 | 0.949 |
| reshuffle of 30% of tasks, both cells | generic | -0.07 | 0.227 | 0.444 | 0.227 | 0.652 | 0.335 | 0.102 | 0.023 | 0.132 | 0.000 | 0.951 |
| uniform -15%, mirror and placebo alike | generic | -4.32 | 0.848 | 0.061 | 0.848 | 0.060 | 0.845 | 0.014 | 0.022 | 0.008 | 0.319 | 0.949 |
| complete breaks -15%, both alike | generic | -4.30 | 0.718 | 0.203 | 0.718 | 0.201 | 0.685 | 0.034 | 0.022 | 0.064 | 0.013 | 0.948 |
| mirror uniform -10%, placebo none | specific | -2.88 | 0.517 | 0.300 | 0.517 | 0.297 | 0.511 | 0.020 | 0.192 | 0.101 | 0.155 | 0.945 |
| mirror uniform -15%, placebo none | specific | -4.32 | 0.848 | 0.061 | 0.848 | 0.060 | 0.845 | 0.014 | 0.379 | 0.245 | 0.085 | 0.949 |
| mirror uniform -20%, placebo none | specific | -5.75 | 0.977 | 0.006 | 0.977 | 0.006 | 0.978 | 0.003 | 0.601 | 0.462 | 0.030 | 0.948 |
| mirror proportional -15%, placebo none | specific | -4.33 | 0.768 | 0.052 | 0.768 | 0.052 | 0.765 | 0.013 | 0.335 | 0.227 | 0.051 | 0.952 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.29 | 0.729 | 0.144 | 0.729 | 0.143 | 0.709 | 0.023 | 0.277 | 0.269 | 0.050 | 0.948 |
| mirror complete breaks -15%, placebo none | specific | -4.30 | 0.724 | 0.199 | 0.724 | 0.197 | 0.689 | 0.036 | 0.218 | 0.299 | 0.039 | 0.948 |
| mirror mixed-sign -15%, placebo none | specific | -4.31 | 0.809 | 0.103 | 0.809 | 0.102 | 0.797 | 0.017 | 0.336 | 0.256 | 0.068 | 0.949 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.32 | 0.856 | 0.067 | 0.856 | 0.066 | 0.854 | 0.012 | 0.262 | 0.304 | 0.026 | 0.942 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.63 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.404 | 0.264 | 0.092 | 0.951 |
