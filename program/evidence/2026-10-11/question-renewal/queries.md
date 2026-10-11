# Retrieval queries for the 2026-10-11 question renewal

Every query the five discovery cells reported, as they reported it, followed
by the slate owner's verification queries. All `orx` calls used orx 0.2.2,
which reports itself outdated against 0.2.18. Cell scratch logs (raw JSON
results) stayed in the session scratchpad and are not committed.

## Cell 1: checker and benchmark calibration

1. orx discover embedding: mutation testing of benchmark evaluators for computer-use agents false negatives (--limit 12)
2. orx discover embedding: false negatives in OSWorld evaluators audit of computer-use benchmark verdicts (--limit 12)
3. orx discover embedding: does mutation-based checker error rate predict on-policy verdict errors of real agent outputs (--limit 12)
4. orx discover keyword: How Benchmarks Mis-Score Computer-Use Agents (--limit 8)
5. orx discover embedding: rerun noise and session variance in computer-use agent benchmark evaluation OSWorld seeds (--limit 12)
6. orx discover embedding: nondeterminism in greedy decoding LLM inference batch invariance reproducibility (--limit 12)
7. orx discover keyword: screenshot clock nondeterminism computer-use agent rerun (--limit 10)
8. orx discover embedding: GUI agent sensitivity to irrelevant screenshot perturbations robustness benchmark (--limit 12)
9. orx discover keyword: RealGUINoise (--limit 5)
10. orx discover embedding: temperature zero agent benchmark run-to-run variance caused by environment timestamps and nondeterministic observations (--limit 12)
11. orx discover keyword: Agent Evaluation Reliability variance decomposition (--limit 6)
12. orx discover embedding: GPU kernel speedup measurement noise timing methodology false speedups KernelBench (--limit 12)
13. orx discover keyword: A/A test kernel timing variance H100 speedup claims (--limit 8)
14. orx discover openalex: Are mutants a valid substitute for real faults in software testing
15. orx paper --full 2610.09142
16. orx discover embedding: statistical separability of agent leaderboard ranks confidence intervals OSWorld leaderboard (--limit 10)
17. orx discover embedding: butterfly effect small input perturbation changes multi-step LLM agent trajectory outcome under greedy decoding (--limit 12)
18. orx discover keyword: deterministic replay computer-use agent frozen clock virtual machine evaluation (--limit 8)
19. orx discover embedding: software version drift breaks agent benchmark evaluators reference solution fails after application upgrade (--limit 10)
20. orx discover embedding: metamorphic testing of evaluation scripts semantically null transformations reference output checker invariance (--limit 10)
21. orx paper --full 2609.22220
22. orx paper --full 2608.12700
23. orx paper --full 2607.16241
24. orx discover embedding: condition-aware componentwise error bound tolerance for verifying GPU kernel correctness under reduced precision TF32 bf16 (--limit 12)
25. orx discover keyword: componentwise backward error tolerance kernel correctness LLM-generated (--limit 8)
26. orx discover embedding: computer-use agents unintended side effects collateral file changes not detected by task evaluators OSWorld (--limit 12)
27. orx discover keyword: OS-Harm computer use agent safety benchmark side effects (--limit 6)
28. orx paper --full 2606.29537
29. orx discover keyword: system clock date shown on screen GUI agent evaluation variance (--limit 8)
30. orx discover embedding: variance decomposition of repeated runs for multimodal desktop agents environment nondeterminism versus model sampling (--limit 10, published after 2026-05-01)
31. orx discover keyword: OSWorld-Verified leaderboard confidence interval single run significance (--limit 10)
32. orx discover embedding: same agent evaluated twice by benchmark maintainers gives different score session effect desktop benchmark (--limit 8)
33. orx paper --full 2607.28367
34. orx paper 2604.06240
35. orx paper 2608.06171
36. orx paper 2610.04433
37. orx paper 2508.13144
38. orx paper 2411.00640
39. orx paper 2408.04667
40. orx discover openalex: Metamorphic Testing: A Review of Challenges and Opportunities
41. OpenReview api2 notes/search: computer use evaluator false negatives
42. OpenReview api2 notes/search: benchmark noise floor agents
43. OpenReview api2 notes/search: checker mutation verifier audit
44. OpenReview api2 notes/search: OSWorld evaluator
45. OpenReview api2 notes/search: rerun variance computer-use agents
46. OpenReview api2 notes/search: nondeterminism agent evaluation reproducibility
47. OpenReview api2 notes/search: verifier errors reinforcement learning audit
48. OpenReview api2 notes?id= cELldjX2oq, UJAisq0CKV, uEXElUZri9, ZH0bV3kwTo (all refused: challenge verification required; not bypassed)
49. OpenReview api2 notes/search: The Evaluator Also Varies
50. OpenReview api2 notes/search: Verifier Errors in RLVR Reward Hacking Limits of Feedback
51. OpenReview api2 notes/search: Which verifier errors reach the gradient
52. Web search (aclanthology.org): benchmark evaluation variance seeds noise "signal and noise" language model evaluation
53. Web search (aclanthology.org): agent benchmark evaluator errors false negatives web agent judge reliability

## Cell 2: computer-use instrument follow-ons

1. orx discover keyword 'rerun variance computer-use agent OSWorld nondeterminism' --published-after 2025-06-01 (k1; first attempt failed on a missing timeout binary, re-run)
2. orx discover embedding 'sources of run-to-run nondeterminism in GUI computer-use agent evaluation under greedy decoding: environment clock pixels versus inference batch nondeterminism' (e1)
3. orx discover keyword 'batch invariant inference deterministic LLM agent evaluation reproducibility' --published-after 2025-06-01 (k2)
4. orx discover embedding 'replay recorded action sequences open-loop in desktop virtual machine to measure environment nondeterminism of agent benchmark' (e2)
5. orx discover keyword 'OSWorld evaluator false positive false negative checker audit' --published-after 2025-06-01 (k3)
6. orx discover embedding 'audit of rule-based state checkers verdicts on real computer-use agent trajectories false accept false reject' (e3)
7. orx discover keyword 'accessibility tree screenshot observation ablation OSWorld' --published-after 2025-01-01 (k4)
8. orx discover embedding 'effect of adding accessibility tree to screenshot observation on open-weight computer-use agent success across model sizes on desktop tasks' (e4)
9. orx discover keyword 'mutation testing evaluation function GUI agent benchmark checker' --published-after 2025-01-01 (k5)
10. orx discover embedding 'rerun noise of agent benchmark shrinks with model scale; run-to-run variance as a function of model size' (e5)
11. orx discover keyword 'item response theory efficient evaluation agent benchmark task subset computer use' --published-after 2025-01-01 (k6)
12. orx discover embedding 'semantically null visual perturbations such as clock time wallpaper or theme change GUI agent success robustness' (e6)
13. orx discover keyword 'pass^k reliability repeated trials computer-use agents consistency' --published-after 2025-06-01 (k7)
14. orx discover embedding 'repair of benchmark task verifiers validated by mutation analysis and rescoring of leaderboard agents' (e7)
15. orx discover keyword 'noise floor agent benchmark rerun' --published-after 2026-06-01 (k8)
16. orx discover keyword 'frozen clock deterministic screenshot GUI agent evaluation' --published-after 2025-01-01 (k9)
17. orx discover embedding 'computer-use agent harness sensitivity versus model scale on OSWorld with open-weight vision-language models of several sizes' --published-after 2026-01-01 (e8)
18. orx discover openalex 'OSWorld computer use agent evaluation reliability' (o1)
19. orx discover openalex 'agent benchmark run-to-run variance reproducibility' (o2)
20. orx discover embedding 'how much of an agent benchmark's rerun disagreement is due to the task checker rather than agent behaviour' --published-after 2026-01-01 (e9)
21. orx discover keyword 'OSWorld-Verified evaluation scripts bugs task verifier fixes' --published-after 2025-06-01 (k10)
22. orx discover embedding 'nondeterministic vLLM serving batch composition changes greedy outputs of multimodal agents across reruns' --published-after 2025-06-01 (e10)
23. orx discover keyword 'larger models more consistent repeated runs agent variance model size' --published-after 2026-01-01 (k11)
24. orx discover embedding 'does outcome consistency across identical reruns of an agent improve with model scale within one model family' --published-after 2025-06-01 (e11)
25. orx discover keyword 'Qwen3.5 OSWorld screenshot accessibility tree' --published-after 2026-02-01 (k12)
26. orx discover keyword 'on-policy audit PASS verdicts computer-use benchmark false positive desktop' --published-after 2026-01-01 (k13)
27. orx discover embedding 'certified action delivery layer for computer-use benchmark key events dropped modifiers harness bugs' --published-after 2026-01-01 (e12)
28. orx discover keyword 'LibreOffice Impress pptx comparison checker shape order OSWorld' --published-after 2025-01-01 (k14)
29. orx discover embedding 'benchmark version drift: evaluator code changes between benchmark revisions alter verdicts and break comparability with published agent results' --published-after 2025-06-01 (e13)
30. orx discover keyword 'checker repair overfitting held-out mutants verifier patch generalization' --published-after 2025-06-01 (k15)
31. orx discover embedding 'first divergence between repeated agent trajectories caused by on-screen clock or timestamp in screenshot observation' (e14)
32. orx discover keyword 'Pass^k model size scaling reliability GUI agent open-weight' --published-after 2026-01-01 (k16)
33. orx discover openalex 'computer use agent accessibility tree observation' (o3)
34. orx discover openalex 'mutation analysis test oracle adequacy benchmark verifier' (o4)
35. orx discover embedding 'replaying the same action sequence in a reset virtual machine reproduces the final state and verdict, separating environment nondeterminism from policy nondeterminism' --published-after 2025-01-01 (e15)
36. orx discover keyword 'rescoring archived trajectories under revised evaluator benchmark revision verdict changes' --published-after 2025-06-01 (k17)
37. orx discover embedding 'external anchoring a self-hosted agent benchmark run against public leaderboard trajectories, reproducing per-task outcomes' --published-after 2025-06-01 (e16)
38. orx discover keyword 'OSWorld-Verified reproducibility leaderboard self-hosted reproduce reported score' --published-after 2025-06-01 (k18)
39. orx paper --full: 2608.22331, 2609.33812, 2604.17849, 2610.09142, 2609.34262, 2610.11678, 2607.04334, 2606.29472, 2609.24890, 2609.26621, 2603.10577, 2610.11050, 2607.22798, 2608.06171, 2404.07972, 2608.03327, 2602.07150, 2609.36931, 2610.00651, 2607.28367, 2610.01138, 2609.34198, 2608.11694, 2609.40284
40. orx paper (report only): 2609.34469, 2609.37322, 2605.00551
41. OpenReview api2 notes/search term='computer-use agent rerun variance'
42. OpenReview api2 notes/search term='OSWorld evaluator reliability' (found ezVIHPgaiG, the ARR version of 2604.17849; fVkcp4NMcq)
43. OpenReview api2 notes/search term='accessibility tree screenshot computer use agent'
44. OpenReview api2 notes/search term='nondeterminism agent evaluation batch invariant' (found rGmv0X20Oj, FlexBI)
45. ACL Anthology proxy (OpenAlex works search, landing_page_url filter aclanthology.org, from 2025-01-01): 'GUI agent evaluation reliability', 'agent benchmark rerun variance', 'accessibility tree screenshot agent', 'evaluation nondeterminism greedy decoding' (all returned 0; filter unsupported)
46. ACL-family venues via OpenAlex source-id filter (ACL, NAACL, TACL, EACL, Findings NAACL, Findings EACL; from 2025-01-01): 'GUI agent evaluation', 'agent evaluation variance reruns', 'computer use agent benchmark', 'nondeterminism LLM evaluation'
47. Hugging Face API file listing (metadata only, no data download): datasets/xlangai/ubuntu_osworld_verified_trajs tree/main, plus its README.md

## Cell 3: kernel and code correctness after Q1

1. orx discover keyword 'Calibrating the Checksum' --limit 8
2. orx discover embedding 'tolerance-based correctness checks for GPU kernels cannot distinguish reduced precision TF32 from wrong outputs' --limit 12
3. orx discover embedding 'LLM-generated GPU kernels cheat speedup by downcasting to half precision bf16 fp16 passing tolerance check' --limit 15
4. orx discover keyword 'precision downcast reward hacking kernel speedup tolerance' --limit 12
5. orx discover embedding 'integer-valued test inputs make floating point matrix multiplication exact so any summation order gives identical results, enabling zero-tolerance testing of kernels' --limit 15
6. orx discover keyword 'exactly representable inputs zero tolerance kernel testing summation order' --limit 12
7. orx discover embedding 'black-box probing of matrix multiply units with crafted inputs to reveal rounding mode, operand precision and accumulation order (tensor core numerical behavior)' --limit 15
8. orx discover keyword 'FPRev summation order revealing' --limit 8
9. orx discover embedding 'detecting silent precision reduction in optimized kernels: verifying operand and accumulator formats of a candidate implementation against a numerical contract' --limit 15
10. orx discover keyword 'Correctness Illusion kernel' --limit 8
11. orx discover keyword 'integer inputs exact floating point differential testing deep learning operators' --limit 12
12. orx discover embedding 'test oracle for numerical kernels using inputs on which every valid floating-point evaluation is exact, eliminating tolerance' --limit 12 --published-after 2023-01-01
13. orx discover keyword 'TRITON_INTERPRET interpreter mode CPU kernel correctness' --limit 12
14. orx discover embedding 'verifying LLM-generated Triton or CUDA kernels without a GPU by executing them on CPU emulation or interpreter for reward computation' --limit 15
15. orx discover keyword 'TF32 tolerance allclose correct kernel rejected benchmark' --limit 12
16. orx discover embedding 'benchmark reference computed in TF32 violates its own correctness tolerance against float64; unrefereeable problems in kernel benchmarks' --limit 12
17. orx discover embedding 'speedup obtained by lowering numerical precision in generated kernels inflates benchmark results; precision-matched speedup accounting' --limit 15
18. orx discover keyword 'AI CUDA Engineer archive precision half speedup analysis' --limit 10
19. orx discover keyword 'KernelArena reward hacks catalog' --limit 8
20. orx discover embedding 'catalog of reward hacks by LLMs in GPU kernel benchmarks: timing attacks, precision downgrade, caching outputs, shape specialization' --limit 12
21. OpenReview api2 notes/search 'kernel correctness tolerance precision' limit 15
22. OpenReview api2 notes/search 'GPU kernel verification reward hacking' limit 15
23. OpenReview api2 rerun of the same two terms through a script (forum-title fetch blocked by ChallengeRequiredError; duplicates)
24. OpenReview api2 notes/search 'Triton kernel correctness verification' limit 25
25. OpenReview api2 notes/search 'kernel benchmark correctness tolerance' limit 25
26. OpenReview api2 notes/search 'TF32 precision correctness kernel' limit 25
27. OpenReview api2 notes/search 'mutation analysis GPU kernel oracle precision' limit 20
28. OpenReview api2 notes/search 'Triton interpreter CPU' limit 20
29. ACL Anthology (regex over the full abstracts BibTeX export, fetched 2026-10-11): 'gpu kernel' AND (correct|verif|test)
30. ACL Anthology regex: (cuda|triton) AND kernel AND (generat|llm|language model)
31. ACL Anthology regex: (floating-point|numerical) (toleran|precision) AND (test|benchmark|evaluat) AND (code|program)
32. ACL Anthology regex: (reward hack|test adequacy) AND code
33. ACL Anthology regex: scicode|numerical code generation AND (toleran|allclose|verif)
34. orx discover embedding 'static analysis of compiled PTX or SASS to determine which floating-point formats a GPU kernel computes in, e.g. detecting half-precision tensor core instructions' --limit 12
35. orx discover embedding 'minimum detectable fault magnitude of a tolerance-based numerical test oracle given legitimate floating-point variance of valid implementations' --limit 12
36. orx discover embedding 'reinforcement learning for kernel generation comparing verifier strength: weak allclose check versus strong hidden-shape verifier, effect on held-out correctness' --limit 15 --published-after 2026-08-01
37. orx discover keyword 'verifier strength kernel RL false accept on-policy' --limit 10 --published-after 2026-08-15
38. orx discover embedding 'numerical accuracy of Winograd and FFT convolution algorithms in reduced precision versus direct convolution, cuDNN algorithm selection error' --limit 10
39. orx discover embedding 'Triton interpreter fidelity: differences between CPU interpreted execution and GPU execution of Triton kernels' --limit 8
40. orx discover keyword 'AutoTriton automatic Triton programming reinforcement learning' --limit 5
41. orx discover keyword 'robust-kbench' --limit 3
42. orx discover embedding 'RL policies exploit floating-point tolerance in numerical code verifiers: outputs within allclose but wrong; reward hacking via tolerance' --limit 12 --published-after 2026-01-01
43. orx discover keyword 'Kuiper approximation relation floating point real numbers kernel verification' --limit 6
44. orx discover keyword 'dyadic integer test vectors exact GEMM verification order independent' --limit 8
45. orx discover embedding 'precision-aware correctness criteria for kernel benchmarks: declared numeric contract (TF32, BF16) instead of a single allclose tolerance' --limit 10 --published-after 2026-05-01
46. orx paper --full: 2607.16241, 2609.22220, 2608.12700, 2610.05683, 2609.19611
47. Hugging Face API metadata reads: hkust-nlp/drkernel-coldstart-8k, SakanaAI/AI-CUDA-Engineer-Archive, GPUMODE/KernelBook, ScalingIntelligence/kernelbench-samples; model searches for KernelLLM, AutoTriton, drkernel-8b, Kevin-32B
48. Data reads into the scratchpad only: Sakana level_1 and level_2 parquets, drkernel-coldstart-8k parquet (SHA-256 prefix 4ed72a9f)

## Cell 4: multilingual and long-context mechanisms

1. orx discover keyword: multilingual NoLiMa literal overlap needle haystack cross-lingual (limit 15)
2. orx discover embedding: Is the cross-lingual long-context retrieval gap explained by loss of lexical overlap between question and needle? (limit 15)
3. orx discover keyword: cross-lingual needle in a haystack lexical overlap paraphrase same-language control (limit 15)
4. orx discover keyword: multilingual long-context benchmark needle language mismatch query document language (after 2025-01-01)
5. orx discover keyword: OneRULER multilingual long context
6. orx paper --full 2503.01996
7. orx discover keyword: multilingual evaluation answer extraction exact match false negatives native numerals script normalization benchmark scoring
8. orx discover embedding: Scoring functions in multilingual benchmarks reject correct answers written in native digits or scripts, inflating the cross-language gap
9. orx discover keyword: MLNeedle multilingual needle haystack
10. orx discover embedding: non-literal needle in a haystack across languages: latent association retrieval when question and needle are in different languages (after 2025-01-01)
11. orx discover keyword: NoLiMa translated languages (after 2025-03-01)
12. orx discover keyword: literal match multilingual long-context retrieval attention lexical overlap cross-lingual question (after 2025-06-01)
13. orx discover keyword: tokenizer fertility effective context length long-context degradation token distance versus content distance languages (after 2025-01-01)
14. orx discover keyword: Serbian Cyrillic Latin script digraphia language model tokenization evaluation
15. orx discover keyword: KV cache compression multilingual languages disparity long context eviction non-English (after 2025-01-01)
16. orx discover embedding: Does KV cache eviction or compression hurt non-English or cross-lingual long-context retrieval more than English?
17. orx discover keyword: computer-use agent instruction language translated instructions OSWorld multilingual GUI agent grounding (after 2025-06-01)
18. orx discover embedding: GUI agents fail when the task instruction is in a different language from the interface labels; cross-lingual grounding of UI elements
19. orx paper --full 2609.23490
20. orx discover keyword: OSWorld evaluator checker robustness locale date number format false negative evaluation function (after 2025-01-01)
21. orx discover embedding: Benchmark evaluation scripts for desktop agents break under non-English system locales (decimal comma, date formats, localized file names)
22. orx discover keyword: self-translate query into context language long-context cross-lingual question answering prompting translate-test (after 2024-06-01)
23. orx discover embedding: Translating the question into the document's language before answering improves cross-lingual long-document QA because it restores lexical matches
24. orx discover embedding: Long-context accuracy in high-fertility languages: does degradation follow the number of tokens or the amount of content? parallel haystacks across languages
25. orx paper 2606.06203 (report)
26. orx paper --full 2608.27481
27. orx paper --full 2506.04135
28. orx paper --full 2607.28367
29. orx discover keyword: same language different script retrieval transliteration question passage Cyrillic Latin LLM in-context retrieval (after 2024-06-01)
30. orx discover keyword: Wikidata multilingual labels synthetic needle long-context benchmark entity association (after 2024-06-01)
31. OpenReview api2 notes/search: cross-lingual needle haystack literal
32. OpenReview api2 notes/search: multilingual long-context retrieval lexical overlap
33. OpenReview api2 notes/search: tokenizer fertility long context degradation
34. OpenReview api2 notes?id= sOXznQZgnM, nDHs6Q4a9b, Fd0zAJPFeH, KuE4q8O0rz (all returned the 403 challenge; abstracts taken from search results)
35. orx discover openalex: cross-lingual long-context retrieval lexical overlap needle (OpenAlex as the ACL Anthology proxy; found 2026.eacl-long.290)
36. orx discover keyword: self-translate multilingual language models think better in English
37. orx paper 2308.01223, 2602.22453, 2409.18006, 2504.12845 (reports, to verify ids)
38. orx discover keyword: spreadsheet agent locale decimal separator date format localization robustness benchmark evaluation (after 2025-01-01)
39. orx discover embedding: Does the same RoPE position-based degradation explain why long-context retrieval is worse in languages whose tokenizer produces more tokens?

## Cell 5: kill-shot and occupancy

orx discover queries (date filter in brackets):

1. keyword [2026-01-01] (initial test run): mutation testing computer-use agent benchmark evaluator
2. keyword [2026-01-01]: OSWorld evaluator false negative checker audit
3. keyword [2026-01-01]: mutation testing computer-use agent benchmark evaluator
4. embedding [2026-01-01]: benchmark task validity outcome validity agentic benchmark checklist evaluator bugs
5. embedding [2026-01-01]: auditing the correctness of programmatic evaluators in desktop computer-use agent benchmarks
6. embedding [2026-01-01]: mis-scored verdicts in computer use benchmarks state checker
7. keyword [2026-01-01]: mutation analysis benchmark oracle agent tasks false positive false negative
8. keyword [2026-06-01]: OSWorld-Verified evaluation script errors
9. keyword [2026-01-01]: reward hacking computer-use agent reinforcement learning checker exploit
10. embedding [2026-01-01]: how many tasks and reruns are needed to detect a difference between agents statistical power
11. embedding [2026-01-01]: variance decomposition of agent benchmark scores generalizability theory tasks seeds scaffolds
12. embedding [2026-01-01]: harness choice versus run-to-run noise in computer-use agent evaluation
13. keyword [2026-01-01]: nondeterminism greedy decoding vLLM agent evaluation reproducibility batch invariance
14. keyword [2026-01-01]: minimum detectable effect agent benchmark paired comparison tasks reruns
15. keyword [2026-01-01]: harness sensitivity model scale small models computer use scaffold
16. embedding [2026-01-01]: serving session effect inference engine version changes agent benchmark results
17. keyword [2026-01-01]: rerun variance computer-use agents seeds OSWorld noise
18. keyword [2026-08-01]: Triton kernel RL verifier strength ablation
19. embedding [2026-01-01]: precision-aware correctness oracle for GPU kernels under TF32 reduced precision
20. embedding [2026-01-01]: relative error tolerance metric accepts all-zeros output numerical correctness check
21. embedding [2026-08-01]: gate strength as a variable in kernel RL matched compute stronger verifier yields better kernels
22. keyword [2026-06-01]: kernel generation reinforcement learning correctness verifier reward hacking hidden shapes
23. keyword [2026-01-01]: KernelBench correctness check tolerance TF32 false accept
24. keyword [2026-07-01]: LLM generated CUDA kernels correctness audit independent oracle
25. embedding [2026-06-01]: on-policy false accept rate of GPU kernel correctness checkers during RL training
26. embedding [2026-06-01]: AI research agent preregistration adversarial review gauntlet proposals refuted negative results
27. keyword [2026-06-01]: LLM-as-judge computer-use trajectories agreement human audit OSWorld
28. keyword [2026-01-01]: nested KVM virtual machines concurrency computer-use agent evaluation infrastructure failure rate
29. embedding [2026-06-01]: auditing autonomous research agents honest exits stopping rules preregistered
30. embedding [2026-01-01]: LLM judges disagree on whether two office documents are equivalent rater agreement kappa
31. keyword [2026-06-01]: automated scientist research ideas fail feasibility decisiveness review
32. keyword [2026-01-01]: action execution errors computer-use harness keyboard modifier xdotool pyautogui
33. embedding [2026-01-01]: certifying the action path of a computer-use agent harness infrastructure failures separate from model failures
34. embedding [2026-06-01]: sparse attention top-k indexer multilingual cross-lingual retrieval recall loss
35. embedding [2026-06-01]: multilingual localized interface computer-use agents performance drop non-English UI
36. keyword [2026-01-01]: batch invariant deterministic inference agent benchmark reruns outcome flips
37. embedding [2026-01-01]: deterministic serving eliminates rerun variance in agent evaluation
38. keyword [2026-01-01]: Arabic right-to-left GUI agent interface mirrored layout
39. embedding [2026-01-01]: sources of run-to-run nondeterminism in computer-use agents environment timing versus model inference
40. keyword [2026-01-01]: GUI agent trajectory divergence identical screenshots replay determinism
41. keyword [2026-06-01]: DeepSeek sparse attention lightning indexer multilingual long context
42. keyword [2026-06-01]: Winograd TF32 numerical error tolerance correct algorithm rejected
43. keyword [2026-01-01]: screenshot clock dynamic content nondeterminism desktop agent evaluation frozen time
44. embedding [2026-01-01]: GUI agents sensitivity to small pixel perturbations irrelevant screen changes flips actions
45. embedding [2026-06-01]: tolerance-based numerical verification cannot distinguish small faults from legitimate reduced-precision algorithm differences
46. embedding [2026-01-01]: verifier error measured by injected mutants versus error rate on policy-generated outputs gap
47. keyword [2026-06-01]: compare_pptx_files OSWorld
48. keyword [2026-01-01]: realism probe LLM-written kernels incorrect checker mutation on-policy
49. embedding [2026-01-01]: re-saving gold solution through application changes file and flips evaluator verdict round trip
50. embedding [2026-01-01]: noise-relative error normalization yardstick of correct reference implementations kernel verification three-valued verdict
51. embedding [2026-01-01]: RL training computer-use agent with corrected evaluator rewards checker noise effect on learned policy
52. embedding [2026-06-01]: cross-lingual long-context retrieval question in different language than passage attention recall
53. keyword [2026-01-01]: multilingual OSWorld localized interface language LibreOffice agent
54. keyword [2026-01-01]: TF32 cuDNN algorithm selection correctness threshold kernel benchmark reference nondeterministic
55. keyword [2026-01-01]: token fertility long-context retrieval multilingual needle in a haystack cross-lingual
56. embedding [2026-08-01]: certified harness action execution failure rate bound computer-use benchmark infrastructure validity
57. keyword [2026-06-01]: verifier false negatives RLVR equivalent answers rejected reward noise computer use
58. keyword [2026-01-01]: computer-use agent evaluation repeated runs pass^k consistency OSWorld
59. embedding [2026-01-01]: making desktop computer-use benchmark runs bit-reproducible VM snapshot deterministic screenshots and batch-invariant inference
60. keyword [2026-01-01]: first divergence replicated trajectories agent environment serving prefix caching
61. embedding [2026-06-01]: on-policy audit of PASS verdicts desktop agent benchmark false accepts final file state
62. embedding [2026-01-01]: effect of harness implementation bugs on computer-use agent task success dropped tool calls modifier keys
63. embedding [2026-01-01]: how much of a reported harness effect is due to execution defects rather than scaffold design
64. keyword [2026-01-01]: harness bug fix changes agent benchmark score parsing multiple tool calls dropped
65. embedding [2026-01-01]: do injected mutants represent the errors agents actually make when auditing benchmark verifiers coupling to real faults
66. keyword [2026-01-01]: mutants valid substitute real faults LLM generated code errors distribution

orx discover openalex queries:

67. [2025-06-01]: multilingual GUI agent localization right-to-left
68. [2025-06-01]: mutation testing evaluation oracle benchmark LLM agents
69. [2025-06-01]: GPU kernel generation correctness tolerance verification LLM
70. [2025-06-01]: LLM evaluation run-to-run variance greedy decoding nondeterminism agents
71. [2025-06-01]: computer-use agent benchmark evaluator errors audit
72. [2014-01-01]: Are mutants a valid substitute for real faults in software testing

OpenReview api2 notes/search (group ICLR.cc/2027/Conference):

73. computer-use agent evaluator checker false negative
74. OSWorld rerun variance harness
75. nondeterminism agent evaluation inference reruns
76. kernel correctness verifier tolerance
77. mutation verifier agent benchmark blind spots
78. checker adequacy mutation analysis computer-use OSWorld
79. sparse attention indexer cross-lingual multilingual recall
80. right-to-left Arabic GUI agent localization
81. computer use agent reproducibility deterministic inference reruns
82. GPU kernel correctness tolerance precision TF32 audit
83. first divergence nondeterminism GUI agent screenshots
84. batch invariant deterministic vLLM evaluation agents
85. harness execution errors computer-use action translation bugs success

Reads (not searches): orx paper --full 2610.09142 and 2609.40284; orx paper
(report) 2604.06240, 2607.11022, 2604.24955; Hugging Face tree listing of
datasets/xlangai/ubuntu_osworld_verified_trajs (metadata only); OpenReview
api2 notes?id= for 6 submissions (blocked by the bot challenge).

## Slate owner: verification queries (2026-10-11)

Title resolution, `orx paper <id>` (report header compared with the cited
title), 102 ids: 2609.36931, 2609.38981, 2610.11678, 2608.06171, 2609.33044,
2609.40284, 2408.04667, 2604.17849, 2602.07150, 2609.26621, 2608.22331,
2609.04748, 2610.07274, 2607.28367, 2610.09142, 2609.22220, 2604.06240,
2504.08942, 2609.34262, 2603.10577, 2609.37315, 2604.24955, 2609.37322,
2606.29537, 2608.20362, 2610.02926, 2506.04135, 2610.08159, 2404.07972,
2609.34198, 2609.17394, 2610.00651, 2608.11323, 2609.07785, 2609.33812,
2508.13144, 2411.00640, 2610.04433, 2610.05533, 2610.00917, 2609.07925,
2607.04334, 2607.22798, 2605.00551, 2606.29472, 2610.01618, 2609.32459,
2607.16241, 2606.20128, 2610.05683, 2608.12700, 2609.19611, 2411.00442,
2512.07004, 2603.20421, 2609.00363, 2609.00381, 2607.16228, 2609.21058,
2602.05885, 2609.33074, 2507.05687, 2510.17891, 2607.11022, 2609.35677,
2604.22032, 2608.08722, 2502.05167, 2408.10151, 2503.01996, 2409.18006,
2608.27481, 2608.06506, 2608.26175, 2603.08869, 2607.01002, 2602.22453,
2308.01223, 2606.27306, 2610.03136, 2608.25832, 2606.24460, 2609.39001,
2608.21384, 2606.06203, 2609.33093, 2609.23490, 2608.08775, 2608.21794,
2608.11110, 2604.07666, 2601.04411, 2610.11231, 2610.11050, 2609.24890,
2609.18123, 2606.15034, 2609.36201, 2609.35889, 2610.11754, 2610.09089,
2509.14279. All 102 resolved to the cited title. Added after the slate's
not-carried table cited it: 2608.04975 (resolved).

Full text, `orx paper <id> --full`, searched for the figures quoted in the
slate: 2607.28367, 2604.17849, 2609.22220, 2609.21058, 2609.04748,
2609.36931, 2610.11678, 2607.16241, 2610.09142, 2609.40284, 2608.22331,
2609.17394.

OpenReview api2 `notes/search` (source=forum), to confirm forum ids:

- 'The Evaluator Also Varies' (cELldjX2oq: found; abstract read)
- 'The Reliability Gap computer use agents' (ezVIHPgaiG: found)
- 'FlexBI batch-invariant' (rGmv0X20Oj: found)
- 'Is This Agent Evaluable' (3vXI4xEByc: found; abstract read)
- 'OpenComputer Verifiable Software Worlds' (CgLTapI6Mr: found)
- 'Faster and Better Benchmark Bugs VLA Acceleration' (1ivlJ9lC5d: found)
- 'KernelAudit' (yTa4gvQUGG: found; abstract read)
- 'CROSS mLongRR' (sOXznQZgnM: found)
- 'Measuring the Checker mutation analysis GPU kernel' (Hdwn4xkEHp: found)
- 'weak-to-strong verifier KernelBench' and 'Scalable Weak-to-Strong Verifier Hardening for Agent Environments' (0ad4aBnjoQ: found; abstract read)
- 'CAVEAT computer use' (gfgvdsOX6v: not found; a different CAVEAT paper, kTuIMbhP1E, returned)

Data recount (not retrieval): the cell-3 drkernel parquet in the session
scratchpad (SHA-256 prefix 4ed72a9f85c069aa), read with pyarrow to recount
accepted rows and `tl.dot` users.
