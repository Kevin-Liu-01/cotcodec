# R04 derived LibreOffice image, build B5: TDF LibreOffice 26.2.6.2 beside the VM's own.
#
# Base: the checker-mutation study's LO-VM image (the OSWorld VM's own userland with its
# Ubuntu LibreOffice 1:7.3.7-0ubuntu0.22.04.4, image sha256:f5b4c40eefd2), named by tag here;
# the R04 host tool refuses to build if the tag names another image and checks afterwards
# that this image's layers extend the base's.
# TDF's deb tarball is fetched from TDF's archive over the build network and checked
# against the size and SHA-256 TDF states for it. Each .deb is unpacked with dpkg-deb -x
# into /opt/libreoffice26.2: the dpkg database is untouched, so no VM package is
# changed or added (dpkg-query before and after must be identical). The menu package
# (desktop entries and /usr/bin links) is not unpacked.
# Rendered by infra/r04-nuisance/render_dockerfiles.py from harness/r04_nuisance/levels.py.
FROM cotcodec-q2-lo-vm:4d5db07d
RUN set -eux; \
    mkdir -p /opt/r04; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-before.tsv; \
    cd /tmp; \
    curl -fsSL --retry 3 -o lo.tar.gz "https://downloadarchive.documentfoundation.org/libreoffice/old/26.2.6.2/deb/x86_64/LibreOffice_26.2.6.2_Linux_x86-64_deb.tar.gz"; \
    test "$(stat -c %s lo.tar.gz)" = "217261547"; \
    echo "ae25483b9c1b56ed156fb2398c85ce97e65048bc0bbcc079934cc1d2e0c11242  lo.tar.gz" | sha256sum -c -; \
    tar -xzf lo.tar.gz; \
    for deb in LibreOffice_*_Linux_x86-64_deb/DEBS/*.deb; do \
      case "$deb" in *debian-menus*) continue ;; esac; \
      dpkg-deb -x "$deb" /; \
    done; \
    rm -rf /tmp/lo.tar.gz /tmp/LibreOffice_*; \
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' > /opt/r04/dpkg-after.tsv; \
    cmp /opt/r04/dpkg-before.tsv /opt/r04/dpkg-after.tsv; \
    chmod -R a+rX /opt/libreoffice26.2; \
    HOME=/tmp/r04-version-home /opt/libreoffice26.2/program/soffice --version > /opt/r04/soffice-version.txt 2>&1; \
    rm -rf /tmp/r04-version-home; \
    grep -q "LibreOffice 26.2.6.2" /opt/r04/soffice-version.txt; \
    (ls -1 /opt/libreoffice26.2/program | grep -i -E "^(python|libpython|pyuno)" || true) > /opt/r04/python.txt; \
    printf '%s\n' "B5" "26.2.6.2" "ae25483b9c1b56ed156fb2398c85ce97e65048bc0bbcc079934cc1d2e0c11242" "217261547" > /opt/r04/build.txt
