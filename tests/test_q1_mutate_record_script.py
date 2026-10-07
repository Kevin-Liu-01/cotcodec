"""Input validation of the GPU-side specialization recorder (no GPU, no torch)."""

from __future__ import annotations

from scripts import q1_record_specializations as recorder
from tests._q1_mutate_support import make_kernelbench, make_substrates


def test_dry_run_validates_inputs(tmp_path, capsys):
    substrates = make_substrates(tmp_path / "substrates", ["relu_where"])
    kernelbench = make_kernelbench(tmp_path / "kb")
    argv = [
        "--substrates-root",
        str(substrates),
        "--kernelbench-root",
        str(kernelbench),
        "--out-root",
        str(tmp_path / "out"),
        "--dry-run",
    ]
    assert recorder.main(argv) == 0
    assert '"substrates": 1' in capsys.readouterr().out
    assert not (tmp_path / "out").exists()


def test_missing_problem_file_is_refused(tmp_path):
    substrates = make_substrates(tmp_path / "substrates", ["matmul"])
    kernelbench = make_kernelbench(tmp_path / "kb")
    argv = [
        "--substrates-root",
        str(substrates),
        "--kernelbench-root",
        str(kernelbench),
        "--out-root",
        str(tmp_path / "out"),
        "--dry-run",
    ]
    assert recorder.main(argv) == 2
