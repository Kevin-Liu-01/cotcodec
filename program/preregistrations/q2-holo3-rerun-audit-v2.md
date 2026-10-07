# q2-holo3-rerun-audit-v2: why do the two Holo3 maintainer runs differ?

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger
row for the freeze time and `git_head_at_freeze`.** The doctor
(`scripts/run_holo3_rerun_audit_doctor.py`) applies the evaluator rule list
below to the real task configs only in `--stage v2`, and reads the
verified-run trajectory tarball beyond the region named in section 2 only in
`--stage v2-tarball`. Both stages exit 3 unless this file is frozen in that
repository ledger, whatever ledger `--ledger` names.

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
- **Related records:** `q2-holo3-rerun-audit-v1-posthoc` (POST-HOC; D10),
  frozen in the same ledger (D15). Owner sign-offs: D15 in
  `program/decisions.md`.

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
  build used them for rule (b)'s reference and signature rates and for rule
  (a)'s power (section 6; the `v2-design` receipt in
  `program/evidence/2026-10-07/holo3-v2-design/`).
- The OSWorld configs, through v1's URL flag. The URL-based split is known.
  Among the 342 clean tasks, run1-only vs run2-only passes are 7 vs 0 in the
  48 tasks where a non-local URL appears and 16 vs 9 in the other 294; the
  net is 14.
- The OpenCUA per-task results (reviewer, then this build's smoke run). The
  external reference in section 5 is therefore EXPLORATORY.
- The first ~232 MB of the compressed tarball (scout, for its structure;
  14 trajectory directories, 6 from run1 and 8 from run2) and the first 8 MB
  (reviewer, 2 directories). Their step counts may have been seen. No
  committed record lists the member names seen there, so the member layout
  the scanner expects (section 4) is checked when the tarball is scanned, not
  before.

Not read by anyone:

- The tarball after its first ~232 MB: run1 and run2 step counts, tool use,
  agent text and screenshots.
- The class of each task's evaluator under the rule list in section 3, and
  its join to the discordant tasks. All 361 configs and the outcomes were on
  disk while this rule list was written, so that blinding is self-attested;
  the plan's narrower L is registered as a sensitivity (section 5) for that
  reason.

**What the known split implies for rule (d).** Every L criterion that rests
on a remote URL (a live getter with a URL, `cloud_file` with a remote URL,
post-configuration with a remote URL) puts the task in v1's URL stratum by
definition. That stratum holds 7 run1-only and 0 run2-only clean tasks, so an
L set inside it can carry a net of at most 7 of the 14, a share of exactly
0.5, and only if all 7 of those tasks are L. A larger share needs L tasks
outside the URL stratum (clock rules, clock metrics, or live getters whose
URL is not in the config) that carry net run1-only passes. Rule (d) therefore
tests within strata (so the known 7-0 split cannot drive it) and keeps the
plan's 0.5 share bar as the materiality condition, with a separate label for
an enrichment that falls short of it.

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

Test: one-sided exact conditional test that run1-only tasks are
over-represented in L, stratified by v1's URL flag (the exact Mantel-Haenszel
test: in each stratum the number of run1-only tasks in L is hypergeometric
given that stratum's task, L and run1-only counts; p is the upper tail of the
sum over the two strata). Within the URL stratum this compares L with W,
outside it L with O. Net share = (run1-only minus run2-only in L) /
(run1-only minus run2-only overall); the overall net is 14.

Decision, at a fixed alpha of 0.04:

- **"checker-side time-drift candidate"** if p < 0.04 and the net share is at
  least 0.5. Handed to Stage 0a (evaluator mutation kit) with its task list.
- **"checker-side enrichment, minority of the gap"** if p < 0.04 and the net
  share is below 0.5. The L run1-only tasks go to Stage 0a as seeds; the gap
  is not attributed to checker time-dependence.
- **"not attributable to checker time-dependence"** if p >= 0.04.

The unstratified one-sided Fisher test of L vs not L is reported as
descriptive only.

Every rule (d) output carries the note "blinding to the class-outcome join is
self-attested" (section 2) and the largest net share the observed L
allocation could carry (in each stratum, as many run1-only tasks in L as L
holds, run2-only tasks only where L leaves no room for other tasks). Per D15,
a checker-side label (either of the first two) that the narrow-L sensitivity
(section 5) does not reproduce is reported as EXPLORATORY, not as a
confirmatory result.

### Rule (a): agent behaviour shift

Steps = the number of entries in a trajectory's `actions.json` that are JSON
objects with an `action` key. Over clean tasks whose run1 and run2 trajectories both join
(section 4): two-sided Wilcoxon signed-rank test of run1 vs run2 steps (scipy
default, zero differences dropped), and the effect size m = mean over tasks
of ln(run1 steps) - ln(run2 steps) (tasks with a zero count excluded from m).

Decision, at a fixed alpha of 0.01: **"agent-behaviour shift"** if p < 0.01
and |m| >= ln(1.10); otherwise **"no agent-behaviour shift"**. The median of
the per-task step ratios, the geometric-mean ratio exp(m) and the number of
tied pairs are reported as descriptive. The 23 run1-only and 9 run2-only
clean tasks pair a passing with a failing episode, and failing episodes run longer, so the known
outcomes alone move m towards run2 being longer; section 5 registers the
same test on concordant tasks as a sensitivity and section 6 states power by
direction.

### Rule (b): failure signatures of the unique failures

Run2-unique failures: clean tasks with y = 0 in run2, y = 1 in run1, and
y = 1 in every H Company run that scored the task (at least two must have).
There are 14 (run1-unique failures, defined the same way: 2). Each is given
the first class that applies to its run2 trajectory:

1. **environment:** any environment criterion in force (below);
2. **step cap:** at least 100 steps, whatever the final tool;
3. **premature answer:** steps at most 0.5 times the run1 trajectory's steps
   (this class cannot fire when the run1 trajectory does not join or parse);
4. **declared infeasible:** run2's `status.json` has an `agp_message`
   starting with `Infeasible` or `FAIL` among `agp_actions`;
5. **other.**

A task whose run2 trajectory does not join or does not parse is
**unclassifiable** and stays in the denominator. "Agent-side" means classes 2
and 3 together.

Environment criteria. The primary classification uses the two criteria that
can also be applied to the H Company reference (whose screenshots are not
read):

- tool error: an entry carrying, at any depth, a key named exactly `error`,
  `exception`, `traceback` or `tool_error` (case-sensitive) whose value is
  non-empty: not null, false, zero, an empty string, an empty list or an
  empty object;
- text: a case-insensitive match of any pattern below within the
  `reasoning`, the `thought` or the `note` text of an entry, each field
  matched on its own (no match spans two fields); a pattern counts once per
  entry.

A third criterion, screenshots (at least 3 consecutive screenshots whose
decompressed PNG bytes have the same SHA-256, in the order the trajectory's
`actions.json` references them, or in ascending image index if it references
none), enters only the all-criteria sensitivity (section 5). If no joined
episode has a screenshot under the member layout of section 4, that
sensitivity is reported as NOT RUN.

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
for each criterion, compute the share of episodes of clean tasks that both
runs passed (y = 1 in run1 and run2; 260 tasks, up to 520 episodes) on which
it fires. A primary criterion that fires on more than 20% of them is not in
force. The screenshot share is reported too, and each share is also reported
per run as a descriptive number.

**H rerun reference.** The three H Company runs are exchangeable reruns of
the same agent. For each H run, its unique failures are the clean tasks it
fails while both sibling H runs pass; each is classified by the same code and
order with the same criteria in force, with the first sibling in the order
`072452`, `072955`, `073458` as the comparison run for "premature answer"
(H runs have no `status.json`, so none is "declared infeasible"). Pooled over
the three runs, with both primary criteria in force, this reference was
computed before registration from already-read data and is registered here:
**30 unique failures: environment 0, step cap 9, premature answer 1, other 20
(agent-side 10).** The doctor recomputes it and fails a positive control if
it differs (section 4). If the guard takes a criterion out of force, the
reference is recomputed with the same criteria as run2.

Decision on the 14 run2-unique failures, each comparison a one-sided Fisher
exact test of run2's class count against the pooled reference count at a
fixed alpha of 0.025:

- **"R1-retro: infrastructure"** if the environment share is at least 0.5
  and its comparison gives p < 0.025;
- else **"agent-side session variation"** if the agent-side share is at
  least 0.5 and its comparison gives p < 0.025;
- otherwise **"unexplained"**.

With the registered reference and 14 tasks these are count thresholds:
environment at least 7 of 14 (the share bar binds) and agent-side at least
10 of 14 (the reference comparison binds). The run1-unique failures are
classified the same way and reported, with no decision.

### Rule (c): coverage

Of the 718 scored episodes (359 per run), count those whose `trajectory_id`
in `status.json` has a parsed `actions.json` in the tarball. If fewer than
95% join, rules (a) and (b) are reported as descriptive only, with no
decision label, and nothing else depends on their numbers.

### Error rates

Fixed and independent of which tests run: rule (d) at 0.04 and rule (a) at
0.01 (a Bonferroni split of 0.05 over the two hypothesis tests); rule (b)'s
two reference comparisons at 0.025 each. The nominal family-wise error rate
over rules (a), (b) and (d) is therefore 0.10 (the Bonferroni bound 0.04 +
0.01 + 2 x 0.025; D15). No test's threshold depends on whether another test
ran or on its p-value, so whether the tarball is read cannot change rule
(d)'s verdict. Rule (c) is a gate.

## 4. Joining, exclusions, run conditions and infrastructure failures

- The clean set, flags F1 to F6 and the run1/repair merge are v1's, computed
  by the same code (`harness/holo3_rerun_audit.py`, `build_v1_matrix`).
- Trajectory join: `status.json` `trajectory_id` of the merged run1 record
  and of run2, matched to the trajectory directory name in the tarball.
- Before fetching any tarball byte, the doctor checks the package's entry
  for it against the size, CRC-32 and SHA-256 of section 1. The tarball is
  then downloaded to the host's persistent run root with resume, and
  accepted only if its size, CRC-32 and SHA-256 all match section 1. A
  partial or complete file that fails a check is deleted; a file already in
  place is re-verified, never trusted. A failed check is an infrastructure
  failure: the download is repeated, and if it cannot pass, (a) to (c) are
  reported as NOT RUN, never as negative.
- Member layout: the scanner reads members named
  `{trajectory_id}/actions.json` and `{trajectory_id}/images/{index}.png`,
  each optionally gzipped, at any depth, and records how many members of each
  kind it saw (no names). If no `actions.json` matches, coverage is 0 and
  rule (c) makes (a) and (b) descriptive; if no joined episode has a matched
  screenshot, the all-criteria sensitivity is NOT RUN. The feature file must
  pass the same public-safety scan as a receipt, or it is not written
  (exit 1).
- Any doctor exit code 2 is an infrastructure failure: a fetch, identity or
  truncated-transfer error, or an integrity error (a member read fails its
  zip CRC-32, a verified-package member does not match `SHA256SUMS`, the
  leaderboard sheet does not match its SHA-256, or the tarball entry differs
  from section 1). The run is repeated with a new output path and an empty
  cache; no code or rule is edited to make a run pass. If the repeat fails
  with the same error on the same input, v2 is reported as NOT RUN
  (integrity).
- Positive controls that must pass for any v2 number to be read (exit 1
  otherwise): all 20 Holo3 per-domain leaderboard cells and both totals; the
  cited leaderboard cells; all 18 OpenCUA turn totals map one-to-one onto
  their leaderboard rows; the `SHA256SUMS` case, which rechecks every
  verified-package member read (a mismatch found while reading already
  exits 2); the blob manifest of the 361 task
  configs read at `f7230379` equals the one v1 read at `c7e54d24`
  (`3d4ae6da235e1d6627e72b389cda9fead93dbe9966ac8a3a3e23a1f39762bbf1`); the
  pooled H rerun reference equals the registered one (section 3); the
  receipt passes the public-safety scan.
- **A run that exits 1 yields no v2 result.** Its rule outputs are not read
  or reported as results; the failing control is reported. Inputs and code
  are pinned, so a repeat would fail the same way: the cause is investigated,
  any code change is a new registration with a new id, and this registration
  reports v2 as NOT RUN (control failure).
- **Run conditions.** A v2 receipt is the registered result only if it ran
  against the repository ledger (`program/preregistrations/ledger.jsonl`),
  committed and unmodified; with the five code files unchanged since the
  ledger's `git_head_at_freeze`; with the OpenCUA control (the doctor refuses
  `--skip-opencua` in v2); for a run that uses trajectories, within 14 days
  of `frozen_at`; and, for a v2 run given a feature file, with
  `--tarball-receipt` naming the v2-tarball receipt that wrote it, which
  must be a PASS labelled "v2 CONFIRMATORY" with every run condition true,
  the same five code-file hashes and ledger row, the section 1 tarball
  SHA-256 and the feature file's SHA-256. The doctor checks each condition,
  records them under `confirmatory_checks`, and labels any run that fails
  one "v2 NON-CONFIRMATORY". Runs use a clone whose history contains
  `git_head_at_freeze` (in a shallow clone the code check fails closed).
  Each receipt records the Python, numpy and scipy versions.

## 5. Sensitivity and exploratory analyses

Registered sensitivities (each reported beside the primary result; where its
decision differs, both are reported and the primary decision is labelled not
robust to that choice):

- **Narrow L (the reviewed plan's definition).** L restricted to the
  expected side: a getter in `evaluator.expected` with a type in the L list
  except `time_diff_range`, a `cloud_file` getter in `evaluator.expected`
  with a remote URL, or a `relativeTime` key inside `evaluator.expected`.
  Rule (d) is repeated with this L. A checker-side primary label it does not
  reproduce is reported as EXPLORATORY (D15; section 3).
- **Concordant tasks (rule (a)).** Rule (a)'s test and decision on the clean
  tasks with the same outcome in both runs (260 both pass, 50 both fail),
  which carry no offset from the known run1-only vs run2-only imbalance.
- **Probe region.** Rules (a) to (c) repeated after dropping every clean task
  whose run1 or run2 trajectory has its `actions.json` within the first
  250,000,000 compressed bytes of the tarball (this covers the 232 MB read
  before registration); a trajectory that has screenshots but no
  `actions.json` counts as probed. Rule (b)'s H reference is recomputed on
  the same tasks.
- **All criteria.** Rule (b) with all three environment criteria
  (screenshots included, no guard), against the reference with the same
  criteria. The reference cannot fire the screenshot criterion, so this
  sensitivity leans towards "R1-retro"; it is not a decision.
- **Plan's class order.** Rule (b) with the step cap checked before the
  environment criteria, as in the reviewed plan, against the reference
  classified in the same order.

Exploratory (labelled EXPLORATORY in every output):

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
- Evaluator class counts for all 361 tasks; run1-only and run2-only counts
  per class and per stratum; step-cap counts; tool-use histograms; all
  classes of the run1-unique failures.

## 6. Sample sizes, seeds and minimum detectable effects

Rules (a), (b) and (d) use exact or rank tests and no random numbers. The
design numbers below come from already-read inputs only (v1 totals and URL
strata; the H Company runs' rewards and step counts), computed by
`scripts/run_holo3_rerun_audit_doctor.py --stage v2-design` at commit
`0b0211678a6197107d064f3fdc9d4e41866e89d5` (receipt in
`program/evidence/2026-10-07/holo3-v2-design/`). They supersede the
`results.v2_design` section of the v1 receipt.

**Rule (d), exact power.** The stratum margins are known (URL stratum 48
tasks, 7 run1-only, 0 run2-only; other 294 tasks, 16 run1-only, 9
run2-only), so power depends only on how many L tasks each stratum holds and
on the odds ratio psi with which run1-only tasks fall in L (run2-only tasks
fall in L at random). Detection = p < 0.04 and net share >= 0.5, by exact
enumeration. In brackets: the test alone, without the share bar.

| L in URL stratum, L elsewhere | psi 1 | psi 3 | psi 5 | psi 10 | psi 30 |
|---|---:|---:|---:|---:|---:|
| 10, 0 | 0.000 (0.027) | 0.000 (0.264) | 0.003 (0.496) | 0.021 (0.796) | 0.182 (0.982) |
| 20, 0 | 0.001 (0.016) | 0.038 (0.214) | 0.111 (0.421) | 0.295 (0.707) | 0.642 (0.941) |
| 30, 0 | 0.028 (0.028) | 0.226 (0.226) | 0.388 (0.388) | 0.608 (0.608) | 0.842 (0.842) |
| 0, 20 | 0.000 (0.017) | 0.004 (0.264) | 0.034 (0.563) | 0.249 (0.904) | 0.875 (0.999) |
| 0, 40 | 0.001 (0.012) | 0.087 (0.348) | 0.313 (0.708) | 0.757 (0.969) | 0.993 (1.000) |
| 10, 20 | 0.004 (0.025) | 0.207 (0.477) | 0.548 (0.820) | 0.924 (0.989) | 1.000 (1.000) |
| 20, 40 | 0.032 (0.034) | 0.643 (0.664) | 0.926 (0.936) | 0.998 (0.999) | 1.000 (1.000) |

The psi = 1 column is the false-label rate in these allocations: at most
0.032 for the candidate label and 0.034 for either enrichment label. Over
every allocation of L (0 to 48 tasks in the URL stratum and 0 to 294
elsewhere, 14,455 allocations), the test's false-positive rate is at most
0.039996 (24 and 34 L tasks), below 0.04 as an exact conditional test must
be, and the candidate label cannot fire more often. If L lies inside the URL
stratum, the candidate label needs all 7 URL-stratum run1-only tasks in L
(power 0.18 to 0.84 even at psi = 30 above), so even large enrichment there
is often labelled "minority of the gap". The rule (d) output states the
largest share its L allocation could carry, and the report says when the
candidate label was out of reach. A null or minority result with small L is
weak evidence, and the report says so.

**Rule (a), power given the known outcome pattern.** The clean set's
outcomes are known: 260 tasks pass in both runs, 50 fail in both, 23 are
run1-only and 9 run2-only. Failing episodes run longer than passing ones: in
the H Company reruns, 27% of the failing episodes of discordant pairs and
45% of both-fail episodes reach the 100-step cap, against 0.9% of both-pass
episodes. Each simulated clean task therefore draws a step pair from the H
Company rerun pairs with the same outcomes (802 both-pass and 159 both-fail
pairs, each in both orders, and 106 discordant pairs oriented by outcome,
over the three run pairs), with steps counted as in rule (a). Run2's steps are then
multiplied by a factor on a random fraction of the tasks, rounded and capped
at 100 (400 simulations per seed, seeds 42, 43 and 44). The H reruns
themselves give m = -0.031, -0.021 and +0.009 and Wilcoxon p of 0.24, 0.56
and 0.69, with 43-47% of tasks at identical counts. With no change in
behaviour the known outcomes give a mean m of -0.017 (about a fifth of
ln 1.10) and a false-label rate of 0.001; on concordant tasks m is -0.001
and the rate 0.000. Mean power, primary rule and (in brackets) the
concordant-task sensitivity:

| Run2 steps | Power |
|---|---:|
| x1.05, all tasks | 0.035 (0.004) |
| /1.05, all tasks | 0.003 (0.009) |
| x1.10, all tasks | 0.693 (0.464) |
| /1.10, all tasks | 0.233 (0.458) |
| x1.15, all tasks | 0.965 (0.926) |
| /1.15, all tasks | 0.907 (0.989) |
| x1.20, all tasks | 1.000 (0.997) |
| /1.20, all tasks | 0.999 (1.000) |
| x2.0 on 20% of tasks | 0.911 (0.831) |
| x0.5 on 20% of tasks | 0.762 (0.915) |
| x1.5 on 30% of tasks | 0.846 (0.715) |
| x0.5 on 30% of tasks | 0.998 (1.000) |
| x1.5 on 40% of tasks | 0.984 (0.957) |
| x0.5 on 40% of tasks | 1.000 (1.000) |

Power depends on the direction. A uniform 15% change is detected with power
0.97 if run2 is longer and 0.91 if it is shorter; a uniform 10% change with
0.69 and 0.23; a 5% lengthening of run2 is labelled a shift with probability
0.035, a 5% shortening with 0.003. A uniform 20% change in either direction
and each subset shift in the table (2x on 20%, 1.5x on 30-40% and a halving
on 20-40% of tasks) are detected with power at least 0.76. The primary and
concordant decisions differ in 0.1% of simulations with no change and in up
to 25% at a uniform 10% change, where both sit on the threshold. The outcome-blind bootstrap of
all H rerun pairs (`results.v2_design.rule_a_power`), which this replaces,
gave 0.966 and 0.917 at 15% and 0.658 and 0.268 at 10%.

**Rule (b)** decides on 14 tasks against the registered reference of 30
(section 3): environment needs at least 7 of 14 and agent-side at least 10
of 14. Applied to each H run against the other two pooled, the rule labels
none of them; the superseded share-only rule labelled H run `072452` (4 of 8
agent-side on clean tasks) "agent-side session variation". On H Company
failing trajectories the text criterion fires on 7-10 of 71 per run, and on
passing clean episodes on 1.1% (tool errors 0%); of the failing trajectories
with a text hit, 4 of 7, 4 of 10 and 1 of 7 also hit the step cap, which is
why the environment class now comes first. Every H trajectory ends with
`answer`.

Power of rule (b) (exact binomial, full coverage): if each of the 14
run2-unique failures is an environment failure with probability 0.3, 0.4,
0.5, 0.6 or 0.7, the infrastructure label fires with probability 0.09, 0.31,
0.60, 0.85 or 0.97. If each is agent-side with probability 0.5, 0.6, 0.7, 0.8
or 0.9 and none is an environment failure, the agent-side label fires with
probability 0.09, 0.28, 0.58, 0.87 or 0.99, and with 0.004 at the
reference's own agent-side share of 1/3. Unclassifiable tasks stay in the
denominator and lower these numbers.

## 7. Reported regardless of outcome

Every quantity named in sections 3 to 6, the evaluator class, narrow-L flag
and reasons of each task, both stratum tables, the largest attainable net
share in L, the specificity-guard shares (pooled and per run), the coverage
fraction, the tarball member-layout counts, the H reference composition per
run, every sensitivity with its robustness flag, the positive controls, the
run-condition checks, input hashes, library versions and transfer totals, in
a dated evidence bundle under `program/evidence/` with the doctor receipts. A
rule that cannot run is reported as NOT RUN with the reason.

## 8. Timing

D15 (`program/decisions.md`) approves the 5.75 GB tarball read under D1,
for after this freeze; because the error rates are fixed, whether it happens
cannot change rule (d)'s verdict. The final v2 result is the doctor run that
includes rules (a) to (c) if the tarball is read and scanned within 14 days
of the freeze; otherwise it is the rule (d) run, with (a) to (c) NOT RUN.
Both runs are kept if both happen.

## Design decisions

Choices this registration makes where the reviewed plan left them open or
where it departs from the plan. Decisions 1-14 are accepted in D15
(`program/decisions.md`), with its two conditions applied in sections 3 and
5; decisions 15-21 record the changes made after the pre-freeze audit of
2026-10-07.

1. **The tarball read is part of v2, behind an explicit switch.** The plan
   made the 5.75 GB read optional pending the owner's OK, which D15 gives
   under D1. Rules (a) to (c) carry most of v2's confirmatory value and the
   data is public and MIT. The doctor still requires `--allow-large-download`
   and v2 frozen in the repository ledger. If the read does not happen within
   14 days of the freeze, (a) to (c) are NOT RUN and (d) stands alone at its
   own alpha.
2. **L is broader than "expected value fetched live", and the plan's L is a
   sensitivity.** Result-side getters that reload a live page at evaluation
   time (`active_tab_info`, `page_info`), clock-reading metrics, and
   post-configuration that opens a live URL also make the verdict for a fixed
   final state depend on when the evaluator runs, so they are L too. Because
   the broadening was written while configs and outcomes were on disk, the
   plan's narrow L is registered as a sensitivity.
3. **Rule (d) is stratified by v1's URL flag** and has a third label. The URL
   split (7-0 vs 16-9) is already known and bounds the share any URL-based L
   can carry at exactly 0.5; an unstratified test would mostly re-read it.
   The exact Mantel-Haenszel test measures only the new information (which
   tasks are L within each stratum); the plan's 0.5 share bar stays as the
   materiality condition, and an enrichment below it gets its own label.
4. **Fixed error rates instead of Holm.** With Holm over (a) and (d), (d)'s
   verdict depended on whether the tarball was read and on (a)'s p-value. A
   fixed Bonferroni split ((d) 0.04, (a) 0.01, keeping v1's 0.01 for a
   behaviour shift) removes that coupling, and a coverage-limited (a) feeds
   nothing.
5. **Rule (a)'s effect size is the mean log step ratio.** With 43-47% tied
   pairs, the plan's median-of-ratios gate stays at 1.0 under large shifts
   confined to some tasks and is asymmetric (a 1.1x shift and a 1/1.1x shift
   differ). |mean ln ratio| >= ln 1.10 is symmetric and sees subset shifts.
6. **Rule (b) labels must beat the H rerun reference.** On exchangeable
   reruns the step cap and premature answers already make up 20-50% of
   unique failures, so the plan's share-only bar could label rerun noise as
   "agent-side session variation". Each label now also needs a one-sided
   Fisher test against the registered pooled H reference.
7. **Environment before the step cap in rule (b).** Environment failures
   that exhaust the step budget (an agent stuck on a blocked page) were
   counted as agent-side under the plan's order. The plan's order is a
   registered sensitivity.
8. **Screenshots are a sensitivity criterion only.** The H reference cannot
   apply it (its screenshots are not read), so it cannot decide a label that
   claims an excess over the reference. The specificity guard (20% of
   both-pass episodes) still applies to the two primary criteria.
9. **Probe-region sensitivity** covers the tarball bytes read before
   registration instead of discarding those trajectories outright; a
   trajectory without an `actions.json` counts as probed.
10. **"Premature answer" has no final-tool condition**, because every H
    Company trajectory ends with `answer`; the plan's step ratio alone
    defines it.
11. **Unique failures need at least two H Company rewards**, and unjoined
    tasks stay in rule (b)'s denominator as unclassifiable, so poor coverage
    cannot inflate a class share.
12. **The pooled variance ratio is defined** as the ratio of between-turn to
    residual mean squares in a tasks x turns two-way layout of the binary
    outcome. It reproduces the review's 0.66.
13. **Evaluator configs are read at `f7230379`**, the review's best candidate
    for the maintainers' OSWorld revision; its `evaluation_examples/` equals
    the commit v1 used, so the W/O split is the same in both.
14. **Run conditions are enforced by the doctor**, not by convention: a run
    on another ledger, with changed code, without the OpenCUA control,
    outside the 14-day window or with a feature file that no confirmatory
    scan wrote is labelled NON-CONFIRMATORY or refused.
15. **The freeze gate reads the repository ledger.** Both v2 stages refuse
    unless this file is frozen in `program/preregistrations/ledger.jsonl`,
    whatever `--ledger` names, so a freeze in a scratch ledger can no longer
    unblind the class-outcome join or start the tarball download.
16. **The feature file's provenance is a run condition.** A v2 run given a
    feature file is confirmatory only if `--tarball-receipt` names the
    confirmatory v2-tarball receipt that wrote it, with the same code, freeze
    and tarball (section 4). Without this, a feature file from edited
    scanning code or written by hand could carry a confirmatory label.
17. **Rule (a) gets a concordant-task sensitivity and power by direction.**
    Each of the 23 run1-only and 9 run2-only clean tasks pairs a passing
    episode with a longer failing one, so the known imbalance offsets m
    towards run2 being longer (-0.017 under the design model) and makes
    power depend on the direction. The primary rule stays on all clean
    tasks; the concordant-task sensitivity has no such offset, and a primary
    decision it does not reproduce is labelled not robust (section 5).
    Section 6 states power given the known outcomes.
18. **Rule (d) outputs carry their limits.** Every output states that
    blinding to the class-outcome join is self-attested and the largest net
    share its L allocation could carry, and a checker-side label not
    reproduced by the narrow-L sensitivity is EXPLORATORY (D15).
19. **The environment criteria are exact.** A tool-error key must match
    exactly, case included, and have a non-empty value; the text patterns
    are matched within each field, never across fields. The earlier code
    counted `{"error": false}` and `Error` keys, and joined the fields.
20. **Integrity errors are infrastructure failures with a stopping rule.**
    CRC-32, `SHA256SUMS`, leaderboard SHA-256 and tarball-literal mismatches
    exit 2 and are repeated once from an empty cache; a repeat that fails the
    same way makes v2 NOT RUN (integrity). The `SHA256SUMS` case is
    recomputed rather than recorded as a pass.
21. **Pinned inputs are asserted in code.** The tarball's size, CRC-32 and
    SHA-256 from section 1 are checked before any byte is fetched; the v2
    config blob manifest must equal v1's (design decision 13); the feature
    file passes the public-safety scan; and the tarball's member layout is
    counted, so an unexpected layout shows in the receipt.
