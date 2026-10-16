# LM2 tables (EXPLORATORY)

## Accuracy by arm and task (percent of samples correct; 95% item-bootstrap interval)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 38.3 [21.7, 55.0] (20 items, 60 samples) | 46.7 [28.3, 65.0] (20 items, 60 samples) | 50.0 [33.3, 66.7] (20 items, 60 samples) |
| v4f-iq3 | 48.3 [30.0, 66.7] (20 items, 60 samples) | 40.0 [21.7, 58.3] (20 items, 60 samples) | 48.3 [28.3, 68.3] (20 items, 60 samples) |
| v4f-q2 | 38.3 [25.0, 53.3] (20 items, 60 samples) | 33.3 [15.0, 51.7] (20 items, 60 samples) | 51.7 [31.7, 71.7] (20 items, 60 samples) |
| qwen235-q3 | - | - | - |
| gptoss120 | 40.0 [23.3, 58.3] (20 items, 60 samples) | 48.3 [30.0, 66.7] (20 items, 60 samples) | 40.0 [23.3, 56.7] (20 items, 60 samples) |

## Accuracy on the common prefix (math 20 items, code 20 items, knowledge 20 items)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 38.3 [21.7, 55.0] | 46.7 [28.3, 65.0] | 50.0 [33.3, 66.7] |
| v4f-iq3 | 48.3 [30.0, 66.7] | 40.0 [21.7, 58.3] | 48.3 [28.3, 68.3] |
| v4f-q2 | 38.3 [25.0, 53.3] | 33.3 [15.0, 51.7] | 51.7 [31.7, 71.7] |
| qwen235-q3 | - | - | - |
| gptoss120 | 40.0 [23.3, 58.3] | 48.3 [30.0, 66.7] | 40.0 [23.3, 56.7] |

## Quantization cost inside V4 Flash 0731 (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - v4f-q8 | -0.0 [-10.0, +10.0] (items 20, 5/5) | -13.3 [-26.7, -0.0] (items 20, 2/7) | +1.7 [-11.7, +15.0] (items 20, 5/4) | -3.9 [-11.1, +3.3] |
| v4f-iq3 - v4f-q8 | +10.0 [-1.7, +23.3] (items 20, 5/2) | -6.7 [-15.0, +1.7] (items 20, 1/4) | -1.7 [-13.3, +11.7] (items 20, 4/5) | +0.6 [-6.1, +7.2] |
| v4f-q2 - v4f-iq3 | -10.0 [-20.0, -0.0] (items 20, 2/8) | -6.7 [-15.0, +1.7] (items 20, 1/4) | +3.3 [-10.0, +16.7] (items 20, 5/4) | -4.4 [-10.6, +1.7] |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - v4f-q8 math 14.9, code 18.9, knowledge 18.1, task mean 10.1; v4f-iq3 - v4f-q8 math 17.7, code 12.5, knowledge 17.7, task mean 9.5; v4f-q2 - v4f-iq3 math 13.4, code 12.4, knowledge 19.5, task mean 9.0.

## Between models (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - qwen235-q3 | - | - | - | - |
| v4f-q2 - gptoss120 | -1.7 [-15.0, +11.7] (items 20, 4/7) | -15.0 [-30.0, +1.7] (items 20, 1/8) | +11.7 [-8.3, +33.3] (items 20, 8/5) | -1.7 [-11.7, +8.3] |
| v4f-iq3 - qwen235-q3 | - | - | - | - |
| v4f-iq3 - gptoss120 | +8.3 [-1.7, +20.0] (items 20, 5/2) | -8.3 [-20.0, +3.3] (items 20, 1/5) | +8.3 [-6.7, +25.0] (items 20, 5/3) | +2.8 [-5.0, +10.6] |
| qwen235-q3 - gptoss120 | - | - | - | - |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - gptoss120 math 19.1, code 23.4, knowledge 29.9, task mean 14.2; v4f-iq3 - gptoss120 math 15.8, code 17.4, knowledge 22.7, task mean 10.9.

## Output tokens and truncation

| Arm | Task | Mean tokens | Median | Mean tokens (correct) | Tokens per correct | Truncated % | No answer % |
|---|---|---:|---:|---:|---:|---:|---:|
| v4f-q8 | math | 1717 | 1110 | 1178 | 4480 | 3.3 | 3.3 |
| v4f-q8 | code | 1377 | 474 | 439 | 2951 | 6.7 | 6.7 |
| v4f-q8 | knowledge | 223 | 126 | 187 | 446 | 0.0 | 0.0 |
| v4f-iq3 | math | 2101 | 1471 | 1610 | 4348 | 10.0 | 10.0 |
| v4f-iq3 | code | 2389 | 1203 | 472 | 5973 | 31.7 | 31.7 |
| v4f-iq3 | knowledge | 277 | 127 | 217 | 572 | 1.7 | 1.7 |
| v4f-q2 | math | 2255 | 1426 | 1600 | 5882 | 13.3 | 13.3 |
| v4f-q2 | code | 3107 | 2360 | 517 | 9321 | 40.0 | 40.0 |
| v4f-q2 | knowledge | 358 | 118 | 156 | 694 | 1.7 | 1.7 |
| gptoss120 | math | 1386 | 1291 | 1786 | 3465 | 0.0 | 0.0 |
| gptoss120 | code | 1622 | 1336 | 1017 | 3355 | 0.0 | 0.0 |
| gptoss120 | knowledge | 274 | 164 | 286 | 684 | 0.0 | 0.0 |

## Throughput on the H100s (llama.cpp b11669, layer split)

| Arm | Job (phase) | GPUs | Slots | Load s | Aggregate tok/s (all slots busy) | tok/s per GPU | Generated tokens | Completed requests |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| gptoss120 | 1804 (pilot) | 2 | 48 | 22.66 | 280.2 | 140.1 | 70270 | 19 |
| gptoss120 | 1832 (diag, -bs) | 2 | 48 | 13.55 | 467.5 | 233.8 | 12811 | 24 |
| gptoss120 | 1844 (main) | 1 | 24 | 12.05 | 364.3 | 364.3 | 496582 | 478 |
| qwen235-q3 | 1987 (main) | 2 | 28 | 75.72 | 145.3 | 72.7 | 140333 | 36 |
| v4f-iq3 | 1865 (main) | 2 | 64 | 70.68 | 213.1 | 106.6 | 364374 | 230 |
| v4f-iq3 | 1974 (main) | 2 | 64 | 41.11 | 132.5 | 66.3 | 104994 | 24 |
| v4f-q2 | 1802 (pilot) | 2 | 64 | 43.14 | 199.5 | 99.8 | 45147 | 15 |
| v4f-q2 | 1830 (diag, -bs) | 2 | 64 | 25.82 | 208.8 | 104.4 | 38259 | 12 |
| v4f-q2 | 1842 (main) | 2 | 64 | 21.1 | 177.8 | 88.9 | 417479 | 199 |
| v4f-q2 | 1933 (cancelled; no summary) | 2 | 30 | None | 168.7 | 84.3 | 93963 | None |
| v4f-q2 | 1949 (cancelled; no summary) | 2 | 64 | None | 142.4 | 71.2 | 6744 | None |
| v4f-q2 | 1955 (main) | 2 | 64 | 22.07 | 132.0 | 66.0 | 128753 | 3 |
| v4f-q8 | 1898 (main) | 3 | 64 | 82.24 | 222.6 | 74.2 | 277185 | 270 |

## Quality against resident memory on a 128 GB machine

| Arm | File GB | Weights GiB | KV at 32K GiB | Resident at 32K GiB | Fit tier | Mac decode tok/s (basis) | math acc | code acc | knowledge acc |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|
| v4f-q8 | 161.9 | 150.8 | 0.27 | 154.0 | No | does not fit (reference only) | 38.33 | 46.67 | 50.0 |
| v4f-iq3 | 104.2 | 97.1 | 0.27 | 100.3 | Tight | 36.0 (estimate, dossier row F2: 31-41 (midpoint)) | 48.33 | 40.0 | 48.33 |
| v4f-q2 | 86.7 | 80.8 | 0.27 | 84.0 | Yes | 39.35 (measured, ds4 maintainer, 2K context (S95)) | 38.33 | 33.33 | 51.67 |
| qwen235-q3 | 104.2 | 97.0 | 5.875 | 105.9 | Tight | 31.0 (estimate, dossier row Q2: 27-35 (midpoint)) | - | - | - |
| gptoss120 | 63.4 | 59.0 | 1.1 | 63.1 | Yes | 105.0 (community report, upstream llama.cpp tg128 (S97)) | 40.0 | 48.33 | 40.0 |

# Secondary reading: completed responses at the 16,384 run cap only

## Accuracy by arm and task (percent of samples correct; 95% item-bootstrap interval)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 40.0 [23.3, 56.7] (20 items, 60 samples) | 46.7 [28.3, 65.0] (20 items, 60 samples) | 50.0 [33.3, 66.7] (20 items, 60 samples) |
| v4f-iq3 | 48.3 [30.0, 66.7] (20 items, 56 samples) | 51.9 [31.5, 72.2] (18 items, 41 samples) | 48.3 [28.3, 68.3] (20 items, 59 samples) |
| v4f-q2 | 41.7 [28.3, 55.0] (20 items, 58 samples) | 48.9 [28.9, 68.9] (15 items, 40 samples) | 51.7 [31.7, 71.7] (20 items, 60 samples) |
| qwen235-q3 | - | - | - |
| gptoss120 | 40.0 [23.3, 58.3] (20 items, 60 samples) | 48.3 [30.0, 66.7] (20 items, 60 samples) | 40.0 [23.3, 56.7] (20 items, 60 samples) |

## Accuracy on the common prefix (math 20 items, code 20 items, knowledge 20 items)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 40.0 [23.3, 56.7] | 46.7 [28.3, 65.0] | 50.0 [33.3, 66.7] |
| v4f-iq3 | 48.3 [30.0, 66.7] | 51.9 [31.5, 72.2] | 48.3 [28.3, 68.3] |
| v4f-q2 | 41.7 [28.3, 55.0] | 48.9 [28.9, 68.9] | 51.7 [31.7, 71.7] |
| qwen235-q3 | - | - | - |
| gptoss120 | 40.0 [23.3, 58.3] | 48.3 [30.0, 66.7] | 40.0 [23.3, 56.7] |

## Quantization cost inside V4 Flash 0731 (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - v4f-q8 | +1.7 [-10.0, +13.3] (items 20, 5/5) | -11.1 [-28.9, +4.4] (items 15, 2/4) | +1.7 [-11.7, +15.0] (items 20, 5/4) | -2.6 [-10.7, +5.4] |
| v4f-iq3 - v4f-q8 | +8.3 [-3.3, +21.7] (items 20, 5/3) | +1.9 [-3.7, +7.4] (items 18, 2/1) | -1.7 [-13.3, +11.7] (items 20, 4/5) | +2.8 [-3.6, +9.1] |
| v4f-q2 - v4f-iq3 | -6.7 [-16.7, +3.3] (items 20, 3/7) | -9.5 [-28.6, +4.8] (items 14, 2/4) | +3.3 [-10.0, +16.7] (items 20, 5/4) | -4.3 [-12.5, +3.3] |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - v4f-q8 math 17.0, code 24.4, knowledge 18.1, task mean 11.6; v4f-iq3 - v4f-q8 math 18.7, code 9.0, knowledge 17.7, task mean 9.2; v4f-q2 - v4f-iq3 math 14.3, code 24.1, knowledge 19.5, task mean 11.4.

## Between models (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - qwen235-q3 | - | - | - | - |
| v4f-q2 - gptoss120 | +0.8 [-12.5, +15.0] (items 20, 5/6) | -16.7 [-38.9, +6.7] (items 15, 1/6) | +11.7 [-8.3, +33.3] (items 20, 8/5) | -1.4 [-12.6, +10.0] |
| v4f-iq3 - qwen235-q3 | - | - | - | - |
| v4f-iq3 - gptoss120 | +5.0 [-10.0, +18.3] (items 20, 5/2) | -1.9 [-13.0, +11.1] (items 18, 2/3) | +8.3 [-6.7, +25.0] (items 20, 5/3) | +3.8 [-4.4, +12.2] |
| qwen235-q3 - gptoss120 | - | - | - | - |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - gptoss120 math 19.9, code 32.0, knowledge 29.9, task mean 16.0; v4f-iq3 - gptoss120 math 20.9, code 17.3, knowledge 22.7, task mean 11.8.

## Output tokens and truncation

| Arm | Task | Mean tokens | Median | Mean tokens (correct) | Tokens per correct | Truncated % | No answer % |
|---|---|---:|---:|---:|---:|---:|---:|
| v4f-q8 | math | 1717 | 1110 | 1397 | 4293 | 0.0 | 0.0 |
| v4f-q8 | code | 1377 | 474 | 439 | 2951 | 0.0 | 0.0 |
| v4f-q8 | knowledge | 223 | 126 | 187 | 446 | 0.0 | 0.0 |
| v4f-iq3 | math | 1837 | 1313 | 1610 | 3548 | 0.0 | 0.0 |
| v4f-iq3 | code | 1012 | 436 | 670 | 1660 | 0.0 | 0.0 |
| v4f-iq3 | knowledge | 182 | 126 | 217 | 371 | 0.0 | 0.0 |
| v4f-q2 | math | 1765 | 1331 | 1785 | 4096 | 0.0 | 0.0 |
| v4f-q2 | code | 1256 | 864 | 823 | 2284 | 0.0 | 0.0 |
| v4f-q2 | knowledge | 358 | 118 | 156 | 694 | 0.0 | 0.0 |
| gptoss120 | math | 1386 | 1291 | 1786 | 3465 | 0.0 | 0.0 |
| gptoss120 | code | 1622 | 1336 | 1017 | 3355 | 0.0 | 0.0 |
| gptoss120 | knowledge | 274 | 164 | 286 | 684 | 0.0 | 0.0 |


# Reading at a 4,096-token budget, with Qwen3-235B on its determined prefix

## Accuracy by arm and task (percent of samples correct; 95% item-bootstrap interval)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 38.3 [21.7, 55.0] (20 items, 60 samples) | 46.7 [28.3, 65.0] (20 items, 60 samples) | 50.0 [33.3, 66.7] (20 items, 60 samples) |
| v4f-iq3 | 46.7 [28.3, 65.0] (20 items, 60 samples) | 40.0 [21.7, 58.3] (20 items, 60 samples) | 48.3 [28.3, 68.3] (20 items, 60 samples) |
| v4f-q2 | 36.7 [23.3, 50.0] (20 items, 60 samples) | 33.3 [15.0, 51.7] (20 items, 60 samples) | 51.7 [31.7, 71.7] (20 items, 60 samples) |
| qwen235-q3 | 0.0 [0.0, 0.0] (3 items, 9 samples) | 50.0 [16.7, 83.3] (6 items, 18 samples) | 76.2 [47.6, 95.2] (7 items, 21 samples) |
| gptoss120 | 40.0 [23.3, 58.3] (20 items, 60 samples) | 48.3 [30.0, 66.7] (20 items, 60 samples) | 40.0 [23.3, 56.7] (20 items, 60 samples) |

## Accuracy on the common prefix (math 3 items, code 6 items, knowledge 7 items)

| Arm | math | code | knowledge |
|---|---|---|---|
| v4f-q8 | 0.0 [0.0, 0.0] | 55.6 [16.7, 88.9] | 57.1 [33.3, 81.0] |
| v4f-iq3 | 22.2 [0.0, 66.7] | 44.4 [11.1, 77.8] | 47.6 [14.3, 81.0] |
| v4f-q2 | 11.1 [0.0, 33.3] | 33.3 [5.6, 66.7] | 47.6 [19.1, 76.2] |
| qwen235-q3 | 0.0 [0.0, 0.0] | 50.0 [16.7, 83.3] | 76.2 [47.6, 95.2] |
| gptoss120 | 11.1 [0.0, 33.3] | 61.1 [27.8, 88.9] | 47.6 [19.1, 71.4] |

## Quantization cost inside V4 Flash 0731 (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - v4f-q8 | -1.7 [-11.7, +8.3] (items 20, 4/5) | -13.3 [-26.7, -0.0] (items 20, 2/7) | +1.7 [-11.7, +15.0] (items 20, 5/4) | -4.4 [-11.7, +2.2] |
| v4f-iq3 - v4f-q8 | +8.3 [-3.3, +21.7] (items 20, 4/2) | -6.7 [-15.0, +1.7] (items 20, 1/4) | -1.7 [-13.3, +11.7] (items 20, 4/5) | +0.0 [-6.7, +6.7] |
| v4f-q2 - v4f-iq3 | -10.0 [-20.0, -0.0] (items 20, 2/8) | -6.7 [-15.0, +1.7] (items 20, 1/4) | +3.3 [-10.0, +16.7] (items 20, 5/4) | -4.4 [-10.6, +1.7] |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - v4f-q8 math 14.2, code 18.9, knowledge 18.1, task mean 10.0; v4f-iq3 - v4f-q8 math 17.5, code 12.5, knowledge 17.7, task mean 9.4; v4f-q2 - v4f-iq3 math 13.4, code 12.4, knowledge 19.5, task mean 9.0.

## Between models (paired, points)

| Contrast | math | code | knowledge | task mean |
|---|---|---|---|---|
| v4f-q2 - qwen235-q3 | +11.1 [+0.0, +33.3] (items 3, 1/0) | -16.7 [-38.9, +0.0] (items 6, 0/2) | -28.6 [-66.7, +14.3] (items 7, 2/4) | -11.4 [-27.8, +5.6] |
| v4f-q2 - gptoss120 | -3.3 [-15.0, +10.0] (items 20, 4/7) | -15.0 [-30.0, +1.7] (items 20, 1/8) | +11.7 [-8.3, +33.3] (items 20, 8/5) | -2.2 [-11.7, +7.8] |
| v4f-iq3 - qwen235-q3 | +22.2 [+0.0, +66.7] (items 3, 1/0) | -5.6 [-33.3, +16.7] (items 6, 1/1) | -28.6 [-61.9, +0.0] (items 7, 1/4) | -4.0 [-21.4, +14.0] |
| v4f-iq3 - gptoss120 | +6.7 [-3.3, +16.7] (items 20, 5/2) | -8.3 [-20.0, +3.3] (items 20, 1/5) | +8.3 [-6.7, +25.0] (items 20, 5/3) | +2.2 [-5.0, +9.4] |
| qwen235-q3 - gptoss120 | -11.1 [-33.3, +0.0] (items 3, 0/1) | -11.1 [-22.2, +0.0] (items 6, 0/2) | +28.6 [+0.0, +61.9] (items 7, 4/1) | +2.1 [-10.3, +14.6] |

Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: v4f-q2 - qwen235-q3 math 25.6, code 29.3, knowledge 61.1, task mean 24.1; v4f-q2 - gptoss120 math 17.3, code 23.4, knowledge 29.9, task mean 14.0; v4f-iq3 - qwen235-q3 math 51.2, code 34.2, knowledge 44.5, task mean 25.2; v4f-iq3 - gptoss120 math 14.1, code 17.4, knowledge 22.7, task mean 10.6; qwen235-q3 - gptoss120 math 25.6, code 17.8, knowledge 44.4, task mean 17.9.


# Budget sweep (answered within B tokens; three V4 Flash files and gpt-oss)

| Budget | v4f-q8 math/code/knowledge | v4f-iq3 math/code/knowledge | v4f-q2 math/code/knowledge | gptoss120 math/code/knowledge |
|---|---|---|---|---|
| 2048 | 35.0/45.0/50.0 | 36.7/36.7/48.3 | 28.3/31.7/51.7 | 26.7/38.3/40.0 |
| 3072 | 36.7/46.7/50.0 | 43.3/40.0/48.3 | 31.7/31.7/51.7 | 36.7/45.0/40.0 |
| 4096 | 38.3/46.7/50.0 | 46.7/40.0/48.3 | 36.7/33.3/51.7 | 40.0/48.3/40.0 |
| 5120 | 38.3/46.7/50.0 | 48.3/40.0/48.3 | 38.3/33.3/51.7 | 40.0/48.3/40.0 |

| Budget | Contrast | Math | Code | Knowledge |
|---|---|---|---|---|
| 2048 | v4f-q2 - v4f-q8 | -6.7 [-15.0, +1.7] | -13.3 [-25.0, -3.3] | +1.7 [-11.7, +15.0] |
| 2048 | v4f-iq3 - v4f-q8 | +1.7 [-6.7, +11.7] | -8.3 [-18.3, +1.7] | -1.7 [-13.3, +11.7] |
| 2048 | v4f-q2 - v4f-iq3 | -8.3 [-16.7, -0.0] | -5.0 [-10.0, +0.0] | +3.3 [-10.0, +16.7] |
| 2048 | v4f-q2 - gptoss120 | +1.7 [-10.0, +13.3] | -6.7 [-20.0, +6.7] | +11.7 [-8.3, +33.3] |
| 2048 | v4f-iq3 - gptoss120 | +10.0 [+0.0, +23.3] | -1.7 [-13.3, +10.0] | +8.3 [-6.7, +25.0] |
| 3072 | v4f-q2 - v4f-q8 | -5.0 [-13.3, +3.3] | -15.0 [-28.3, -3.3] | +1.7 [-11.7, +15.0] |
| 3072 | v4f-iq3 - v4f-q8 | +6.7 [-3.3, +18.3] | -6.7 [-15.0, +1.7] | -1.7 [-13.3, +11.7] |
| 3072 | v4f-q2 - v4f-iq3 | -11.7 [-21.7, -1.7] | -8.3 [-16.7, -1.7] | +3.3 [-10.0, +16.7] |
| 3072 | v4f-q2 - gptoss120 | -5.0 [-18.3, +10.0] | -13.3 [-26.7, +0.0] | +11.7 [-8.3, +33.3] |
| 3072 | v4f-iq3 - gptoss120 | +6.7 [-3.3, +16.7] | -5.0 [-18.3, +6.7] | +8.3 [-6.7, +25.0] |
| 4096 | v4f-q2 - v4f-q8 | -1.7 [-11.7, +8.3] | -13.3 [-26.7, -0.0] | +1.7 [-11.7, +15.0] |
| 4096 | v4f-iq3 - v4f-q8 | +8.3 [-3.3, +21.7] | -6.7 [-15.0, +1.7] | -1.7 [-13.3, +11.7] |
| 4096 | v4f-q2 - v4f-iq3 | -10.0 [-20.0, -0.0] | -6.7 [-15.0, +1.7] | +3.3 [-10.0, +16.7] |
| 4096 | v4f-q2 - gptoss120 | -3.3 [-15.0, +10.0] | -15.0 [-30.0, +1.7] | +11.7 [-8.3, +33.3] |
| 4096 | v4f-iq3 - gptoss120 | +6.7 [-3.3, +16.7] | -8.3 [-20.0, +3.3] | +8.3 [-6.7, +25.0] |
| 5120 | v4f-q2 - v4f-q8 | -0.0 [-10.0, +10.0] | -13.3 [-26.7, -0.0] | +1.7 [-11.7, +15.0] |
| 5120 | v4f-iq3 - v4f-q8 | +10.0 [-1.7, +23.3] | -6.7 [-15.0, +1.7] | -1.7 [-13.3, +11.7] |
| 5120 | v4f-q2 - v4f-iq3 | -10.0 [-20.0, -0.0] | -6.7 [-15.0, +1.7] | +3.3 [-10.0, +16.7] |
| 5120 | v4f-q2 - gptoss120 | -1.7 [-15.0, +11.7] | -15.0 [-30.0, +1.7] | +11.7 [-8.3, +33.3] |
| 5120 | v4f-iq3 - gptoss120 | +8.3 [-1.7, +20.0] | -8.3 [-20.0, +3.3] | +8.3 [-6.7, +25.0] |

# Code against Q8 at the 5,120 budget

| Arm | Q8 solved, arm not | of which finished, wrong | of which unfinished | Arm solved, Q8 not | Arm unfinished | Q8 solved where arm unfinished | Both finished: pairs, arm / Q8 solved, paired diff | Items longer than Q8 |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| v4f-q2 | 10 | 6 | 4 | 2 | 24 of 60 | 4 | 35, 20 / 24, -11.9 [-30.9, +4.8] | 16 of 20 |
| v4f-iq3 | 8 | 4 | 4 | 4 | 19 of 60 | 4 | 40, 24 / 24, +0.0 [-5.6, +5.6] | 16 of 20 |
