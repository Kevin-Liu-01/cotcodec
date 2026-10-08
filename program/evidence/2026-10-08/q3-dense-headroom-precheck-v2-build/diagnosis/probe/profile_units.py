"""CPU profile of v1's per-unit evaluation (harness/dense_headroom_torch.py) on the doctor's
tiny models at realistic context lengths. Diagnostic only; synthetic inputs."""
import cProfile
import io
import os
import pstats
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
LENGTHS = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [2048, 6000]
sys.path.insert(0, str(REPO))
OUT.mkdir(parents=True, exist_ok=True)

from harness import dense_headroom_data as dhd  # noqa: E402

dhd.block_gpu_only_kernels()
import numpy as np  # noqa: E402
import torch  # noqa: E402

from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import dense_headroom_torch as dht  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402
from scripts import run_dense_headroom_precheck_doctor as doctor  # noqa: E402

torch.set_num_threads(int(os.environ.get("PROF_THREADS", "8")))
sit.set_determinism(allow_tf32=True)
names = dhs.selector_names([42, 43, 44])
device = torch.device("cpu")
rng = np.random.default_rng(0)


def unit(vocab, length):
    tokens = rng.integers(3, vocab - 1, size=length + 24).astype(np.uint32)
    tokens[0] = 1
    q0, q1 = length + 2, length + 20
    n0, n1 = length // 3, length // 3 + 120
    options = [rng.integers(3, vocab - 1, size=int(n)).astype(np.uint32) for n in (5, 9, 2, 12)]
    return tokens, q0, q1, n0, n1, options


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    models = {"attention": (doctor.make_tiny_attention(root / "a"), False),
              "hybrid": (doctor.make_tiny_hybrid(root / "h"), True)}
    for kind, (path, hybrid) in models.items():
        model = sit.load_teacher(path, device)
        if hybrid:
            torch.use_deterministic_algorithms(True, warn_only=True)
        else:
            torch.use_deterministic_algorithms(True)
        layers = dht.attention_layers(model.config)
        vocab = int(model.config.vocab_size)
        for length in LENGTHS:
            tokens, q0, q1, n0, n1, options = unit(vocab, length)
            k_blocks = dhd.budget_blocks(length)
            lex = np.zeros(len(tokens) // 4, dtype=np.float32)
            lex[n0 // 4: n0 // 4 + 5] = 2
            kwargs = dict(layers=layers, k_blocks=k_blocks, fixed_k_blocks=256,
                          scaling=dht.scaling_of(model.config), seeds=[42, 43, 44],
                          unit_key="c0-q0", names=names, hybrid=hybrid, device=device,
                          options=options, option_bytes=[5, 9, 2, 12], answer=1, lex_blocks=lex)
            dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=True, do_mc=True, **kwargs)
            timings = {}
            for label, sel, mc in (("select_only", True, False), ("mc_only", False, True),
                                   ("both", True, True)):
                t0 = time.perf_counter()
                for _ in range(3):
                    dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=sel, do_mc=mc,
                                      **kwargs)
                timings[label] = (time.perf_counter() - t0) / 3
            prof = cProfile.Profile()
            prof.enable()
            dht.evaluate_unit(model, tokens, q0, q1, n0, n1, do_select=True, do_mc=True,
                              **kwargs)
            prof.disable()
            s = io.StringIO()
            st = pstats.Stats(prof, stream=s)
            st.sort_stats("tottime").print_stats(25)
            st.sort_stats("cumulative").print_stats(40)
            (OUT / f"{kind}-L{length}.txt").write_text(s.getvalue())
            print(kind, length, {k: round(v, 3) for k, v in timings.items()}, flush=True)
