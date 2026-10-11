# Controls

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

`controls.json` holds the SHA-256 of what each control produced next to the committed file it
reproduces. All three are byte-identical, run from the same archive (`65bc2e2`) and interpreter:

1. `audit summarize` without `--adjudications` reproduces the 2026-10-08 audit summary (four files).
2. The pre-adjudication analysis with `--k2-report` reproduces the K2 rerun's `analysis.json` and stdout.
3. The same without `--k2-report` reproduces the 2026-10-08 `analysis.json` and stdout.

The produced copies are identical to the committed files, so they are not duplicated here.
