# Userspace tools to read files out of the OSWorld VM disk image without root,
# KVM or a mount: qemu-img dd copies one partition to a sparse raw file and
# debugfs reads ext4 files from it. Probe tool only; not a measurement image.
FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends qemu-utils e2fsprogs fdisk python3 \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}\t${Version}\n' qemu-utils e2fsprogs fdisk python3 > /opt/vmprobe-packages.tsv
