#!/usr/bin/env bash
# am3-nonabstain-generality-v1, pre-freeze checks 2 and 3: a rehearsal of section 16's operator
# scripts on the host under a fake HOME, with sbatch, scontrol, squeue and nvidia-smi stubbed on
# PATH, and, for the Mac's labelling script, ssh and scp (to the fake HOME) and the claude CLI (its
# authentication failure). No job is submitted, no GPU is used, no model runs, and no held-out or
# abstention input is opened: the scripts run in dev mode against copies of the development
# artifact and features, job 1471's run directory (linked, read only), and fake build, selftest,
# job and labeller records (the "subagent" transcripts are written by this script). The fake HOME
# sits under ~/cotcodec-runs so the lane submitter's run-root check passes. Each case prints PASS
# or FAIL; the copied artifact and features are removed at the end.
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
cat > "$BASE/bin/ssh" <<'EOF'
#!/usr/bin/env bash
shift; cd "$HOME" && bash -c "$*"
EOF
cat > "$BASE/bin/scp" <<'EOF'
#!/usr/bin/env bash
args=()
for a in "$@"; do [[ "$a" == -q ]] && continue; args+=("${a/#fal-h100-01:/$HOME/}"); done
cp "${args[@]}"
EOF
cat > "$BASE/bin/claude" <<'EOF'
#!/usr/bin/env bash
echo '{"type":"system","subtype":"init","model":"claude-opus-5-5","session_id":"s0"}'
echo '{"type":"assistant","message":{"model":"<synthetic>","content":[{"type":"text","text":"Invalid API key"}]}}'
echo '{"type":"result","subtype":"success","is_error":true,"result":"Invalid API key","api_error_status":401}'
exit 1
EOF
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
check "build submits, prints only its job id and records the attempt" "[[ '$j1' =~ ^[0-9]+\$ && \$(cat $R/ops/build-attempts-$SHORT.txt) == '$j1' ]]"
# The build fails before its build root exists (no mk_build here).
bash $O/am3g-build.sh dev "$SHORT" > /dev/null 2>&1; rc=$?
check "a second 'build' is refused although the failed build left no build root (check 3)" "[[ $rc -ne 0 && ! -e $R/overlay-build-vllm-$SHORT ]]"
j2=$(bash $O/am3g-build.sh dev "$SHORT" rebuild 2>/dev/null)
check "the rebuild after a build that failed before its root existed submits into -r2" "[[ '$j2' =~ ^[0-9]+\$ ]] && grep -q 'COTCODEC_BUILD_ROOT=$R/overlay-build-vllm-$SHORT-r2' $FAKE/stub.log"
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
printf '   JobState=REQUEUED Reason=None\n' > "$FAKE/stub-jobs/9998.txt"
bash $O/am3g-job-state.sh dev 9998 > /dev/null 2>&1; rc=$?
check "job state treats a state that is not terminal as running (exit 1, no record)" "[[ $rc -eq 1 && ! -e $R/ops/scontrol-9998.txt ]]"

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
  printf 'JobId=%s\n   JobState=COMPLETED\n' "$1" > "$R/ops/scontrol-$1.txt"
  printf 'reason=%s\nfinished_at=%s\nhard_stop_at=%s\n' "$2" "$3" "$4" > "$R/runs/development/$1/termination.env"
  python3 -c "import json,sys;json.dump($5,open(sys.argv[1],'w'))" "$R/runs/development/$1/am3g/summary.json"
}
decision() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['decision'])" "$R/rerun-decision-development-$1.json" 2>/dev/null; }
mkdir -p "$R/runs/development/$J/am3g"
python3 -c "import json,sys;json.dump({'steps':{}},open(sys.argv[1],'w'))" "$R/runs/development/$J/am3g/summary.json"
bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$J" > /dev/null 2>&1; rc=$?
check "rerun-decision refuses a job that has not ended (no scontrol record, no termination.env), and writes nothing (check 3)" "[[ $rc -eq 2 && ! -e $R/rerun-decision-development-$J.json && ! -e $R/rerun-decision-development-$J.json.tmp ]]"
fake_job "$J" workload_failed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "{'steps':{'rd-qwen3-8b':{'kind':'reader','status':'failed'}},'model_verification':{}}"
bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$J" > /dev/null 2>&1
check "a failed reader step is a rerun" "[[ \$(decision $J) == rerun ]]"
h0=$(sha256sum "$R/rerun-decision-development-$J.json")
bash $O/am3g-rerun-decision.sh dev "$SHORT" development "$J" > /dev/null 2>&1; rc=$?
check "a repeated rerun-decision is refused and leaves the record unchanged" "[[ $rc -eq 2 && \$(sha256sum $R/rerun-decision-development-$J.json) == '$h0' ]]"
fake_job 9607 workload_failed 2026-10-15T10:00:00Z 2026-10-15T11:00:00Z "[1, 2]"
bash $O/am3g-rerun-decision.sh dev "$SHORT" development 9607 > "$BASE/decision-9607.out" 2>&1; rc=$?
check "a summary that is not a JSON object is a named V2 error with no record" "[[ $rc -ne 0 && ! -e $R/rerun-decision-development-9607.json ]] && grep -q 'V2, incomplete.*not a JSON object' $BASE/decision-9607.out"
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

# --- the blind hand check's records and the Mac's labelling script (check 3: major 1, minors 3, 5, 8)
mkdir -p "$R/private" "$R/runs/development"
cp "$REAL_R/private/features-development.json.gz" "$R/private/"
ln -s "$REAL_R/runs/development/1471" "$R/runs/development/1471"
bash $O/am3g-hand-sample.sh dev "$SHORT" 1471 > /dev/null 2>&1; rc=$?
check "hand-sample draws the development sample" "[[ $rc -eq 0 && -s $R/hand-sample-$SHORT.json && -f $R/hand/hand-first-chunk-01.jsonl ]]"
h0=$(sha256sum "$R/hand-sample-$SHORT.json")
bash $O/am3g-hand-sample.sh dev "$SHORT" 1471 > /dev/null 2>&1; rc=$?
check "a repeated hand-sample is refused and leaves its record unchanged" "[[ $rc -eq 2 && \$(sha256sum $R/hand-sample-$SHORT.json) == '$h0' ]]"
fake_subagent() {  # $1 stage dir on the "Mac", $2 chunk NN, $3 transcript path, $4 agent id
  python3 - "$1" "$2" "$3" "$4" <<'PY'
import datetime, json, sys
s, nn, out, agent = sys.argv[1:]
d = [l.split(None, 1)[1].strip() for l in open(f"{s}/chunk-dirs.txt") if l.split()[0] == nn][0]
chunk, output = [l.split() for l in open(f"{s}/chunks.txt")][int(nn) - 1]
now = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
common = {"agentId": agent, "sessionId": "rehearsal"}
lines = [{"type": "user", "message": {"role": "user", "content": open(f"{s}/prompt-{nn}-abs.txt").read()}}]
for k, (name, target) in enumerate([("Read", "hand-check-instructions.txt"), ("Read", chunk), ("Write", output)]):
    lines.append({"type": "assistant", "message": {"model": "claude-opus-5-5", "content": [
        {"type": "tool_use", "id": f"t{k}", "name": name, "input": {"file_path": f"{d}/{target}"}}]}})
    lines.append({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": f"t{k}", "content": "ok"}]}})
ids = [json.loads(l)["item_id"] for l in open(f"{d}/{chunk}") if l.strip()]
open(f"{d}/{output}", "w").write("".join(json.dumps({"item_id": i, "label": 1, "note": ""}) + "\n" for i in ids))
with open(out, "w") as handle:
    for entry in lines:
        handle.write(json.dumps({**entry, **common, "timestamp": now()}) + "\n")
PY
}
MAC=$BASE/mac; mkdir -p "$MAC/session-a/subagents" "$MAC/session-b/subagents"
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w1" cli > "$BASE/label-1.out" 2>&1; rc=$?
check "the CLI launch claims the stage, meets the CLI's authentication failure and stops with exit 3" "[[ $rc -eq 3 && -d $R/hand/claim-first && -f $MAC/w1/first/cli-failed-at.txt ]] && grep -q 'hand stage first claimed' $R/ops/jobs.log"
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w2" prepare > "$BASE/label-2.out" 2>&1; rc=$?
check "a stage already claimed is refused, from another work directory too" "[[ $rc -eq 2 && ! -e $MAC/w2/first ]] && grep -q 'already claimed' $BASE/label-2.out"
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w1" push cli > /dev/null 2>&1; rc=$?
check "a CLI push outside the cli action is refused" "[[ $rc -eq 2 && ! -e $R/hand/labeller-first.json ]]"
sleep 1
fake_subagent "$MAC/w1/first" 01 "$MAC/session-a/subagents/agent-ra1.jsonl" ra1
printf '{"type":"user","message":{"role":"user","content":"another task"},"agentId":"rz9"}\n' > "$MAC/session-a/subagents/agent-rz9.jsonl"
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w1" push subagent "$MAC/session-a/subagents" > "$BASE/label-3.out" 2>&1; rc=$?
check "the subagent push finds one transcript for the chunk, copies it unmodified and records the attempts" "[[ $rc -eq 0 ]] && cmp -s $MAC/session-a/subagents/agent-ra1.jsonl $R/hand/transcripts/first-01.jsonl && python3 -c \"import json,sys;d=json.load(open('$R/hand/labeller-first.json'));sys.exit(not (d['attempts']=={'01':1} and d['agents']=={'01':'ra1'} and d['subagent_transcripts_scanned']==2))\""
bash $O/am3g-hand-merge.sh dev "$SHORT" first > "$BASE/merge-1.out" 2>&1; rc=$?
check "the merge audits the transcript (model, prompt, agent id, paths, times) and writes the final labels" "[[ $rc -eq 0 ]] && python3 -c \"import json,sys;d=json.load(open('$R/hand-merge-first-$SHORT.json'));a=list(d['transcript_audit'].values())[0];sys.exit(not (a['pass'] and d['final_complete'] and d['labelling_attempts']==1 and a['agent_ids']==['ra1']))\""
h0=$(sha256sum "$R/hand-merge-first-$SHORT.json")
bash $O/am3g-hand-merge.sh dev "$SHORT" first > /dev/null 2>&1; rc=$?
check "a repeated hand-merge is refused and leaves its record unchanged" "[[ $rc -eq 2 && \$(sha256sum $R/hand-merge-first-$SHORT.json) == '$h0' ]]"
check "the transcripts' digest list is read-only after the merge" "[[ ! -w $R/hand/transcripts-first.sha256 ]]"
bash $O/am3g-hand-receipt.sh dev "$SHORT" first > /dev/null 2>&1; rc=$?
check "the receipt records the launch, attempts and agent ids, and carries the records staging copies" "[[ $rc -eq 0 && -f $R/hand-check/hand-sample-$SHORT.json && -f $R/hand-check/hand-merge-first-$SHORT.json && -f $R/hand-check/hand-manifest.json ]] && python3 -c \"import json,sys;d=json.load(open('$R/hand-check/hand-receipt-first.json'));sys.exit(not (d['labeller_launch']=='subagent' and d['labelling_attempts']=={'01':1} and d['chunks'][0]['agent_ids']==['ra1'] and d['cli_error_sha256']))\""
# An extra labelling attempt: a fresh hand directory, two transcripts with the chunk's prompt.
mkdir -p "$BASE/set-aside"; mv "$R/hand" "$R/hand-check" "$R/hand-sample-$SHORT.json" "$R/hand-merge-first-$SHORT.json" "$BASE/set-aside/"
bash $O/am3g-hand-sample.sh dev "$SHORT" 1471 > /dev/null 2>&1
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w3" cli > /dev/null 2>&1
sleep 1
fake_subagent "$MAC/w3/first" 01 "$MAC/session-b/subagents/agent-rb1.jsonl" rb1
fake_subagent "$MAC/w3/first" 01 "$MAC/session-b/subagents/agent-rb2.jsonl" rb2
bash $O/am3g-hand-label-mac.sh dev "$SHORT" first "$MAC/w3" push subagent "$MAC/session-b/subagents" > "$BASE/label-4.out" 2>&1
bash $O/am3g-hand-merge.sh dev "$SHORT" first > "$BASE/merge-2.out" 2>&1; rc=$?
check "an extra transcript is visible (2 attempts for chunk 01) and voids the hand check: empty final labels, no repair" "[[ $rc -eq 0 && ! -s $R/hand/hand-labels.jsonl && ! -e $R/hand/hand-repair-sample.jsonl ]] && python3 -c \"import json,sys;d=json.load(open('$R/hand-merge-first-$SHORT.json'));sys.exit(not (d['void'] and d['labelling_attempts']==2))\""
bash $O/am3g-hand-receipt.sh dev "$SHORT" first > /dev/null 2>&1; rc=$?
check "the receipt of the void stage records it" "[[ $rc -eq 0 ]] && python3 -c \"import json,sys;d=json.load(open('$R/hand-check/hand-receipt-first.json'));sys.exit(not (d['void'] and d['labelling_attempts']=={'01':2} and d['matching_subagent_transcripts']==2))\""
rm -f "$A/study-artifact.json" "$R/private/features-development.json.gz"
echo "rehearsal $SHORT: $pass passed, $fail failed"
