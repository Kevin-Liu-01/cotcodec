# Metric-image venv fingerprints

`score.sh` copies `/opt/q2/venv-{lock,scout}.fingerprint.json` into every
scoring job's output directory. The copies written by Slurm 781 (confirm
controls, raw), 791 (reserve controls, raw) and 796 (confirm mutants) are
byte-identical, so one copy is kept here:

| File | SHA-256 | `fingerprint_sha256` (pinned, prereg section 2) |
|---|---|---|
| `venv-lock.fingerprint.json` | `52ebb24c53776476d6c65ac172048bfe7804b186c1e2000134e136ee7be99a9a` | `f2c9e208d2bdb888668e64143f0603ce92f56cee2fd1002f0211d2c2287db810` |
| `venv-scout.fingerprint.json` | `60d135ab934990cac32cffec28dbfa2ecb9db36ccf6a259cf53264dba808c718` | `e591c8875c353ecbf6ec38b6c9c467e01b4164cc129744bd51e27c993310417a` |
