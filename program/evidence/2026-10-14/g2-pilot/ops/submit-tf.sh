#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/cotcodec-runs/stage0/g2-pilot
TF=runs/rollouts-v2/1342/g2/tf-input.json
SHA=$(sha256sum $TF | cut -d" " -f1); SIZE=$(stat -c %s $TF)
G=$(git -C checkout-307fa7ed rev-parse HEAD); SRC=$(sha256sum capsule/source-307fa7ed.tar.gz | cut -d" " -f1)
echo "$SHA $SIZE"
mkdir -p runs/teacher-force
cat > manifests/teacher-force.yaml <<EOF
# G2 pilot (EXPLORATORY), teacher-forcing job. scripts/run_g2_teacher_force.py in the research
# source overlay (torch 2.11, transformers 5.15, FLA 0.5.2) built from the same commit as the
# rollout image (build job 1340). Input: the tf-input.json of rollout job 1342, hash-bound as
# the study artifact. Paths per experiments/g2/g2-pilot-v1.yaml; R3 on seed-42 rollouts only.
# Slurm limit 9 min x 1 H100 = 0.15 GPU-h cap; the driver stops starting work 210 s before it.
runtime: docker-single-node-discovery-v1
name: g2-pilot-teacher-force
image_id: sha256:95bb9a2d6602f743be1f0556e0aa3283de28a3330991f6996a9d66ffc35c080a
git_sha: "$G"
source_sha256: "$SRC"
run_root: /home/kevin/cotcodec-runs/stage0/g2-pilot/runs/teacher-force
container_profile: default
resources:
  gpu_type: h100
  gpus: 1
  cpus: 16
  memory_gb: 96
  minutes: 9
budget:
  max_gpu_hours: 0.15
randomness_contract: deterministic
seeds: []
model:
  cache_host_path: /home/kevin/cotcodec-runs/hf-cache
  model_id: qwen3.5-4b
  revision: "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
  receipt_sha256: "75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082"
  artifact_root_sha256: "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"
study_artifact:
  source_id: g2-pilot-tf-input
  revision: "$G"
  license: MIT
  host_path: /home/kevin/cotcodec-runs/stage0/g2-pilot/$TF
  sha256: "$SHA"
  size_bytes: $SIZE
command:
  - python
  - scripts/run_g2_teacher_force.py
  - run
  - "--evidence"
  - /inputs/study-artifact.json
  - "--expected-evidence-sha256"
  - "$SHA"
  - "--output-dir"
  - /outputs/g2tf
  - "--allocation-minutes"
  - "9"
  - "--r3-rollout-seeds"
  - "42"
EOF
chmod a-w $TF
cd checkout-307fa7ed
uv run --locked python scripts/submit_docker_research_job.py ../manifests/teacher-force.yaml --dry-run > ../manifests/teacher-force.dry-run.json 2>&1 && echo dry ok
uv run --locked python scripts/submit_docker_research_job.py ../manifests/teacher-force.yaml --test-only > ../manifests/teacher-force.test-only.txt 2>&1 && echo test ok
if [[ -z "$(squeue -h -o %j | grep ^ib- || true)" ]]; then
  { echo "== teacher-force at $(date -u +%FT%TZ)"; squeue -h -o "%i %j %T %M"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } >> ../ops/preflight.log
  uv run --locked python scripts/submit_docker_research_job.py ../manifests/teacher-force.yaml > ../manifests/teacher-force.submit.txt 2>&1
  J=$(tail -1 ../manifests/teacher-force.submit.txt); echo "submitted $J"
  echo "$(date -u +%FT%TZ) teacher-force job submitted: $J" >> ../ops/jobs.log
else
  squeue
fi
