# AM5: the non-abstention rule's cost when the evidence is absent (tables)

**EXPLORATORY, development split only (the pilot's 63 questions, with their evidence sessions removed). Nothing here licenses a claim; a held-out registration follows only if the development run is clean (D120).**

Counts over the 63 development questions per reader. Ablated: evidence sessions removed. Original: AM3's committed records of the same questions' pools (retrieved arm). Rates with exact 95% Clopper-Pearson intervals. Judge: Qwen3-32B with LongMemEval's non-abstention answer-check prompt. Hand: one blind isolated agent (D9: agent labels).

## Ablated pools: (a) switch rate, (b) top 4 answers, (c) whole pool abstains

| Reader | K | (a) switch rate | (b) BM25 top 4 does not abstain | (c) all 8 abstains | every 4-subset abstains | rule keeps an abstention | mean reads |
|---|---:|---|---|---|---|---|---:|
| qwen3-8b | 8 | 1/63 (0.016 [0.000, 0.085]) | 1/63 (0.016 [0.000, 0.085]) | 61/63 (0.968 [0.890, 0.996]) | 60/63 (0.952 [0.867, 0.990]) | 61/63 (0.968 [0.890, 0.996]) | 7.84 |
| qwen3-8b | 70 | 2/63 (0.032 [0.004, 0.110]) | 1/63 (0.016 [0.000, 0.085]) | 61/63 (0.968 [0.890, 0.996]) | 60/63 (0.952 [0.867, 0.990]) | 60/63 (0.952 [0.867, 0.990]) | 67.76 |
| olmo-2-1124-7b-instruct | 8 | 6/63 (0.095 [0.036, 0.196]) | 4/63 (0.063 [0.018, 0.155]) | 56/63 (0.889 [0.784, 0.954]) | 49/63 (0.778 [0.655, 0.873]) | 53/63 (0.841 [0.727, 0.921]) | 7.06 |
| olmo-2-1124-7b-instruct | 70 | 10/63 (0.159 [0.079, 0.273]) | 4/63 (0.063 [0.018, 0.155]) | 56/63 (0.889 [0.784, 0.954]) | 49/63 (0.778 [0.655, 0.873]) | 49/63 (0.778 [0.655, 0.873]) | 56.51 |
| qwen3.5-9b | 8 | 3/63 (0.048 [0.010, 0.133]) | 0/63 (0.000 [0.000, 0.057]) | 61/63 (0.968 [0.890, 0.996]) | 60/63 (0.952 [0.867, 0.990]) | 60/63 (0.952 [0.867, 0.990]) | 7.84 |
| qwen3.5-9b | 70 | 3/63 (0.048 [0.010, 0.133]) | 0/63 (0.000 [0.000, 0.057]) | 61/63 (0.968 [0.890, 0.996]) | 60/63 (0.952 [0.867, 0.990]) | 60/63 (0.952 [0.867, 0.990]) | 66.89 |

## Ablated pools: (d) answers correct by chance

Switched: the rule's reply where BM25 top 4 abstains and a 4-subset answers within K reads. Top-4 answers: BM25 top 4's reply where it does not abstain. Judged: Qwen3-32B yes. Hand: the blind agent's 1. Cost: switched replies not correct (judge; hand).

| Reader | K | switched | judged correct | hand correct (labelled) | judge yes, hand no | judge no, hand yes | cost, judge | cost, hand |
|---|---:|---:|---:|---|---:|---:|---|---|
| qwen3-8b | 8 | 1 | 1 | 1 (1 of 1) | 0 | 0 | 0/63 (0.000 [0.000, 0.057]) | 0/63 (0.000 [0.000, 0.057]) |
| qwen3-8b | 70 | 2 | 1 | 1 (2 of 2) | 0 | 0 | 1/63 (0.016 [0.000, 0.085]) | 1/63 (0.016 [0.000, 0.085]) |
| olmo-2-1124-7b-instruct | 8 | 6 | 1 | 1 (6 of 6) | 0 | 0 | 5/63 (0.079 [0.026, 0.176]) | 5/63 (0.079 [0.026, 0.176]) |
| olmo-2-1124-7b-instruct | 70 | 10 | 1 | 1 (10 of 10) | 0 | 0 | 9/63 (0.143 [0.067, 0.254]) | 9/63 (0.143 [0.067, 0.254]) |
| qwen3.5-9b | 8 | 3 | 0 | 0 (3 of 3) | 0 | 0 | 3/63 (0.048 [0.010, 0.133]) | 3/63 (0.048 [0.010, 0.133]) |
| qwen3.5-9b | 70 | 3 | 0 | 0 (3 of 3) | 0 | 0 | 3/63 (0.048 [0.010, 0.133]) | 3/63 (0.048 [0.010, 0.133]) |

| Reader | top-4 answers | judged correct | hand correct (labelled) | all-8 answers | all-8 answers judged correct |
|---|---:|---:|---|---:|---:|
| qwen3-8b | 1 | 0 | 0 (1 of 1) | 2 | 1 |
| olmo-2-1124-7b-instruct | 4 | 1 | 1 (4 of 4) | 7 | 1 |
| qwen3.5-9b | 0 | 0 | 0 (0 of 0) | 2 | 0 |

## The same questions' original pools (AM3's committed records, retrieved arm)

| Reader | K | switch rate | BM25 top 4 does not abstain | all 8 abstains | every 4-subset abstains | gained b | lost c | gain per question | BM25 top 4 correct | rule correct |
|---|---:|---|---|---|---|---:|---:|---:|---|---|
| qwen3-8b | 8 | 7/63 (0.111 [0.046, 0.216]) | 46/63 (0.730 [0.603, 0.834]) | 17/63 (0.270 [0.166, 0.397]) | 10/63 (0.159 [0.079, 0.273]) | 1 | 0 | +0.016 | 32/63 (0.508 [0.379, 0.636]) | 33/63 (0.524 [0.394, 0.651]) |
| qwen3-8b | 70 | 7/63 (0.111 [0.046, 0.216]) | 46/63 (0.730 [0.603, 0.834]) | 17/63 (0.270 [0.166, 0.397]) | 10/63 (0.159 [0.079, 0.273]) | 1 | 0 | +0.016 | 32/63 (0.508 [0.379, 0.636]) | 33/63 (0.524 [0.394, 0.651]) |
| olmo-2-1124-7b-instruct | 8 | 13/63 (0.206 [0.115, 0.327]) | 43/63 (0.683 [0.553, 0.794]) | 21/63 (0.333 [0.220, 0.463]) | 5/63 (0.079 [0.026, 0.176]) | 4 | 0 | +0.063 | 26/63 (0.413 [0.290, 0.544]) | 30/63 (0.476 [0.349, 0.606]) |
| olmo-2-1124-7b-instruct | 70 | 15/63 (0.238 [0.140, 0.362]) | 43/63 (0.683 [0.553, 0.794]) | 21/63 (0.333 [0.220, 0.463]) | 5/63 (0.079 [0.026, 0.176]) | 4 | 0 | +0.063 | 26/63 (0.413 [0.290, 0.544]) | 30/63 (0.476 [0.349, 0.606]) |
| qwen3.5-9b | 8 | 7/63 (0.111 [0.046, 0.216]) | 44/63 (0.698 [0.570, 0.808]) | 17/63 (0.270 [0.166, 0.397]) | 11/63 (0.175 [0.091, 0.291]) | 3 | 0 | +0.048 | 29/63 (0.460 [0.334, 0.591]) | 32/63 (0.508 [0.379, 0.636]) |
| qwen3.5-9b | 70 | 8/63 (0.127 [0.056, 0.235]) | 44/63 (0.698 [0.570, 0.808]) | 17/63 (0.270 [0.166, 0.397]) | 11/63 (0.175 [0.091, 0.291]) | 3 | 0 | +0.048 | 29/63 (0.460 [0.334, 0.591]) | 32/63 (0.508 [0.379, 0.636]) |

## Side by side (descriptive)

Gain per question on the original pools against the cost per question on the ablated pools of the same 63 questions; the break-even share is am3g's g/(g + l), the share of evidence-absent questions above which BM25 top 4 is ahead, if deployment's unanswerable questions looked like these.

| Reader | K | gain, original | cost, ablated (judge) | cost, ablated (hand) | break-even (judge) | break-even (hand) | switched on both |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3-8b | 8 | +0.016 | 0.000 | 0.000 | 1.00 | 1.00 | 1 |
| qwen3-8b | 70 | +0.016 | 0.016 | 0.016 | 0.50 | 0.50 | 1 |
| olmo-2-1124-7b-instruct | 8 | +0.063 | 0.079 | 0.079 | 0.44 | 0.44 | 0 |
| olmo-2-1124-7b-instruct | 70 | +0.063 | 0.143 | 0.143 | 0.31 | 0.31 | 1 |
| qwen3.5-9b | 8 | +0.048 | 0.048 | 0.048 | 0.50 | 0.50 | 0 |
| qwen3.5-9b | 70 | +0.048 | 0.048 | 0.048 | 0.50 | 0.50 | 0 |

## (e) Leakage

| Check | Count |
|---|---:|
| evidence session ids | 124 |
| has answer memories in the ablated pools | 0 |
| has answer turns before | 126 |
| has answer turns in evidence sessions | 126 |
| has answer turns left in the haystack | 0 |
| memories | 504 |
| memories shared with the original pools | 263 |
| original pools with a has answer memory | 58 |
| pool memories equal to an evidence turn | 0 |
| pools with a has answer memory | 0 |
| pools with a memory containing the answer | 4 |
| pools with a memory equal to an evidence turn | 0 |
| questions | 63 |
| questions whose remaining user turns contain the answer | 10 |
| questions with a repeated evidence session id | 0 |
| questions with has answer turns left | 0 |
| sessions removed | 124 |

| Type | questions | pools with a has_answer memory | pools with a memory containing the answer | questions whose remaining user turns contain the answer |
|---|---:|---:|---:|---:|
| knowledge-update | 11 | 0 | 2 | 3 |
| multi-session | 18 | 0 | 2 | 7 |
| single-session-assistant | 1 | 0 | 0 | 0 |
| single-session-preference | 5 | 0 | 0 | 0 |
| single-session-user | 9 | 0 | 0 | 0 |
| temporal-reasoning | 19 | 0 | 0 | 0 |

## Judge validation (AM1's items on these 63 questions)

| Item | items | judged yes |
|---|---:|---:|
| validation:idk | 63 | 0 |
| validation:other-answer | 62 | 4 |
| validation:reference | 58 | 58 |

## Hand check

Status: complete; 18 of 18 items labelled, 3 labelled correct; plan `171707ec40cb99d7...`. Hand against judge: 18 of 18 agree (judge yes, hand no 0; judge no, hand yes 0; kappa 1.00).

Replies judged or hand-labelled correct, with their question's leakage facts (answer in a pool memory; answer in a remaining user turn; answer tokens; memories shared with the original pool; has_answer memories in the original pool):

| Item | question | type | uses | judge | hand | answer in pool | answer in remaining turns | answer tokens | shared memories | original has_answer |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| a0000 | gpt4_b0863698 | temporal-reasoning | olmo-2-1124-7b-instruct top4-answers | 1 | 1 | 0 | 0 | 11 | 7 | 1 |
| a0013 | a06e4cfe | single-session-user | olmo-2-1124-7b-instruct switched | 1 | 1 | 0 | 0 | 2 | 6 | 1 |
| a0015 | b6025781 | single-session-preference | qwen3-8b switched | 1 | 1 | 0 | 0 | 72 | 5 | 1 |

