# q2-holo3-rerun-audit-v2: why do the two Holo3 maintainer runs differ?

**Status: DRAFT for the program owner's review. Not frozen.** Freeze it with
`uv run python scripts/preregister.py freeze q2-holo3-rerun-audit-v2 program/preregistrations/q2-holo3-rerun-audit-v2.md`
before anyone (a) applies the evaluator rule list below to the real task
configs or (b) reads any byte of the verified-run trajectory tarball beyond
the region named in section 2. The doctor refuses both until the ledger holds
this file (`scripts/run_holo3_rerun_audit_doctor.py --stage v2` and
`--stage v2-tarball` exit 3 otherwise).

- **Experiment id:** `q2-holo3-rerun-audit-v2`
- **Question (Q2 Stage 0c follow-up):** the two OSWorld-Verified rows for
  Holo3-35B-A3B are maintainer runs of the same agent (run1 plus a repair
  pass, 82.56; run2, 78.15). Per task they are not exchangeable (v1 post-hoc
  record: McNemar 25 vs 9 on 359 tasks). Is the shift on the checker side
  (evaluators whose verdict depends on when they run) or on the agent side
  (different behaviour of the remotely served agent), or is it an
  environment failure that v1's log flags missed?
- **Code:** `scripts/run_holo3_rerun_audit_doctor.py`,
  `harness/holo3_rerun_audit.py`, `harness/holo3_v2.py`,
  `harness/remote_zip.py`, `harness/osworld_source.py`, at the commit the
  ledger records as `git_head_at_freeze`.
- **Related records:** `q2-holo3-rerun-audit-v1-posthoc` (POST-HOC; D10).

## 1. Data

| Input | Pin |
|---|---|
| Dataset | `xlangai/ubuntu_osworld_verified_trajs` at revision `5473c39e42a538a187a9b2c2b499db59d560fd8c` (MIT) |
| Verified-run package | `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_20260420_verified-run_with-local-rewards.zip`, 5,773,773,410 B, LFS SHA-256 `0dea53ac7b04fa7d962c2da48e4c5b4023455c221043378fe1857daf97251ca4` |
| Trajectory tarball (member of that package) | `trajectories/hcompany_verified_run_20260420_trajectories.tar.gz`, STORED, data at package offset 555, 5,748,726,271 B, CRC-32 `c5d5275e`, SHA-256 `3d6d65d1842f827494fb19fa4431bfe77f3b3430f3a7edf7673f928d114ffccd` (from the package's `SHA256SUMS`) |
| H Company runs | `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_hcompany-internal-runs-20260416_complete-with-rewards.zip`, 9,127,328,489 B, LFS SHA-256 `9f2c17ae83b605992608386e68c75b284d74217bc3267f2b851b68a2b838ea4c` |
| OSWorld task configs | `xlang-ai/OSWorld` at `f723037959a9d70af4a9f39922ec63ae6f078196` (PR #477 head, Apache-2.0); `evaluation_examples/` is identical to `c7e54d24d136d52be0c6d5a7487a1a32f99e7017`, the commit v1 read |
| OpenCUA three-run sets | the six `opencua_agent-opencua_{7b,32b}-cot_l2-action_history-3image-Ubuntu-{15,50,100}steps.zip` archives at the same dataset revision (sizes and LFS SHA-256 in `harness/holo3_rerun_audit.py`) |
| Leaderboard cells | `OS-World/OS-World.github.io` at `62f8466dbe8b4d67c104b5ead3f8271da01aa09d`, `static/data/osworld_verified_results.xlsx`, SHA-256 `cf6b4b67eed566ddcd5a8b7ad2d89013157978dad0eea76ea12d2377471efc09` (no license: cited, not stored) |

The tarball's paths contain a personal directory name. The scanner keeps only
trajectory ids and derived numbers; no path, screenshot or agent text is
written anywhere.

## 2. What has already been read, and by whom

Read before this registration (none of it can be tested confirmatorily here):

- All per-task scores, flags, elapsed times and AGP outcomes of run1, the
  repair pass and run2, and the rewards of the three H Company runs (v1,
  2026-10-07; reproduced by this build).
- The H Company runs' `actions.json` (scout, reviewer and this build). This
  build used them to calibrate rule (b)'s signatures (section 6).
- The OSWorld configs, through v1's URL flag. The URL-based split is known:
  among clean tasks, run1-only vs run2-only passes are 7 vs 0 where a
  non-local URL appears and 16 vs 9 elsewhere.
- The OpenCUA per-task results (reviewer, then this build's smoke run). The
  external reference in section 5 is therefore EXPLORATORY.
- The first ~232 MB of the compressed tarball (scout, for its structure;
  14 trajectory directories, 6 from run1 and 8 from run2) and the first 8 MB
  (reviewer, 2 directories). Their step counts may have been seen.

Not read by anyone:

- The tarball after its first ~232 MB: run1 and run2 step counts, tool use,
  agent text and screenshots.
- The class of each task's evaluator under the rule list in section 3, and
  its join to the discordant tasks.

## 3. Confirmatory rules

Unit: task. Population: the 342 **clean** tasks of v1 (scored in both runs
and not flagged F2, F3, F4 or F6 in either run). Outcome y = 1[score >= 0.5].
A *run1-only* task has y = 1 in run1 and 0 in run2; *run2-only* the reverse.

### Rule (d): checker-side time dependence

Each task's evaluator is classified from its config JSON alone, before the
classes are joined to outcomes, as the first that applies of:

- **L** if any of:
  - a getter in `evaluator.result` or `evaluator.expected` (dict or list) has
    type `rule_relativeTime`, `time_diff_range`, `info_from_website`,
    `page_info`, `active_tab_info`, `gotoRecreationPage_and_get_html_content`,
    `number_of_search_results` or `pdf_from_url`;
  - a getter of type `cloud_file` carries a remote URL (as defined below);
  - `evaluator.func` (string or list) includes
    `compare_time_in_speedtest_results`;
  - any key named `relativeTime` appears anywhere in `evaluator`;
  - `evaluator.postconfig` carries a remote URL.
- **W** if not L and a remote URL appears anywhere in `config` or
  `evaluator` (v1's web flag, unchanged).
- **O** otherwise.

A remote URL matches `https?://[^\s"']+` in the JSON text and does not start
with `http://` or `https://` followed by `localhost`, `127.0.0.1` or
`huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache`.

Why these getters: at OSWorld `f7230379` each one either loads a live web page
while the evaluator runs (`page.goto` or an HTTP GET) or computes an expected
value from the clock. `time_diff_range` only returns a tolerance, but its one
consumer is the speed-test metric, which compares a timestamp with the
evaluator's clock. For any of them, the verdict for a fixed final VM state
can change with the time of evaluation (run1 12:18-17:44 UTC, run2
19:14-23:51 UTC, 2026-04-20).

Test: one-sided Fisher exact test that run1-only tasks are over-represented
in L, on the 2 x 2 table (L, W or O) x (run1-only, not run1-only) over the 342
clean tasks. Net share = (run1-only minus run2-only in L) / (run1-only minus
run2-only overall); the overall net is 14.

Decision: **"checker-side time-drift candidate"** if the Holm-adjusted p is
below 0.05 and the net share is at least 0.5; otherwise **"not attributable
to checker time-dependence"**. A candidate is handed to Stage 0a (evaluator
mutation kit) with its task list.

### Rule (a): agent behaviour shift

Steps = the number of entries with an `action` key in a trajectory's
`actions.json`. Over clean tasks whose run1 and run2 trajectories both join
(section 4), two-sided Wilcoxon signed-rank test of run1 vs run2 steps
(scipy default, zero differences dropped), and the median over tasks of
run1 steps / run2 steps (tasks with a zero count excluded from the ratio).

Decision: **"agent-behaviour shift"** if the Holm-adjusted p is below 0.01
and |median ratio - 1| >= 0.10; otherwise **"no agent-behaviour shift"**.

### Rule (b): failure signatures of the unique failures

Run2-unique failures: clean tasks with y = 0 in run2, y = 1 in run1, and
y = 1 in every H Company run that scored the task (at least two must have).
There are 14 (run1-unique failures, defined the same way: 2). Each is given
the first class that applies to its run2 trajectory:

1. **step cap:** at least 100 steps, whatever the final tool;
2. **environment:** any criterion in force from
   - tool error: an entry carrying a non-empty key named `error`,
     `exception`, `traceback` or `tool_error` (at any depth),
   - text: a match, case-insensitive, of any pattern below in the
     `reasoning`, `thought` or `note` text of any entry,
   - screenshots: at least 3 consecutive screenshots, in the order the
     trajectory references them, whose decompressed PNG bytes have the same
     SHA-256;
3. **premature answer:** steps at most 0.5 times the run1 trajectory's steps;
4. **declared infeasible:** run2's `status.json` has an `agp_message`
   starting with `Infeasible` or `FAIL` among `agp_actions`;
5. **other.**

A task whose run2 trajectory does not join or does not parse is
**unclassifiable** and stays in the denominator.

Text patterns (label: regular expression):

```text
captcha: captcha|recaptcha|hcaptcha
unusual_traffic: unusual traffic
access_denied: access denied
bot_challenge: are you a robot|not a robot|verify (?:that )?you are (?:a )?human
challenge_page: cloudflare|checking your browser|just a moment
chrome_net_error: \berr_[a-z_]{4,}\b
unreachable: (?:site|page) can.?t be reached|cannot be reached|could not be reached
page_load: page (?:failed|fails|did not|didn.?t|is not|isn.?t) (?:to )?load
connection: connection (?:reset|refused|timed out|was reset|failed|error)
offline: no internet|you are offline|network error
http_error: \b(?:403 forbidden|429 too many requests|502 bad gateway|503 service unavailable|504 gateway time-?out)\b
rate_limit: too many requests|rate limit
```

The labels are `captcha`, `unusual_traffic`, `access_denied`,
`bot_challenge`, `challenge_page`, `chrome_net_error`, `unreachable`,
`page_load`, `connection`, `offline`, `http_error` and `rate_limit`.

**Specificity guard (decided before any unique failure is classified):**
for each of the three environment criteria, compute the share of episodes of
clean tasks that both runs passed (y = 1 in run1 and run2; 260 tasks, up to
520 episodes) on which it fires. A criterion that fires on more than 20% of
them is not in force for the primary classification. The classification
with all three criteria is reported as a sensitivity.

Decision on the 14 run2-unique failures: if class 2 covers at least 50%
(7 or more), **"R1-retro: infrastructure"**; else if classes 1 and 3
together cover at least 50%, **"agent-side session variation"**; otherwise
**"unexplained"**. The run1-unique failures are classified the same way and
reported, with no decision.

### Rule (c): coverage

Of the 718 scored episodes (359 per run), count those whose `trajectory_id`
in `status.json` has a parsed `actions.json` in the tarball. If fewer than
95% join, rules (a) and (b) are reported as descriptive only, with no
decision label.

### Multiplicity

Holm over the two hypothesis tests, (a) and (d), always with m = 2. If (a)
is not run (the tarball is not read), it enters Holm with p = 1. Rule (b) is
a share rule, not a test, and (c) is a gate.

## 4. Joining, exclusions and infrastructure failures

- The clean set, flags F1 to F6 and the run1/repair merge are v1's, computed
  by the same code (`harness/holo3_rerun_audit.py`, `build_v1_matrix`).
- Trajectory join: `status.json` `trajectory_id` of the merged run1 record
  and of run2, matched to the trajectory directory name in the tarball.
- The tarball is downloaded to the host's persistent run root with resume,
  then accepted only if its size, CRC-32 and SHA-256 all match section 1. A
  failed check is an infrastructure failure: the download is repeated, and if
  it cannot pass, (a) to (c) are reported as NOT RUN, never as negative.
- Any doctor exit code 2 (fetch, identity or integrity error) is an
  infrastructure failure. The run is repeated with a new output path; no
  code or rule is edited to make a run pass.
- Positive controls that must pass for any v2 number to be read (exit 1
  otherwise): all 20 Holo3 per-domain leaderboard cells and both totals; all
  18 OpenCUA turn totals map one-to-one onto their leaderboard rows; every
  verified-package member matches `SHA256SUMS`; every member read passes its
  zip CRC-32; the leaderboard sheet matches its SHA-256 and the cited cells.

## 5. Exploratory analyses (labelled EXPLORATORY in every output)

- **External exchangeability reference.** For each of the 18 OpenCUA rerun
  pairs (6 archives x 3 turns) and the 3 H Company pairs: exact McNemar on
  y = 1[s >= 0.5] over tasks both turns scored, and z = (a_only - b_only) /
  sqrt(a_only + b_only). The rank of the Holo3 run1-run2 |z| (2.74 on 359
  tasks) among them, and the pooled ratio of between-turn to residual mean
  squares from a tasks x turns two-way layout of y, per archive over tasks
  all three turns scored, pooled over the 6 archives (12 between-turn degrees
  of freedom). Label "pair-specific session shift" if the Holo3 |z| exceeds
  every reference |z| and the pooled ratio is at most 1.5. Already computed
  before registration: max reference |z| 1.86; pooled ratio 0.663 on (12,
  4282) df.
- **Probe-region sensitivity (registered).** Rules (a) to (c) repeated after
  dropping every clean task whose run1 or run2 trajectory has its
  `actions.json` within the first 250,000,000 compressed bytes of the tarball
  (this covers the 232 MB read before registration). If a decision differs
  from the primary one, both are reported and that decision is labelled "not
  robust to the pre-registration probe".
- Evaluator class counts for all 361 tasks; run1-only and run2-only counts
  per class; the L vs W table within URL-flagged tasks; step-cap counts;
  tool-use histograms; all classes of the run1-unique failures.

## 6. Sample sizes, seeds and minimum detectable effects

Rules (a), (b) and (d) use exact or rank tests and no random numbers. Power
was simulated before registration from already-read inputs only (v1 totals:
23 run1-only and 9 run2-only among 342 clean tasks; the H Company runs'
step counts), with seeds 42, 43 and 44 (`results.v2_design` of the v1
doctor receipt, `program/evidence/2026-10-06/holo3/`).

Rule (d), detection = Fisher p < 0.025 (the Holm worst case) and net share
>= 0.5, 2,000 simulations per seed. Mean power over seeds by the number of L
tasks among the 342 (n_L) and the run1-only rate among them:

| n_L | rate 0.15 | rate 0.20 | rate 0.30 | rate 0.40 |
|---:|---:|---:|---:|---:|
| 10 | 0.007 | 0.018 | 0.055 | 0.116 |
| 20 | 0.034 | 0.088 | 0.294 | 0.587 |
| 40 | 0.192 | 0.482 | 0.932 | 0.997 |
| 60 | 0.502 | 0.883 | 0.997 | 0.999 |

So (d) can detect a run1-only rate of about 0.3 in L if L holds 40 or more
clean tasks, and needs a rate near 0.5 or more if L holds 20 or fewer. A
null (d) with small n_L is weak evidence, and the report will say so.

Rule (a), detection = Wilcoxon p < 0.005 (the Holm worst case for the 0.01
threshold) and |median ratio - 1| >= 0.10, by bootstrapping 342 task pairs
from the H Company reruns' step counts (400 simulations per seed). The H
reruns themselves show a median step ratio of 1.0 and Wilcoxon p of 0.24,
0.56 and 0.69, with 43-47% of tasks at identical counts. Power by the factor
applied to run2's steps: 1.00 and 1.05: 0.00; 1.10: 0.13; 1.15, 1.20 and
1.30: 1.00. The minimum detectable shift is a 15% change in steps; the
median-ratio threshold, not the test, binds below that.

Rule (b) decides on 14 tasks; 7 of 14 is the 50% bar, with a 95% Clopper-
Pearson interval of 23% to 77%. Its verdict is a coarse attribution, not a
precise share. Calibration on the H Company runs (text and step criteria
only): the text signatures fire on 7-10 of 71 failing and 2-4 of about 286
passing trajectories per run; no tool-error keys occur; 27-30 of 71 failing
trajectories hit the step cap; every trajectory ends with `answer`.

## 7. Reported regardless of outcome

Every quantity named in sections 3 to 6, the evaluator class and reasons of
each task, the specificity-guard shares, the coverage fraction, the positive
controls, input hashes and transfer totals, in a dated evidence bundle under
`program/evidence/` with the doctor receipt. A rule that cannot run is
reported as NOT RUN with the reason.

## 8. Timing

The final v2 result is the doctor run that includes rules (a) to (c) if the
tarball is read within 14 days of the freeze; otherwise it is the rule (d)
run with (a) entering Holm at p = 1. Both runs are kept if both happen.

## Design decisions

Choices this draft makes where the reviewed plan left them open or where it
departs from the plan. Each needs the owner's acceptance at freeze.

1. **The tarball read is part of v2, behind an explicit switch.** The plan
   made the 5.75 GB read optional pending the owner's OK. Rules (a) to (c)
   carry most of v2's confirmatory value, the data is public and MIT, and D1
   authorises recorded research downloads to the host. The doctor still
   requires `--allow-large-download` and a frozen v2. If the owner withholds
   the download, (a) to (c) are NOT RUN and (d) stands alone with p_a = 1.
2. **L is broader than "expected value fetched live".** The plan defined L
   by the expected-value side only. Result-side getters that reload a live
   page at evaluation time (`active_tab_info`, `page_info`), clock-reading
   metrics, and post-configuration that opens a live URL also make the
   verdict for a fixed final state depend on when the evaluator runs, so
   they are L too.
3. **W keeps v1's URL rule unchanged**, so the URL split already seen
   (section 2) is not the contrast under test; the new information is which
   tasks are L.
4. **Holm with a fixed m = 2.** A test that does not run enters with p = 1,
   so the family cannot shrink after the fact. (a) keeps v1's 0.01
   threshold for a step-count shift; (d) uses 0.05.
5. **Specificity guard for rule (b).** The identical-screenshot criterion
   cannot be calibrated before registration without reading screenshots.
   Checking it on episodes both runs passed, before classifying any
   failure, stops a non-specific criterion from deciding the verdict.
6. **Probe-region sensitivity** covers the tarball bytes read before
   registration instead of discarding those trajectories outright.
7. **"Premature answer" has no final-tool condition**, because every H
   Company trajectory ends with `answer`; the plan's step ratio alone defines
   it.
8. **Unique failures need at least two H Company rewards**, and unjoined
   tasks stay in rule (b)'s denominator as unclassifiable, so poor coverage
   cannot inflate a class share.
9. **The pooled variance ratio is defined** as the ratio of between-turn to
   residual mean squares in a tasks x turns two-way layout of the binary
   outcome. It reproduces the review's 0.66.
10. **Evaluator configs are read at `f7230379`**, the review's best candidate
    for the maintainers' OSWorld revision; its `evaluation_examples/` equals
    the commit v1 used, so the W/O split is the same in both.
