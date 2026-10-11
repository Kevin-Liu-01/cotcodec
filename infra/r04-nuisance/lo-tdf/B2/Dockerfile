# R04 derived LibreOffice image, build B2: TDF LibreOffice 7.6.7.2 beside the VM's own.
#
# Base: the checker-mutation study's LO-VM image (the OSWorld VM's own userland with its
# Ubuntu LibreOffice 1:7.3.7-0ubuntu0.22.04.4, image sha256:f5b4c40eefd2), named by tag here;
# the R04 host tool refuses to build if the tag names another image and checks afterwards
# that this image's layers extend the base's.
# TDF's deb tarball is fetched from TDF's archive over the build network and checked
# against the size and SHA-256 TDF states for it. Each .deb is unpacked with dpkg-deb -x
# into /opt/libreoffice7.6: the dpkg database is untouched, so no VM package is
# changed or added (dpkg-query before and after must be identical). The menu package
# (desktop entries and /usr/bin links) is not unpacked.
# Rendered by infra/r04-nuisance/render_dockerfiles.py from harness/r04_nuisance/levels.py.
FROM cotcodec-q2-lo-vm:4d5db07d
RUN set -eux; \
    mkdir -p /opt/r04; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-before.tsv; \
    cd /tmp; \
    curl -fsSL --retry 3 -o lo.tar.gz "https://downloadarchive.documentfoundation.org/libreoffice/old/7.6.7.2/deb/x86_64/LibreOffice_7.6.7.2_Linux_x86-64_deb.tar.gz"; \
    test "$(stat -c %s lo.tar.gz)" = "208207432"; \
    echo "5fbd379bd9cedb037fa00b6e7e830619bff503a9451bc321e2b4e8d646081920  lo.tar.gz" | sha256sum -c -; \
    tar -xzf lo.tar.gz; \
    for deb in LibreOffice_*_Linux_x86-64_deb/DEBS/*.deb; do \
      case "$deb" in *debian-menus*) continue ;; esac; \
      dpkg-deb -x "$deb" /; \
    done; \
    rm -rf /tmp/lo.tar.gz /tmp/LibreOffice_*; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-after.tsv; \
    cmp /opt/r04/dpkg-before.tsv /opt/r04/dpkg-after.tsv; \
    chmod -R a+rX /opt/libreoffice7.6; \
    HOME=/tmp/r04-version-home /opt/libreoffice7.6/program/soffice --version > /opt/r04/soffice-version.txt 2>&1; \
    rm -rf /tmp/r04-version-home; \
    grep -q "LibreOffice 7.6.7.2" /opt/r04/soffice-version.txt; \
    (ls -1 /opt/libreoffice7.6/program | grep -i -E "^(python|libpython|pyuno)" || true) > /opt/r04/python.txt; \
    printf '%s\n' "B2" "7.6.7.2" "5fbd379bd9cedb037fa00b6e7e830619bff503a9451bc321e2b4e8d646081920" "208207432" > /opt/r04/build.txt
