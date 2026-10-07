# LibreOffice reachability image built from the OSWorld VM's own userland.
#
# The VM (HF xlangai/ubuntu_osworld a5d9c3ea, Ubuntu.qcow2 sha256 6bf667a8...)
# runs Ubuntu's LibreOffice 1:7.3.7-0ubuntu0.22.04.4 (buildid 30(Build:2)).
# rootfs/ is that VM's /usr, /etc, dpkg database and LibreOffice user profile,
# copied by infra/q2-mutation/vmprobe/extract_rootfs.py. Two packages are
# added and nothing else may change: xvfb at the VM's X server version
# (2:21.1.4-2ubuntu1.7~22.04.8, same source as the installed xserver-common)
# and openbox, an EWMH window manager so `wmctrl -Fa` works as under GNOME.
# check_dpkg_additions.py fails the build if any installed package changes.
FROM scratch
COPY rootfs/ /
COPY xvfb_21.1.4-2ubuntu1.7~22.04.8_amd64.deb q2-sources.list check_dpkg_additions.py /opt/q2/
RUN set -eux; \
    mkdir -p /tmp /var/tmp /var/log/apt /var/lib/apt/lists/partial /var/cache/apt/archives/partial \
             /var/cache/debconf /var/lib/dpkg/updates; \
    chmod 1777 /tmp /var/tmp; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/q2/dpkg-before.tsv; \
    dpkg -i /opt/q2/xvfb_21.1.4-2ubuntu1.7~22.04.8_amd64.deb; \
    cp /opt/q2/q2-sources.list /etc/apt/sources.list; \
    rm -f /etc/apt/sources.list.d/*; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends --no-upgrade openbox; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/q2/dpkg-after.tsv; \
    python3 /opt/q2/check_dpkg_additions.py /opt/q2/dpkg-before.tsv /opt/q2/dpkg-after.tsv \
      > /opt/q2/dpkg-additions.json; \
    /usr/lib/libreoffice/program/soffice --version > /opt/q2/soffice-version.txt 2>&1 || true
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    PYTHONPATH=/usr/local/lib/python3.10/dist-packages \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
