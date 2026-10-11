# Run (c), the notation sensitivity: `wf_d750e081-ae1`, `claude-opus-5-5`, 12 marker items

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

- `collector-refusal.txt` is the frozen collector's stderr. It maps a transcript only by the bare rendered
  template, so the added D81 sentence makes it refuse, and it wrote nothing.
- `audit_runs.json` is the output of `../../audit_runs.py --suffix-file ../../d81-notation-sentence.txt`:
  12 `ok`, 12 accept.
- `rating-run.json` is the workflow's record, without reasons. The script is copied byte for byte.
