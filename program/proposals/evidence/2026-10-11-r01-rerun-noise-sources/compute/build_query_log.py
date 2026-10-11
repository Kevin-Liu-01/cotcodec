#!/usr/bin/env python3
"""Write query-log.json for the R01 gauntlet (wave 1) from the four discovery cells' reports.

The cells (frontier, kill-shot, cross-domain, asset) returned their queries with the ids each
returned as structured output to the synthesis owner; they are transcribed here verbatim (ids
as reported). Raw orx outputs stay in the session scratchpad and are not committed; the
SHA-256 of each raw file of the frontier, kill-shot and asset cells is recorded when the
scratchpad is present (the cross-domain cell's raw files are not separable from older files in
its directory and are not hashed). The synthesis ran no search of its own.

Counting rule (the S2 precedent): orx discover queries count against the declared 150; the
other searches are listed and counted separately; paper reads and page fetches are reads.

Usage: python3 build_query_log.py --out query-log.json [--scratch DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

KW, EM, OA = "orx discover keyword", "orx discover embedding", "orx discover openalex"

FRONTIER = [
    (KW, "On the Reliability of Computer Use Agents | --limit 10", "2609.17885 2604.17849 2609.38008 2609.22000 2610.02320 2609.32600"),
    (KW, "batch-invariant inference computer-use agent reliability --published-after 2026-01-01 | --limit 12", "2608.22077 2604.17849 2609.32750 2610.00651 2606.31270 2610.04123"),
    (KW, "The Evaluator Also Varies | --limit 10", "2608.26827 2607.25136 2609.22700 2608.29912 2608.08189 2610.02924"),
    (KW, "Same Request, Different Answer prefix caching agent trajectories | --limit 10", "2609.04748 2610.05833 2608.25523 2608.30310 2608.01126 2609.32999"),
    (KW, "Dating the Model hidden date --published-after 2026-06-01 | --limit 10", "2609.36931 2608.18984 2608.19545 2610.09104 2609.33929 2610.04642"),
    (KW, "noise floor agent benchmark reruns temperature zero --published-after 2026-07-01 | --limit 12", "2608.22331 2609.24928 2610.06274 2609.19876 2609.32292 2609.24974"),
    (KW, "on-screen clock screenshot agent nondeterminism --published-after 2025-01-01 | --limit 10", "2608.06065 2608.26991 2609.33646 2608.05784 2608.12219 2610.11942"),
    (KW, "open-loop replay recorded actions virtual machine verdict --published-after 2025-01-01 | --limit 10", "2608.26306 2610.05452 2607.07196 2609.20625 2609.31374 2610.00385"),
    (KW, "Defeating Nondeterminism in LLM Inference batch invariance --published-after 2025-09-01 | --limit 15", "2608.14376 2609.25624 2609.38981 2610.09111 2608.24004 2609.16161"),
    (KW, "first divergence identical reruns agent trajectories --published-after 2026-01-01 | --limit 12", "2608.02276 2609.04148 2609.24928 2609.00829 2609.07782 2609.21423"),
    (KW, "Greedy Decoding Is Not Precision-Invariant | --limit 8", "2609.26621 2610.05052 2609.15504 2610.10596 2609.00355 2609.17184"),
    (KW, "TRACE identical reruns flip outcomes tau2-bench --published-after 2026-08-01 | --limit 10", "2610.11678 2609.32514 2609.33717 2609.36647 2610.07115 2608.16765"),
    (EM, "decomposing run-to-run outcome variance of multimodal desktop computer-use agents into serving numerics, environment timing, and observation noise such as on-screen clocks --published-after 2026-05-01 --prioritize recency | --limit 15", "2610.11050 2610.02320 2610.01787 2610.03818 2609.37176 2609.32778"),
    (EM, "replaying byte-identical recorded LLM requests to measure serving nondeterminism under continuous batching and prefix caching versus batch size one --published-after 2025-09-01 | --limit 15", "2609.32283 2609.28870 2610.09778 2610.05833 2609.38981 2610.09981"),
    (EM, "record and replay of agent action traces in a reset environment to separate environment nondeterminism from policy nondeterminism --published-after 2025-01-01 | --limit 12", "2610.06100 2609.32283 2608.14380 2610.11707 2610.09581 2609.38648"),
    (EM, "timestamps and clocks rendered in screenshots make GUI agent observations differ between reruns and cause trajectory divergence --published-after 2025-01-01 | --limit 12", "2610.11320 2609.34769 2609.36931 2609.28991 2610.03818 2609.16732"),
    (EM, "variance decomposition of agent benchmark scores into task, rerun, seed and harness components; how many reruns are needed --published-after 2026-06-01 | --limit 15", "2610.01618 2610.00651 2610.00917 2609.32961 2610.07274 2609.28850"),
    (EM, "animations, cursor blink, loading timing and asynchronous rendering as sources of nondeterminism in web or desktop agent benchmarks --published-after 2025-01-01 | --limit 12", "2609.40284 2609.34139 2609.34769 2609.17885 2609.35026 2609.10451"),
    (EM, "batch-invariant deterministic inference kernels for hybrid linear attention, Gated DeltaNet or Mamba layers --published-after 2025-09-01 | --limit 12", "2609.33051 2609.07816 2609.38166 2610.08527 2609.38981 2609.04098"),
    (EM, "nondeterministic outputs of vision-language models at temperature zero under vLLM serving; reproducibility of multimodal inference --published-after 2025-09-01 | --limit 12", "2609.33003 2609.33044 2608.29193 2609.00868 2607.24372 2608.17084"),
    (OA, "computer-use agent benchmark reliability run-to-run variance | --limit 15", "2607.28367 2511.04307 2609.07603 2604.06240 2606.20636 2507.02950"),
    (OA, "nondeterminism large language model agent evaluation reruns | --limit 15", "10.15781/t2ff3mk0s 10.1145/3736167 2607.10508 10.1016/j.patter.2026.101644 2607.27484 W7171749523"),
    (OA, "flaky tests time dependency asynchronous wait screenshot comparison | --limit 10", "2103.02669 10.22399/ijcesen.3644 10.13016/m2kh0f27r 10.24215/16666038.18.e16 2302.09330 10.1109/icst62969.2025.10989030"),
    (EM, "rerun nondeterminism sources in computer-use or GUI agent evaluation --published-after 2026-10-03 --prioritize recency | --limit 15", "2610.contamination-clock-evaluation-validity 2610.05622 2610.10088 2610.10961 2610.10988 2610.11447"),
    (KW, "nondeterminism agent evaluation --published-after 2026-10-03 --prioritize recency | --limit 15", "2610.07274 2610.09872 2610.07675 2610.09163 2610.05778 2610.09111"),
    (KW, "batch invariant --published-after 2026-09-15 --prioritize recency | --limit 15", "2610.08975 2610.04685 2610.04746 2610.long-documents-make-a-training-batch-smaller-than-it-looks 2610.04881 2609.37808"),
    (KW, "libfaketime | --limit 10", "2609.32391 2607.06107 2608.01135 2609.18805 2504.06026 2602.18689"),
    (KW, "FlexBI batch-invariant execution flexibility | --limit 10", "2609.38020 2609.16822 2606.20537 2610.03088 2609.06128 2609.02470"),
    (KW, "Measuring all the noises of LLM evals prediction noise data noise | --limit 10", "2512.21326 2610.10142 2609.14504 2609.12291 2609.21899 2606.08171"),
    (KW, "greedy vLLM replicates tau2-bench simulated user first discrepancy | --limit 10", "2608.14641 2608.03206 2609.38043 2609.33717 2610.09307 2610.02460"),
    (KW, "VLLM_BATCH_INVARIANT | --limit 10", "2605.27763 2606.15621 2609.25510 2609.01068 2609.32805 2610.05533"),
    (KW, "batch invariance vision-language model deterministic multimodal inference --published-after 2025-09-01 | --limit 12", "2609.40362 2610.05432 2609.38981 2610.05062 2608.14376 2609.10321"),
    (KW, "time-sensitive tasks OSWorld system clock date checker --published-after 2025-01-01 | --limit 10", "2606.29537 2610.03818 2609.24890 2609.39903 2606.21654 2608.01135"),
    (KW, "Agentic Flakiness flaky-test LLM agent reliability | --limit 10", "2609.25528 2609.25516 2608.06535 2607.09345 2610.04921 2608.17528"),
    (EM, "same action sequence replayed in a reset desktop virtual machine yields a different final state; environment nondeterminism in OSWorld-style benchmarks --published-after 2024-06-01 | --limit 12", "2609.36518 2610.07715 2610.02363 2610.02860 2609.34160 2609.26975"),
    (EM, "freezing or virtualizing system time in a virtual machine or container for reproducible agent benchmark evaluation --published-after 2024-06-01 | --limit 12", "2610.09944 2610.contamination-clock-evaluation-validity 2609.32391 2609.21267 2609.11515 2609.12216"),
    (EM, "masking dynamic screen regions such as the clock or animations in screenshots given to GUI agents to make evaluation reproducible --published-after 2025-01-01 | --limit 12", "2610.09469 2609.36939 2609.34113 2609.32679 2609.32036 2610.03818"),
    (EM, "prefix cache hit versus miss changes greedy decoding output numerically; nondeterminism from KV cache reuse in serving engines --published-after 2025-06-01 | --limit 12", "2609.28870 2610.05833 2610.11245 2609.28006 2609.38706 2610.06251"),
    (OA, "batch invariant kernels deterministic LLM inference | --limit 12", "2608.14376 2609.38981 2511.17826 2605.30218 2606.00516 10.1145/3830418.3843901"),
    (KW, "pass^k reliability computer-use agent repeated trials variance OSWorld --published-after 2025-06-01 | --limit 12", "2609.39903 2610.03818 2609.24890 2609.36927 2606.29537 2604.17849"),
    (OA, "visual regression testing dynamic content masking screenshot flakiness | --limit 10", "2607.01728 10.3390/info15080464 10.1145/3832783.3834455 10.70917/ijcisim-2026-5315 10.54660/ijmer.2021.2.1.63-75 2608.23616"),
    (EM, "how much of agent benchmark rerun variance is caused by inference-engine nondeterminism rather than environment or sampling --published-after 2026-03-01 --prioritize recency | --limit 15", "2610.07274 2610.01618 2610.05532 2610.00651 2609.38469 2609.34710"),
    (KW, "On Randomness in Agentic Evals | --limit 6", "2602.07150 2607.scaling-agentic-rl 2610.10142 2607.27518 2610.10611 2606.24855"),
    (KW, "Rabanser Kapoor agent reliability consistency robustness predictability | --limit 6", "2610.00651 2602.16666 2610.04123 2605.10516 2609.09218 2609.08832"),
    (KW, "BrowserGym reproducibility web agent nondeterminism | --limit 10", "2412.05467 2610.08773 2608.21898 2606.13608 2610.01491 2609.09774"),
    (EM, "web agent benchmark reproducibility problems: page load timing, dynamic content, live websites and reruns giving different outcomes --published-after 2024-06-01 | --limit 12", "2609.34139 2609.34537 2609.35814 2609.13582 2608.11234 2608.08392"),
    (EM, "making GUI agent screenshots byte-identical across episodes with a fixed clock, disabled animations and deterministic rendering --published-after 2024-01-01 | --limit 12", "2609.35671 2609.34321 2610.04800 2609.38778 2609.30609 2609.37176"),
    (KW, "Windows Agent Arena OSWorld runs variance standard deviation repeated --published-after 2025-01-01 | --limit 10", "2609.34821 2610.03818 2609.39903 2609.24890 2609.33812 2606.29537"),
    (KW, "first-divergence audit | --limit 10", "2609.33662 2609.00406 2609.29928 2609.22534 2609.24020 2608.04896"),
    (KW, "rerun variance agents --published-after 2026-10-07 --prioritize recency | --limit 15", "2610.10468 2610.11593 2610.12028 2610.12374 2610.09856 2610.09858"),
    (KW, "status bar clock --published-after 2024-01-01 | --limit 10", "2610.03182 2607.25404 2609.11442 2610.contamination-clock-evaluation-validity 2609.31837 2609.31832"),
    (OA, "GUI agent temperature zero reproducibility nondeterminism screenshots | --limit 12", "2609.09404 2608.06171 2607.17136 2409.10741 2603.21263 10.3386/w35374"),
    (KW, "Marconi prefix caching hybrid LLMs | --limit 6", "2608.30310 2609.33477 2411.19379 2610.08527 2608.11231 2605.05219"),
    (EM, "sources of nondeterminism in agent benchmark evaluation: serving, environment, simulator --published-after 2026-10-07 --prioritize recency | --limit 15", "2610.12452 2610.10310 2610.09426 2610.12360 2610.09872 2610.11877"),
    (KW, "Give Me FP32 or Give Me Death reproducible reasoning | --limit 6", "2609.08660 2609.32028 2609.24271 2609.14118 2609.24526 2609.21449"),
    (EM, "deterministic or batch-invariant LLM inference --published-after 2026-10-01 --prioritize recency | --limit 15", "2610.12325 2610.09111 2610.12083 2610.11765 2610.09778 2610.10655"),
    (EM, "replaying recorded GUI agent action trajectories in a fresh desktop or mobile environment to check whether the same actions reproduce the same outcome --published-after 2024-06-01 | --limit 12", "2610.11707 2608.14380 2609.34139 2609.30887 2609.37176 2609.32130"),
    (OA, "record and replay for Android are we there yet industrial cases | --limit 8", "10.1145/3106237.3117769 10.1145/3611643.3613880 2308.06657 2112.04128 10.1145/3544548.3580679 1605.08567"),
    (KW, "replayed trajectories OSWorld success reproduce actions --published-after 2025-01-01 | --limit 10", "2609.24890 2610.03818 2607.19395 2607.28272 2609.39903 2608.26991"),
]
FRONTIER_OTHER_SEARCH = [
    ("arXiv API search", 'ti:"Localizing Nondeterminism" OR ti:FlexBI OR ti:"Evaluator Also Varies"', "none relevant"),
    ("OpenReview api2 notes/search", "The Evaluator Also Varies", "cELldjX2oq RuzPH5rQbc bwCNQvkEyB"),
    ("OpenReview api2 notes/search", "FlexBI batch-invariant", "rGmv0X20Oj 4mirsxKGzl WWCDDlfucZ 36IAuaaGIZ"),
    ("OpenReview api2 notes/search", "computer-use agent nondeterminism rerun", "dKk6T7nVEP P1rGwEYDxm XScKMmbFmx iysNU5LeqR"),
    ("OpenReview api2 notes/search", "batch invariant inference agent evaluation", "rGmv0X20Oj 4mirsxKGzl 5eZmlUyFpl"),
    ("OpenReview api2 notes/search", "screenshot clock agent reproducibility", "none relevant"),
    ("OpenReview api2 notes/search", "prefix caching nondeterminism", "RUaMUu7vMX 9bodvMSCwD Vj48eXaQDM"),
    ("OpenReview api2 notes/search", "run-to-run variance GUI agent", "I0GKaJXdCh TqM6cln06N 39xo7Yz7Ed gyBEOMWSeM"),
    ("OpenReview api2 notes/search", "noise floor agent evaluation", "g9epz2aV4O 6uL7mSo94t"),
    ("OpenReview api2 notes/search", "deterministic inference agent benchmark reproducibility", "qXJ0EkHo2X 5eZmlUyFpl zgSkVdLJgD"),
    ("OpenReview api2 notes/search", "computer use agent reliability repeated runs", "ezVIHPgaiG dKk6T7nVEP P1rGwEYDxm ctXjjOR3g6"),
    ("OpenReview api2 notes/search", "serving nondeterminism evaluation", "Up1plqCqo3"),
    ("WebSearch", "vLLM batch invariance VLLM_BATCH_INVARIANT supported models hybrid Qwen3-Next", "docs.vllm.ai batch_invariance pages"),
    ("WebSearch", "AndroidWorld benchmark device date time fixed reproducibility", "listing pages; verified in 2405.14573 full text"),
    ("WebSearch", "vLLM prefix caching hybrid models mamba_cache_mode align Gated DeltaNet", "docs.lmcache.ai/mp/hybrid_models.html docs.vllm.ai automatic_prefix_caching"),
    ("WebSearch", "OSWorld-Verified time-sensitive tasks date dependent", "none relevant"),
    ("WebSearch (site:aclanthology.org)", "nondeterminism greedy decoding agent evaluation reruns", "2025.naacl-long.211"),
    ("WebSearch (site:aclanthology.org)", "GUI agent reproducibility screenshot nondeterministic evaluation variance repeated runs", "2025.findings-emnlp.720 2609.07712 2604.11784"),
]
FRONTIER_READS = ("2604.17849 2609.04748 2606.15621 2605.27763 2609.36931 2610.11678 2608.22331 2610.01618 2609.33812 "
                  "2609.20625 2609.26693 2512.21326 2602.07150 2405.14573 2609.40284 2607.17136 2103.02669 "
                  "2605.10516 2602.16666 2506.09501")

KILLSHOT = [
    (KW, "rerun nondeterminism computer-use agent serving environment decomposition", "2608.22077 2609.32750 2610.09111 2606.01533 2609.36201 2610.03818 2609.40284 2609.16251 2605.25707 2610.06597 2608.02352 2608.20319 2609.34432 2610.03088 2606.29472"),
    (KW, "open-loop replay recorded actions agent environment nondeterminism", "2609.32283 2609.33295 2610.01138 2608.08239 2609.20625 2609.40111 2609.24264 2610.06100 2609.16093 2608.27992 2608.00677 2608.25419 2609.35916 2608.23691 2607.17213"),
    (KW, "On the Reliability of Computer Use Agents", "2609.17885 2604.17849 2609.38008 2609.22000 2610.02320 2609.32600 2609.40284 2606.20636 2610.03089 2609.39903 2609.27273 2609.40253 2609.15134 2607.28367 2609.24890"),
    (KW, "The Evaluator Also Varies first divergence", "2607.05742 2606.31371 2608.26827 2607.25136 2609.22700 2608.29912 2606.29719 2608.08189 2610.02924 2609.34557 2610.10619 2608.04463 2609.32696 2610.00694 2609.32267"),
    (KW, "Same Request, Different Answer prefix caching agentic trajectories", "2609.04748 2610.05833 2608.25683 2609.28870 2610.05034 2609.32278 2608.30310 2608.01126 2609.33224 2609.35263 2609.33477 2609.09030 2609.24362 2608.22856 2609.11744"),
    (EM, "We decompose run-to-run outcome variance of a greedy-decoded GUI agent on a desktop benchmark into serving numerics (identical requests replayed under batched prefix-cached serving versus batch-1), environment noise (open-loop replay of recorded actions in a fresh VM) and observation-time noise (masking the on-screen clock)", "2610.01787 2609.32283 2610.07782 2610.09778 2609.29452 2609.27490 2609.34160 2609.25960 2609.32130 2609.34710 2609.31381 2609.13582 2609.26642 2609.22478 2609.26866"),
    (EM, "sources of nondeterminism in LLM agent benchmark reruns at temperature zero: inference engine batching versus environment", "2610.00651 2610.03102 2609.32283 2610.09778 2609.34215 2609.17695 2609.33044 2609.32379 2609.13582 2609.04667 2609.07785 2608.14376 2608.08239 2608.04714 2606.26185"),
    (OA, "nondeterminism agent benchmark reruns temperature zero variance sources", "2609.13582 2608.06171 2607.07391 2608.22510 10.3390/a19070607 2606.22504 2608.13867 2609.33875 2608.15286 2606.06240 2607.20353 10.1145/3786335.3813154 10.2139/ssrn.7411618 2609.33153 10.11575/prism/50921"),
    (KW, "batch invariant inference agent benchmark reliability temperature zero reruns", "2610.00651 2609.24928 2609.35551 2608.02276 2608.24004 2610.04123 2609.24974 2610.05782 2609.13582 2607.25891 2605.30218 2610.06597 2610.07094 2609.33023 2609.09218"),
    (KW, "butterfly effect small perturbation agent trajectory divergence greedy decoding", "2609.26621 2609.39379 2609.34059 2610.01108 2607.27248 2609.35775 2609.24150 2608.29748 2607.24715 2609.15504 2608.24338 2608.27514 2608.03447 2610.00694 2610.07350"),
    (KW, "TRACE identical reruns flip outcomes tau2-bench", "2610.11678 2609.32514 2608.11236 2609.33717 2609.36647 2610.07115 2608.16765 2609.28236 2609.03553 2608.01678 2606.09863 2609.07785 2605.06544 2604.05336 2608.14641"),
    (KW, "clock timestamp screenshot nondeterminism GUI agent evaluation", "2608.06065 2610.01215 2607.25904 2608.26991 2607.28227 2609.13873 2609.00048 2610.05861 2609.07712 2609.32679 2608.09278 2609.03438 2609.12394 2609.25769 2608.17659"),
    (KW, "batch-invariant deterministic inference hybrid linear attention Gated DeltaNet vLLM", "2605.22791 2609.20744 2608.20961 2609.04098 2609.36529 2608.12149 2608.30310 2610.05739 2609.14320 2609.38166 2610.05842 2610.02816 2607.07953 2609.38981 2605.16640"),
    (KW, "trajectory divergence identical prompt agent rerun inference engine attribution environment --published-after 2026-01-01", "2610.08951 2609.01360 2608.06909 2609.33676 2608.29646 2608.09153 2610.11334 2609.19830 2608.25518 2609.19819 2609.22655 2610.11600 2609.39068 2607.18754 2608.26195"),
    (OA, "reproducibility computer use agent OSWorld variance reruns", "2608.27808 2605.12131 2606.17929 W7160727055 2606.20363 2608.02352 2605.11030 2609.23953 2607.28609 2607.25891 2607.22368 2505.24876 2605.20833 2605.27922 2506.03231"),
    (KW, "identical inputs agent rerun divergence prefix cache batch composition screenshot agent --published-after 2026-08-01", "2608.25523 2609.04748 2609.32278 2609.32259 2609.28870 2608.06065 2609.34060 2610.05833 2609.19657 2609.32256 2610.08378 2609.35690 2609.32999 2608.26991 2609.37012"),
    (KW, "OSWorld reruns variance deterministic replay environment --published-after 2026-06-01", "2610.03818 2609.24174 2609.39903 2609.24890 2610.12033 2606.29537 2609.03941 2606.22948 2610.04638 2609.05374 2609.20625 2609.11194 2607.21557 2609.15364 2606.21654"),
    (EM, "deterministic inference does not reduce evaluation variance; rerun noise in agent benchmarks reflects policy sensitivity to any small perturbation, so making serving deterministic freezes noise rather than removing it", "2610.03102 2610.02860 2609.34215 2609.33044 2609.15940 2609.25528 2609.14400 2609.13582 2609.03203 2608.25067 2608.19269 2608.08239 2608.00152 2607.11116 2607.01469"),
    (OA, "batch invariance deterministic LLM inference agent evaluation reproducibility", "2511.17826 2609.25624 10.37547/tajet/volume08issue03-09 2601.08626 2307.14324 2607.29678 2606.01065 2608.28363 2607.25308 2607.20827 10.32604/cmc.2026.088835 2605.18597 2609.04748 2607.05458 2608.08282"),
]
KILLSHOT_OTHER = [("OpenReview api2 (Mac and host relay)", "notes?id=cELldjX2oq; notes?forum=cELldjX2oq", "403 ChallengeRequiredError, not bypassed (2 failed calls)")]
KILLSHOT_READS = "2604.17849 2609.04748 2610.11678 2608.04714 2609.13582 2610.01138 2608.30310 2610.00651 2608.15286 2608.14376 2609.38981 2608.08239 2607.01469 2609.20625"

CROSS = [
    (KW, "batch invariant kernels deterministic LLM inference", "2609.38981 2608.14376 2605.30218 2608.24004 2609.26621 2601.17768 2609.25624 2610.05305"),
    (KW, "reproducible reasoning greedy decoding numerical precision batch size", "2609.26621 2609.17184 2610.08975 2609.15504 2609.02728 2609.31796 2608.24004 2609.18723"),
    (EM, "identical requests to an LLM serving engine produce different greedy outputs because of batching, prefix caching and chunked prefill; measuring and removing serving nondeterminism", "2609.32283 2609.38981 2609.28870 2610.05833 2609.38706 2610.06251 2609.26621 2609.33044 2609.04748 2607.24372 2608.14376"),
    (OA, "root causes of flaky tests empirical analysis", "10.1145/2635868.2635920 10.1145/3756681.3756945 2504.16777 10.1109/icse43902.2021.00141 10.1016/j.simpa.2025.100794 2103.02669 10.1002/stvr.1791 2207.01047"),
    (OA, "UI-based flaky tests empirical analysis", "10.1109/icse43902.2021.00141 2103.02669 10.1109/icse-companion52605.2021.00108 10.5281/zenodo.4456026 2207.01047 10.1145/3613372.3613406 2305.08592"),
    (OA, "Shapley effects global sensitivity analysis Sobol indices", "10.1615/int.j.uncertaintyquantification.2019028372 10.1051/proc/201965266 2101.05487 10.1137/18m1221801"),
    (OA, "reproducible containers deterministic execution DetTrace", "10.1145/3373376.3378519 10.1007/s11219-022-09607-z 2302.12691 2608.27125"),
    (OA, "Engineering record and replay for deployability", "1705.05937 10.1145/3820002.3828587 10.1109/ase.2019.00022 10.1145/3724381 10.1145/3192366.3192380 10.1145/3516807.3516819"),
    (OA, "isolating cause-effect chains delta debugging failure-inducing differences between program runs", "10.1613/jair.1.19716 10.22028/d291-26043 10.26190/unsworks/32244 10.1145/3832109 W1790484086"),
    (OA, "De-flake your tests automatically locating root causes of flaky tests", "10.1109/icsme46990.2020.00083 2207.10143 2305.04735 10.13016/m2kh0f27r 10.1109/icst53961.2022.00034"),
    (OA, "generalizability theory variance components crossed facets decision study", "10.1201/b20498-3 10.1002/0470013192.bsa248 2411.17880 10.3758/s13428-017-0986-3"),
    (KW, "prefix caching hybrid Mamba linear attention state cache determinism", "2608.30310 2609.33477 2610.08527 2608.30386 2609.11998 2609.28870 2608.11231 2607.01299 2609.15030 2609.32278"),
    (OA, "Sobol' indices and Shapley value", "10.1137/130936233 10.1615/int.j.uncertaintyquantification.2019028372 10.1051/proc/201965266"),
    (OA, "The analysis of failure times in the presence of competing risks", "10.2307/2530374 10.1002/sim.1135 10.21037/atm.2016.08.62 W179935622"),
    (OA, "Simplifying and isolating failure-inducing input", "10.1109/32.988498 10.1109/tse.2025.3537167 10.1145/347636.348938 10.1145/3395363.3397349"),
    (OA, "Modeling and ranking flaky tests at Apple", "10.1145/3377813.3381370 10.1145/3428270 10.1109/tse.2022.3201209 10.1145/3832216"),
    (OA, "Brennan generalizability theory fixed facets universe of generalization", "10.58379/vmak1620 10.29221/jce.2016.19.2.251 10.1177/014662168000400209 10.21449/ijate.569996"),
    (KW, "agent trajectory divergence rerun nondeterminism first divergence step --published-after 2025-06-01", "2609.04748 2607.04528 2610.03529 2609.24928 2609.16617 2606.29038 2609.26621 2609.36864"),
    (OA, "Some guidelines and guarantees for common random numbers", "10.1287/mnsc.38.6.884 2605.04732 1410.6782"),
]
CROSS_READS = "2609.38981 2506.09501 2103.02669 1705.05937 2605.30218 2610.05833"
CROSS_FETCHES = ("thinkingmachines.ai blog; docs.vllm.ai batch_invariance (latest); lmsys.org SGLang deterministic; "
                 "Luo et al. 2014 PDF; DetTrace PDF (redirected, not read); Hermit README; gafferongames deterministic lockstep; "
                 "playwright.dev PageAssertions; qemu.org replay docs; reproducible-builds.org timestamps")

ASSET = [
    (KW, "batch invariant inference throughput overhead deterministic vLLM", "2609.38981 2608.14376"),
    (KW, "prefix caching changes greedy agent trajectories nondeterminism", "2608.25523 2608.30310"),
    (KW, "On the Reliability of Computer Use Agents", "2609.17885 2604.17849"),
    (EM, "identical request replay isolates serving numerics", "2609.32283 (and 9 off-topic results, not listed by the cell)"),
    (OA, "batch invariant deterministic LLM inference", "2608.14376 2605.30218 2609.38981 2511.17826 2609.26621 10.1145/3830418.3843901"),
    (KW, "Gated DeltaNet prefix caching", "2608.30310 2609.33477 2609.15030"),
]
ASSET_READS = "2609.38981"


def rows(cell: str, items) -> list[dict]:
    return [{"cell": cell, "tool": t, "query": q, "returned_ids": ids.split()} for t, q, ids in items]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scratch", type=Path)
    args = ap.parse_args()
    discover = rows("frontier", FRONTIER) + rows("kill-shot", KILLSHOT) + rows("cross-domain", CROSS) + rows("asset", ASSET)
    other = rows("frontier", FRONTIER_OTHER_SEARCH) + rows("kill-shot", KILLSHOT_OTHER)
    by_cell = {}
    for r in discover:
        by_cell[r["cell"]] = by_cell.get(r["cell"], 0) + 1
    ids = [i for r in discover for i in r["returned_ids"] if not i.startswith("(")]
    reads = {"frontier": FRONTIER_READS.split(), "kill-shot": KILLSHOT_READS.split(),
             "cross-domain": CROSS_READS.split(), "asset": ASSET_READS.split()}
    uniq_reads = sorted({x for v in reads.values() for x in v})
    raw = {}
    if args.scratch and args.scratch.is_dir():
        for sub, pattern in (("r01-frontier", "*.txt"), ("r01ks/orx", "*.json"), ("r01", "orx*.txt")):
            d = args.scratch / sub
            if d.is_dir():
                raw[sub] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob(pattern))}
    out = {
        "schema": "r01-query-log-v1",
        "gauntlet": "R01 first step, wave 1 (D73 i)",
        "counting_rule": "orx discover queries count against the declared 150 (S2 precedent); other searches listed separately; reads uncounted",
        "queries_against_budget": {
            "declared": 150, "reserve_for_triad": 30,
            "orx_discover_by_cell": by_cell, "orx_discover_total": len(discover),
            "synthesis_searches": 0,
            "remaining_under_counting_rule": 150 - len(discover),
            "reserve_intact_under_counting_rule": 150 - len(discover) >= 30,
            "other_searches": len(other) - 1, "failed_calls": 2,
            "total_if_other_searches_counted": len(discover) + len(other) - 1,
            "remaining_if_other_searches_counted": 150 - (len(discover) + len(other) - 1),
        },
        "prisma": {"ids_returned_by_discover": len(ids), "unique_ids": len(set(ids)),
                   "screened": "by title, all unique ids",
                   "read_beyond_title_unique_papers": len(uniq_reads), "papers_read": uniq_reads,
                   "web_pages_fetched_cross_domain": CROSS_FETCHES,
                   "direct_priors": 0},
        "discover": discover,
        "other_searches": other,
        "reads_by_cell": reads,
        "raw_output_sha256": raw or "scratchpad not present when built",
        "coverage_limits": [
            "orx 0.2.2 reports itself outdated (0.2.18); newest alphaXiv results 2026-10-09 to 2026-10-10",
            "OpenReview per-note pages and PDFs behind a browser challenge; abstracts via api2 search only",
            "ACL Anthology via the renewal dossier's regex queries 18-22 and two site-restricted web searches",
            "not searched: Semantic Scholar or Google Scholar citers, GitHub code search, vLLM issues, patents, X, Reddit, Chinese-language venues",
        ],
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("queries_against_budget",)}, indent=1))
    print(json.dumps({k: v for k, v in out["prisma"].items() if k != "papers_read"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
