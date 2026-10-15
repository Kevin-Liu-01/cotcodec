#!/usr/bin/env bash
# am3-nonabstain-generality-v1, pre-freeze check 2: a rehearsal of section 16's operator scripts on
# the host under a fake HOME, with sbatch, scontrol, squeue and nvidia-smi stubbed on PATH. No job
# is submitted, no GPU is used, no model runs, and no held-out or abstention input is opened: the
# scripts run in dev mode against a copy of the development artifact and fake build, selftest and
# job records. The fake HOME sits under ~/cotcodec-runs so the lane submitter's run-root check
# passes. Each case prints PASS or FAIL; the copied artifact is removed at the end.
# Usage: am3g-rehearse.sh <full commit id> <bundle path>   (run from the dev checkout at that commit)
set -uo pipefail
G="${1:?full commit id}"; BUNDLE="${2:?bundle}"; SHORT=${G:0:8}
REAL=$HOME; REAL_R=$REAL/cotcodec-runs/stage0/am3g-dev-dryrun
BASE=$REAL/cotcodec-runs/stage0/am3g-rehearsal-$SHORT
rm -rf "$BASE"; mkdir -p "$BASE/bin" "$BASE/home"
FAKE=$BASE/home
export UV_CACHE_DIR=$REAL/.cache/uv UV_PYTHON_INSTALL_DIR=$REAL/.local/share/uv/python
cat > "$BASE/bin/sbatch" <<'EOF'
#!/usr/bin/env bash
echo "sbatch $*" >> "$HOME/stub.log"
case " $* " in
  *" --test-only "*) [[ -f "$HOME/stub.testonly-fails" ]] && { echo "sbatch: error: stubbed test-only failure" >&2; exit 1; } ;;
  *) [[ -f "$HOME/stub.sbatch-fails" ]] && { echo "sbatch: error: stubbed failure" >&2; exit 1; }
     [[ -f "$HOME/stub.sbatch-garbage" ]] && { echo "not a job id"; exit 0; } ;;
esac
n=$(( $(cat "$HOME/stub.jobid" 2>/dev/null || echo 9000) + 1 )); echo "$n" > "$HOME/stub.jobid"; echo "$n"
EOF
cat > "$BASE/bin/scontrol" <<'EOF'
#!/usr/bin/env bash
if [[ "$1 $2" == "show nodes" ]]; then printf '   Gres=gpu:h100:8\n   GresUsed=gpu:h100:2(IDX:0-1)\n'; exit 0; fi
if [[ "$1 $2" == "show job" ]]; then f="$HOME/stub-jobs/$3.txt"; [[ -f $f ]] && cat "$f" && exit 0
  echo "slurm_load_jobs error: Invalid job id specified" >&2; exit 1; fi
exit 0
EOF
cat > "$BASE/bin/squeue" <<'EOF'
#!/usr/bin/env bash
f="$HOME/stub.squeue"; [[ -f $f ]] || exit 0
case "$*" in *"%i"*) awk '{print NR, $1, "RUNNING", "1:00", $2}' "$f" ;; *) cat "$f" ;; esac
EOF
printf '#!/usr/bin/env bash\nfor i in 0 1 2 3 4 5 6 7; do echo "$i, 0 MiB, 0 %%"; done\n' > "$BASE/bin/nvidia-smi"
chmod +x "$BASE"/bin/*
export PATH=$BASE/bin:$PATH HOME=$FAKE
pass=0; fail=0
check() { if eval "$2"; then echo "PASS $1"; pass=$((pass+1)); else echo "FAIL $1"; fail=$((fail+1)); fi; }
nosub() { ! grep -v -e '--test-only' "$FAKE/stub.log" 2>/dev/null | grep -q "job-name=am3g-development"; }

R=$FAKE/cotcodec-runs/stage0/am3g-dev-dryrun
mkdir -p "$R/bundles" "$R/bootstrap"
cp "$BUNDLE" "$R/bundles/am3g-$SHORT.bundle"
git -C "$REAL_R/checkout" show "$G:ops/am3g/am3g-env.sh" > "$R/bootstrap/am3g-env.sh"
git -C "$REAL_R/checkout" show "$G:ops/am3g/am3g-checkout.sh" > "$R/bootstrap/am3g-checkout.sh"

# --- bootstrap checkout and its self-check
bash "$R/bootstrap/am3g-checkout.sh" dev "$G" > "$BASE/checkout.out" 2>&1
check "bootstrap checkout at $SHORT, clean" "[[ \$(git -C $R/checkout rev-parse HEAD) == $G && -z \$(git -C $R/checkout status --porcelain) ]]"
echo "# tampered" >> "$R/bootstrap/am3g-env.sh"
bash "$R/bootstrap/am3g-checkout.sh" dev "$G" > "$BASE/checkout2.out" 2>&1; rc=$?
check "a bootstrap copy that differs from the commit's is refused" "[[ $rc -ne 0 ]] && grep -q 'differs from' $BASE/checkout2.out"
cd "$R/checkout" || exit 2
O=ops/am3g

# --- the image capture (major 1) and the build record checks (minor 6)
mkdir -p "$R/capsule"; echo capsule > "$R/capsule/source-$SHORT.tar.gz"; echo '{}' > "$R/capsule/source-receipt-$SHORT.json"
CAP=$(sha256sum "$R/capsule/source-$SHORT.tar.gz" | cut -d" " -f1)
IMG=sha256:$(printf 'a%.0s' $(seq 64))
BASE_IMG=docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f
mk_build() {  # $1 build root, $2 base image, $3 vLLM commit
  mkdir -p "$1"; echo "$IMG" > "$1/image-id.txt"
  printf '{"git_sha": "%s", "source_sha256": "%s", "status": "PASS"}\n' "$G" "$CAP" > "$1/provenance-verification.json"
  printf '{"overlay_image_id": "%s", "git_sha": "%s", "source_sha256": "%s", "vllm_version": "0.31.0", "vllm_commit": "%s", "base_image": "%s"}\n' \
    "$IMG" "$G" "$CAP" "${3:-db9527a46873454610df6dbedf79a36d6bf1a7f6}" "$2" > "$1/build-receipt.json"
}
sed -n "/<<'PY'/,/^PY$/p" $O/am3g-image.sh | sed '1d;$d' > "$BASE/image-checks.py"
E=$REAL_R/overlay-build-vllm-eae156cf
python3 "$BASE/image-checks.py" "$E" "$(tr -d ' \n' < "$E/image-id.txt")" \
  "$(sha256sum "$REAL_R/capsule/source-eae156cf.tar.gz" | cut -d" " -f1)" eae156cf715541e45eb63866dd4ae50db5938250 > "$BASE/image-real.out" 2>&1
check "the image checks pass on the real development build record (job 1467, eae156cf)" "[[ $? -eq 0 ]]"
mk_build "$R/overlay-build-vllm-$SHORT" "$BASE_IMG"
out=$(bash $O/am3g-image.sh dev "$SHORT" 2>"$BASE/image.err")
check "image capture prints exactly one line, the image id" "[[ \$(printf '%s\n' '$out' | wc -l) -eq 1 && '$out' =~ ^sha256:[0-9a-f]{64}\$ ]]"
check "IMAGE=\$(am3g-image.sh) is the id itself" "IMAGE=\$(bash $O/am3g-image.sh dev $SHORT 2>/dev/null) && [[ \$IMAGE == $IMG ]]"
check "jobs.log records the image line whole" "grep -q 'image $IMG for $SHORT' $R/ops/jobs.log"
mk_build "$R/overlay-build-vllm-$SHORT" "docker.io/vllm/vllm-openai@sha256:$(printf '0%.0s' $(seq 64))"
out=$(bash $O/am3g-image.sh dev "$SHORT" 2>"$BASE/image2.err"); rc=$?
check "another base image is refused, nothing on stdout" "[[ $rc -ne 0 && -z '$out' ]] && grep -q 'base image pinned' $BASE/image2.err"
mk_build "$R/overlay-build-vllm-$SHORT" "$BASE_IMG" "$(printf '1%.0s' $(seq 40))"
bash $O/am3g-image.sh dev "$SHORT" > /dev/null 2>"$BASE/image3.err"; rc=$?
check "another vLLM commit is refused" "[[ $rc -ne 0 ]] && grep -q 'vLLM commit db9527a4' $BASE/image3.err"
mk_build "$R/overlay-build-vllm-$SHORT" "$BASE_IMG"
printf 'sha256:%s\nextra\n' "${IMG#sha256:}" > "$R/overlay-build-vllm-$SHORT/image-id.txt"
bash $O/am3g-image.sh dev "$SHORT" > /dev/null 2>&1; rc=$?
check "a malformed image-id.txt is refused" "[[ $rc -ne 0 ]]"

# --- build and the one rebuild (minor 1)
rm -rf "$R/overlay-build-vllm-$SHORT"
j1=$(bash $O/am3g-build.sh dev "$SHORT" 2>/dev/null)
check "build submits and prints only its job id" "[[ '$j1' =~ ^[0-9]+\$ ]]"
mk_build "$R/overlay-build-vllm-$SHORT" "$BASE_IMG"
bash $O/am3g-build.sh dev "$SHORT" > /dev/null 2>&1; rc=$?
check "a second 'build' is refused" "[[ $rc -ne 0 ]]"
j2=$(bash $O/am3g-build.sh dev "$SHORT" rebuild 2>/dev/null)
check "the rebuild submits into overlay-build-vllm-$SHORT-r2" "[[ '$j2' =~ ^[0-9]+\$ ]] && grep -q 'COTCODEC_BUILD_ROOT=$R/overlay-build-vllm-$SHORT-r2' $FAKE/stub.log"
mk_build "$R/overlay-build-vllm-$SHORT-r2" "$BASE_IMG"
bash $O/am3g-build.sh dev "$SHORT" rebuild > /dev/null 2>&1; rc=$?
check "a third attempt is refused" "[[ $rc -ne 0 ]]"
bash $O/am3g-image.sh dev "$SHORT" > /dev/null 2>&1 && grep -q "from overlay-build-vllm-$SHORT-r2" "$R/ops/jobs.log"
check "the image is read from the latest attempt (-r2)" "[[ $? -eq 0 ]]"

# --- job state (minor 3)
mkdir -p "$FAKE/stub-jobs"
printf 'JobId=%s JobName=am3g-vllm-overlay\n   JobState=COMPLETED Reason=None Dependency=(null)\n   RunTime=00:01:05 TimeLimit=00:05:00 TimeMin=N/A\n   NumNodes=1 NumCPUs=8\n   TRES=cpu=8,mem=32G,node=1,gres/gpu=1\n   Command=/x\n   WorkDir=/y\n' "$j1" > "$FAKE/stub-jobs/$j1.txt"
bash $O/am3g-job-state.sh dev "$j1" > /dev/null 2>&1; rc=$?
check "job state saves the full scontrol record once the job ends (exit 0)" "[[ $rc -eq 0 ]] && cmp -s $FAKE/stub-jobs/$j1.txt $R/ops/scontrol-$j1.txt"
rm "$FAKE/stub-jobs/$j1.txt"
bash $O/am3g-job-state.sh dev "$j1" > "$BASE/state2.out" 2>&1; rc=$?
check "after scontrol forgets the job, the saved record is printed" "[[ $rc -eq 0 ]] && grep -q 'TRES=cpu=8' $BASE/state2.out"
printf '   JobState=RUNNING Reason=None\n' > "$FAKE/stub-jobs/9999.txt"
bash $O/am3g-job-state.sh dev 9999 > /dev/null 2>&1; rc=$?
check "job state exits 1 while a job runs" "[[ $rc -eq 1 ]]"

# --- selftest and submit refuse a bad image id (major 1)
bash $O/am3g-selftest.sh dev "$SHORT" "$(printf 'x\n%s' "$IMG")" development > /dev/null 2>&1; rc=$?
check "selftest refuses a two-line image id" "[[ $rc -ne 0 ]]"
js=$(bash $O/am3g-selftest.sh dev "$SHORT" "$IMG" development 2>/dev/null)
check "selftest takes a valid image id and prints only its job id" "[[ '$js' =~ ^[0-9]+\$ ]]"
bash $O/am3g-submit.sh dev "$SHORT" "garbage" development check > /dev/null 2>&1; rc=$?
check "submit refuses a malformed image id" "[[ $rc -ne 0 ]]"

# --- submit failure paths (major 2)
A=$FAKE/cotcodec-runs/stage0/am1-study/runs/main/1411; RC=$FAKE/cotcodec-runs/hf-cache/cotcodec-receipts
mkdir -p "$A" "$RC"
cp "$REAL/cotcodec-runs/stage0/am1-study/runs/main/1411/study-artifact.json" "$A/"
mkdir -p "$R/selftest-development-$SHORT"
printf 'image %s population development\nam3g selftest exit 0\nam3g plan exit 0\n' "$IMG" > "$R/selftest-development-$SHORT/exits.txt"
printf '{"revision": "not-a-commit", "artifact_root_sha256": "%s"}\n' "$(printf '0%.0s' $(seq 64))" > "$RC/qwen3-32b.json"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > "$BASE/submit-1.out" 2>&1; rc=$?
check "a failed dry run stops submit before the test-only check and sbatch; no submit record" "[[ $rc -eq 2 && ! -e $R/manifests/development-$SHORT.submit.txt ]] && grep -q 'dry run failed' $BASE/submit-1.out && ! grep -q 'test-only ok' $BASE/submit-1.out && nosub"
cp "$REAL/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json" "$RC/qwen3-32b.json"
touch "$FAKE/stub.testonly-fails"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > "$BASE/submit-2.out" 2>&1; rc=$?
check "a failed test-only check stops submit; no submit record" "[[ $rc -eq 2 && ! -e $R/manifests/development-$SHORT.submit.txt ]] && grep -q 'test-only failed' $BASE/submit-2.out && nosub"
rm -f "$FAKE/stub.testonly-fails"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development check > "$BASE/submit-3.out" 2>&1; rc=$?
check "check runs the dry run and test-only check and submits nothing" "[[ $rc -eq 0 ]] && grep -q 'test-only ok' $BASE/submit-3.out && nosub"
printf 'transcreate-a gres/gpu:h100:2\n' > "$FAKE/stub.squeue"
bash $O/am3g-preflight.sh dev rehearsal 1 > "$BASE/preflight-1.out" 2> "$BASE/preflight-1.err"; rc=$?
check "preflight ignores D110's transcreate-* jobs and prints nothing on stdout" "[[ $rc -eq 0 && ! -s $BASE/preflight-1.out ]] && grep -q '6 of 8 H100 free' $BASE/preflight-1.err"
printf 'am3g-heldout gres/gpu:h100:1\n' >> "$FAKE/stub.squeue"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > "$BASE/submit-pf.out" 2>&1; rc=$?
check "submit refuses while a GPU job of this program is queued or running; no submit record" "[[ $rc -eq 3 && ! -e $R/manifests/development-$SHORT.submit.txt ]] && nosub"
rm -f "$FAKE/stub.squeue"
touch "$FAKE/stub.sbatch-fails"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > "$BASE/submit-4.out" 2>&1; rc=$?
check "a failed sbatch keeps no submit record (the slot is not used); the output is kept as .tmp" "[[ $rc -eq 2 && ! -e $R/manifests/development-$SHORT.submit.txt && -e $R/manifests/development-$SHORT.submit.txt.tmp ]]"
rm -f "$FAKE/stub.sbatch-fails"; touch "$FAKE/stub.sbatch-garbage"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > "$BASE/submit-5.out" 2>&1; rc=$?
check "a submitter output without a job id keeps no submit record" "[[ $rc -eq 2 && ! -e $R/manifests/development-$SHORT.submit.txt ]] && grep -q 'no job id' $BASE/submit-5.out"
rm -f "$FAKE/stub.sbatch-garbage"
J=$(bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit 2>"$BASE/submit-6.err"); rc=$?
check "after those failures, submit succeeds, prints only the job id and records it" "[[ $rc -eq 0 && '$J' =~ ^[0-9]+\$ && \$(tail -1 $R/manifests/development-$SHORT.submit.txt) == '$J' && ! -e $R/manifests/development-$SHORT.submit.txt.tmp ]]"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development submit > /dev/null 2>&1; rc=$?
check "a second submit is refused" "[[ $rc -ne 0 ]]"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development rerun > "$BASE/rerun-1.out" 2>&1; rc=$?
check "rerun is refused without the rerun rule's record (minor 2)" "[[ $rc -ne 0 ]] && grep -q 'does not say rerun' $BASE/rerun-1.out"

# --- the rerun rule on fake job records (major 3, minor 2)
fake_job() {  # $1 job, $2 lane reason, $3 finished_at, $4 hard_stop_at, $5 python dict of the summary
  mkdir -p "$R/runs/development/$1/am3g"
  printf 'reason=%s\nfinished_at=%s\nhard_stop_at=%s\n' "$2" "$3" "$4" > "$R/runs/development/$1/termination.env"
  python3 -c "import json,sys;json.dump($5,open(sys.argv[1],'w'))" "$R/runs/development/$1/am3g/summary.json"
}
decision() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['decision'])" "$R/rerun-decision-development-$1.json" 2>/dev/null; }
fake_job "$J" workload_failed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{'steps':{'rd-qwen3-8b':{'kind':'reader','status':'failed'}},'model_verification':{}}"
bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$J" > /dev/null 2>&1
check "a failed reader step is a rerun" "[[ \$(decision $J) == rerun ]]"
JR=$(bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development rerun 2>"$BASE/rerun-2.err"); rc=$?
check "rerun runs once the rule's record says rerun, and prints only the job id" "[[ $rc -eq 0 && '$JR' =~ ^[0-9]+\$ && \$(tail -1 $R/manifests/development-$SHORT.rerun.txt) == '$JR' ]]"
fake_job "$JR" workload_failed 2026-10-15T12:00:00Z 2026-10-15T13:00:00Z "{'steps':{'rd-qwen3-8b':{'kind':'reader','status':'failed'}},'model_verification':{}}"
bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$JR" > /dev/null 2>&1
check "the rerun's own rerun decision is void (V2)" "[[ \$(decision $JR) == void ]] && grep -q 'V2' $R/rerun-decision-development-$JR.json"
bash $O/am3g-submit.sh dev "$SHORT" "$IMG" development rerun > /dev/null 2>&1; rc=$?
check "a second rerun is refused" "[[ $rc -ne 0 ]]"
fake_job 9601 hard_stop 2026-10-15T11:00:00Z 2026-10-15T11:00:30Z "{'signal':'SIGTERM','steps':{'rd-qwen3-8b':{'kind':'reader','status':'complete'},'rd-olmo2':{'kind':'reader','status':'failed'}},'model_verification':{}}"
fake_job 9602 signal_TERM_checkpoint_confirmed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{'signal':'SIGTERM','steps':{'rd-qwen3-8b':{'kind':'reader','status':'partial','killed':'late'}},'model_verification':{}}"
fake_job 9603 signal_TERM_checkpoint_confirmed 2026-10-15T10:58:00Z 2026-10-15T11:00:00Z "{'signal':'SIGTERM','steps':{'rd-qwen3-8b':{'kind':'reader','status':'partial'}},'model_verification':{}}"
fake_job 9604 completed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{'steps':{'rd-qwen3-8b':{'status':'partial'}},'model_verification':{}}"
fake_job 9605 completed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{'steps':{'rd-qwen3-8b':{'status':'complete'},'rd-olmo2':{'status':'engine-failed'},'rd-olmo2-default':{'status':'complete'},'rd-qwen35-9b-default':{'status':'complete'},'judge32':{'status':'complete'}},'model_verification':{}}"
fake_job 9606 gpu_prolog_unavailable 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{}"
for c in "9601 no-rerun a hard stop on an incomplete job, even with a failed step and a signal" \
         "9602 rerun a signal well before the limit, even with a step stopped late" \
         "9603 no-rerun a signal within 300 s of the hard stop" \
         "9604 no-rerun a step stopped by its time budget" \
         "9605 complete every essential step complete (OLMo-2 by its fallback)" \
         "9606 rerun a job that never started"; do
  read -r j want why <<<"$c"
  bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$j" > /dev/null 2>&1
  check "rerun rule: $why -> $want" "[[ \$(decision $j) == $want ]]"
done
rm -f "$A/study-artifact.json"
echo "rehearsal $SHORT: $pass passed, $fail failed"
