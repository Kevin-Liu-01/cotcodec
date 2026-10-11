# R04 derived LibreOffice image, build B4: TDF LibreOffice 25.8.7.3 beside the VM's own.
#
# Base: the checker-mutation study's LO-VM image (the OSWorld VM's own userland with its
# Ubuntu LibreOffice 1:7.3.7-0ubuntu0.22.04.4, image sha256:f5b4c40eefd2), named by tag here;
# the R04 host tool refuses to build if the tag names another image and checks afterwards
# that this image's layers extend the base's.
# TDF's deb tarball is fetched from TDF's archive over the build network and checked
# against the size and SHA-256 TDF states for it. Each .deb is unpacked with dpkg-deb -x
# into /opt/libreoffice25.8: the dpkg database is untouched, so no VM package is
# changed or added (dpkg-query before and after must be identical). The menu package
# (desktop entries and /usr/bin links) is not unpacked.
# Rendered by infra/r04-nuisance/render_dockerfiles.py from harness/r04_nuisance/levels.py.
FROM cotcodec-q2-lo-vm:4d5db07d
RUN set -eux; \
    mkdir -p /opt/r04; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-before.tsv; \
    cd /tmp; \
    curl -fsSL --retry 3 -o lo.tar.gz "https://downloadarchive.documentfoundation.org/libreoffice/old/25.8.7.3/deb/x86_64/LibreOffice_25.8.7.3_Linux_x86-64_deb.tar.gz"; \
    test "$(stat -c %s lo.tar.gz)" = "212886122"; \
    echo "7f4d7b2e36921eec5122c655249a24cc88935ee357e8261fd3bccd15aa1f7b9f  lo.tar.gz" | sha256sum -c -; \
    tar -xzf lo.tar.gz; \
    for deb in LibreOffice_*_Linux_x86-64_deb/DEBS/*.deb; do \
      case "$deb" in *debian-menus*) continue ;; esac; \
      dpkg-deb -x "$deb" /; \
    done; \
    rm -rf /tmp/lo.tar.gz /tmp/LibreOffice_*; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-after.tsv; \
    cmp /opt/r04/dpkg-before.tsv /opt/r04/dpkg-after.tsv; \
    chmod -R a+rX /opt/libreoffice25.8; \
    HOME=/tmp/r04-version-home /opt/libreoffice25.8/program/soffice --version > /opt/r04/soffice-version.txt 2>&1; \
    rm -rf /tmp/r04-version-home; \
    grep -q "LibreOffice 25.8.7.3" /opt/r04/soffice-version.txt; \
    (ls -1 /opt/libreoffice25.8/program | grep -i -E "^(python|libpython|pyuno)" || true) > /opt/r04/python.txt; \
    printf '%s\n' "B4" "25.8.7.3" "7f4d7b2e36921eec5122c655249a24cc88935ee357e8261fd3bccd15aa1f7b9f" "212886122" > /opt/r04/build.txt
