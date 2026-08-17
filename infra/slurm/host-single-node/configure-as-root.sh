#!/usr/bin/env bash
set -euo pipefail

expected_host="fal-h100-01"
expected_version="slurm-wlm 21.08.5"
config_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [[ ${EUID} -ne 0 ]]; then
  echo "run this reviewed bootstrap as root" >&2
  exit 2
fi
if [[ $(hostname) != "$expected_host" ]]; then
  echo "refusing unexpected host: $(hostname)" >&2
  exit 3
fi
if [[ $(/usr/sbin/slurmd -V) != "$expected_version" ]]; then
  echo "refusing unreviewed Slurm version: $(/usr/sbin/slurmd -V)" >&2
  exit 4
fi
if [[ ! -s /etc/munge/munge.key ]]; then
  echo "Munge key is missing" >&2
  exit 5
fi
for index in {0..7}; do
  if [[ ! -c /dev/nvidia${index} ]]; then
    echo "missing NVIDIA device /dev/nvidia${index}" >&2
    exit 6
  fi
done

install -d -m 0755 /etc/slurm
if [[ -e /etc/slurm/slurm.conf ]] && ! cmp -s \
  "$config_dir/slurm.conf" /etc/slurm/slurm.conf; then
  echo "refusing to overwrite a different /etc/slurm/slurm.conf" >&2
  exit 7
fi
if [[ -e /etc/slurm/gres.conf ]] && ! cmp -s \
  "$config_dir/gres.conf" /etc/slurm/gres.conf; then
  echo "refusing to overwrite a different /etc/slurm/gres.conf" >&2
  exit 8
fi

install -o root -g root -m 0644 "$config_dir/slurm.conf" /etc/slurm/slurm.conf
install -o root -g root -m 0644 "$config_dir/gres.conf" /etc/slurm/gres.conf
install -d -o slurm -g slurm -m 0750 /var/spool/slurmctld
install -d -o root -g root -m 0750 /var/spool/slurmd
install -d -o slurm -g slurm -m 0750 /var/log/slurm
touch /var/log/slurm/jobcomp.log
chown slurm:slurm /var/log/slurm/jobcomp.log
chmod 0640 /var/log/slurm/jobcomp.log

systemctl restart munge
systemctl restart slurmctld
systemctl restart slurmd
systemctl --no-pager --full status slurmctld slurmd
