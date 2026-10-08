# Pinned CPU container for the S1a secondary model (q2-stage1-rescoped-v1, G0 item 12).
#
# rocker/r-ver 4.4.2 (amd64 manifest of the tag's index digest below) sets its CRAN mirror to a
# dated Posit Package Manager snapshot, so install2.r resolves the same package versions on
# any build day; the built image is kept by ID and its package versions are written into
# /opt/q2/r-packages.json (the lock). It runs GPU-less with --network=none (D12, D13).
FROM rocker/r-ver:4.4.2@sha256:df26749182af64d5263bf64149d51a427b476ed28c4e046997143be3f97fdd7c
RUN install2.r --error --skipinstalled --ncpus 4 glmmTMB jsonlite \
 && rm -rf /tmp/downloaded_packages
RUN mkdir -p /opt/q2 \
 && Rscript -e 'ip <- installed.packages(fields = "Repository"); \
      repos <- getOption("repos"); \
      out <- list(R = R.version.string, repos = as.list(repos), \
                  packages = setNames(as.list(ip[, "Version"]), ip[, "Package"])); \
      writeLines(jsonlite::toJSON(out, auto_unbox = TRUE, pretty = TRUE), "/opt/q2/r-packages.json")' \
 && sha256sum /opt/q2/r-packages.json > /opt/q2/r-packages.sha256
ENV HOME=/tmp/home
