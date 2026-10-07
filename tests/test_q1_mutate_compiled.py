"""Compiled-specialization dedup hook.

The pure-Python parts run everywhere. ``test_cpu_compile_*`` needs Triton and
runs only inside a GPU-less research container (it compiles for sm_90 without
a device and never launches anything).
"""

from __future__ import annotations

import json

import pytest

from harness.q1.mutate import compiled
from tests._q1_mutate_support import toy_text


def test_launch_scope_hash_ignores_device_bodies_only():
    text = toy_text("relu_where")
    device_change = text.replace("y = tl.where(x > 0, x, 0.0)", "y = x")
    launch_change = text.replace("BLOCK_SIZE=1024)", "BLOCK_SIZE=512)")
    assert compiled.launch_scope_hash(text) == compiled.launch_scope_hash(device_change)
    assert compiled.launch_scope_hash(text) != compiled.launch_scope_hash(launch_change)


def test_compiled_key_is_order_independent():
    a = compiled.compiled_key({"k": ["2", "1"], "j": ["3"]}, "L")
    b = compiled.compiled_key({"j": ["3"], "k": ["1", "2"]}, "L")
    assert a == b
    assert a != compiled.compiled_key({"k": ["1", "2"], "j": ["3"]}, "M")


def test_classify_statuses():
    text = toy_text("relu_where")
    launch = compiled.launch_scope_hash(text)
    parent_key = compiled.compiled_key({"relu_kernel": ["p"]}, launch)
    seen: dict[str, str] = {}
    assert compiled.classify(parent_key, text, None, seen, "m0") == ("compile-fail", None)
    assert compiled.classify(parent_key, text, {"relu_kernel": ["p"]}, seen, "m1")[0] == (
        "equivalent-to-parent"
    )
    assert compiled.classify(parent_key, text, {"relu_kernel": ["x"]}, seen, "m2")[0] == "distinct"
    assert compiled.classify(parent_key, text, {"relu_kernel": ["x"]}, seen, "m3")[0] == "duplicate"
    launch_only = text.replace("BLOCK_SIZE=1024)", "BLOCK_SIZE=512)")
    assert compiled.classify(parent_key, launch_only, {"relu_kernel": ["p"]}, seen, "m4")[0] == (
        "distinct"
    )


def test_specialization_file_validation(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(
        json.dumps(
            {
                "schema": compiled.SPEC_SCHEMA,
                "records": [{"function": "relu_kernel", "specialization_data": "{}"}],
            }
        )
    )
    assert compiled.load_specializations(good)[0].function == "relu_kernel"
    for bad in (
        {"schema": "other", "records": []},
        {"schema": compiled.SPEC_SCHEMA, "records": []},
        {"schema": compiled.SPEC_SCHEMA, "records": [{"function": "f"}]},
    ):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(compiled.CompileHookError):
            compiled.load_specializations(path)


def test_compile_requires_line_info_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("TRITON_DISABLE_LINE_INFO", raising=False)
    with pytest.raises(compiled.CompileHookError, match="TRITON_DISABLE_LINE_INFO"):
        compiled.compile_hashes(tmp_path / "kernel.py", [])


def _relu_record() -> compiled.Specialization:
    """A record in Triton 3.6's serialized form, built without a device."""
    from triton.backends.compiler import GPUTarget
    from triton.compiler.compiler import make_backend
    from triton.runtime.jit import serialize_specialization_data

    backend = make_backend(GPUTarget(*compiled.DEFAULT_TARGET))
    options = backend.parse_options({"num_warps": 4, "num_stages": 3})
    signature = {"x_ptr": "*fp32", "y_ptr": "*fp32", "n_elements": "i32", "BLOCK_SIZE": "constexpr"}
    constants = {(3,): 1024}
    attrs = {
        (0,): [["tt.divisibility", 16]],
        (1,): [["tt.divisibility", 16]],
        (2,): [["tt.divisibility", 16]],
    }
    data = serialize_specialization_data("relu_kernel", signature, constants, attrs, options, "k")
    return compiled.Specialization("relu_kernel", data)


def test_cpu_compile_separates_mutants_and_merges_equivalents(tmp_path, monkeypatch):
    pytest.importorskip("triton")
    monkeypatch.setenv("TRITON_DISABLE_LINE_INFO", "1")
    monkeypatch.setenv("TRITON_CACHE_DIR", str(tmp_path / "cache"))
    text = toy_text("relu_where")
    variants = {
        "parent": text,
        "reformatted": text.replace(
            "mask = offsets < n_elements", "mask = n_elements > offsets  # flipped"
        ),
        "lt2le": text.replace("mask = offsets < n_elements", "mask = offsets <= n_elements"),
        "relu_removed": text.replace("y = tl.where(x > 0, x, 0.0)", "y = x"),
    }
    record = _relu_record()
    hashes = {}
    for name, source in variants.items():
        path = tmp_path / f"{name}.py"
        path.write_text(source)
        hashes[name] = compiled.compile_hashes(path, [record])["relu_kernel"]
    assert hashes["parent"] == hashes["reformatted"]
    assert hashes["lt2le"] != hashes["parent"]
    assert hashes["relu_removed"] != hashes["parent"]


def test_cpu_compile_cli_reports_errors_per_kernel(tmp_path, monkeypatch, capsys):
    pytest.importorskip("triton")
    monkeypatch.setenv("TRITON_DISABLE_LINE_INFO", "1")
    monkeypatch.setenv("TRITON_CACHE_DIR", str(tmp_path / "cache"))
    spec = tmp_path / "specializations.json"
    spec.write_text(compiled.dump_specializations([_relu_record()], "3.6.0"))
    good = tmp_path / "good.py"
    good.write_text(toy_text("relu_where"))
    bad = tmp_path / "bad.py"
    bad.write_text(
        toy_text("relu_where").replace(
            "block_start = pid * BLOCK_SIZE", "block_start = pid / BLOCK_SIZE"
        )
    )
    assert compiled.main(["--spec", str(spec), "--kernels", str(good), str(bad)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert "hashes" in rows[0] and "error" in rows[1]
