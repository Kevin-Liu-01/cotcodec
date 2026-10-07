"""Operator catalog, planning, label rules and simulated purity on synthetic documents.

The office appliers need LibreOffice, so these tests build the document an
operator should produce with the synthetic builders and check that the purity
oracle admits it, and that it rejects tampered variants. The real UNO path is
exercised by ``harness.q2_mutation.operators.validate`` in the LO container.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

import pytest

from harness.q2_mutation.operators import _synth as synth
from harness.q2_mutation.operators import catalog, registry
from harness.q2_mutation.operators._base import Context, plan_operator
from harness.q2_mutation.operators._purity import Expectation, admitted, check
from harness.q2_mutation.operators._snapshot import snapshot
from harness.q2_mutation.operators.pipeline import (
    apply_text_records,
    is_admitted,
    make_context,
    plan_task,
    verify,
)
from harness.q2_mutation.schema import LABELS, MutationResult, RequirementSpec, SchemaError

OPS_DIR = Path(__file__).resolve().parents[1] / "harness" / "q2_mutation" / "operators"


def _spec(kind: str, **changes) -> RequirementSpec:
    data = synth.synthetic_spec(kind)
    data.update(changes)
    return RequirementSpec.from_dict(data)


def _ctx(tmp_path: Path, kind: str, spec: RequirementSpec | None = None) -> Context:
    spec = spec or _spec(kind)
    if kind == "xlsx":
        base = synth.build_xlsx(tmp_path / "gold.xlsx")
        initial = synth.build_xlsx(tmp_path / "init.xlsx", drop=("Data!D5", "Data!B6", "Data!B7"))
    elif kind == "docx":
        base = synth.build_docx(tmp_path / "gold.docx")
        initial = synth.build_docx(tmp_path / "init.docx", blocks=synth.DEFAULT_DOCX[1:])
    elif kind == "pptx":
        base = synth.build_pptx(tmp_path / "gold.pptx")
        initial = None
    else:
        raise ValueError(kind)
    return make_context(spec.task_id, spec, base, initial)


def _one(ctx: Context, name: str, unit: str | None = None) -> dict:
    planned, _skips = plan_operator(registry()[name](), ctx)
    records = [p.record for p in planned]
    if unit is not None:
        records = [r for r in records if r["recipe"]["params"]["site"]["unit"] == unit]
    assert records, f"{name} planned nothing"
    return records[0]


def _expectation(record: dict) -> Expectation:
    return Expectation.from_dict(record["recipe"]["params"]["expectation"])


# --------------------------------------------------------------------------- catalog


def test_catalog_covers_labels_and_families() -> None:
    cat = catalog()
    names = [e["name"] for e in cat["operators"]]
    assert len(names) == len(set(names)) >= 40
    for family in ("xlsx", "docx", "pptx"):
        classes = set(cat["counts"][family])
        assert classes == {
            "should_pass_equiv", "should_pass_alt_solution", "should_fail_violation",
            "should_fail_extra_change",
        }
    for entry in cat["operators"]:
        assert entry["label_class"] in LABELS and entry["label_class"] != "ambiguous"
        assert entry["target"] in {"requirement", "outside", "document"}
        assert entry["description"]
        assert entry["stratum"] == "document_model"
        assert re.fullmatch(r"(xlsx|docx|pptx|text|config)\.(eq|alt|viol|extra)\.[a-z_]+",
                            entry["name"])
    assert catalog()["catalog_sha256"] == cat["catalog_sha256"]


def test_uno_applier_is_self_contained_and_python38_compatible() -> None:
    source = (OPS_DIR / "uno_apply.py").read_text()
    tree = ast.parse(source, feature_version=(3, 8))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert "harness" not in imported
    assert imported <= {
        "__future__", "argparse", "contextlib", "hashlib", "json", "os", "shutil", "signal",
        "subprocess", "sys", "tempfile", "threading", "time", "traceback", "uno", "com",
    }


def test_every_planned_step_has_an_applier(tmp_path: Path) -> None:
    uno_source = (OPS_DIR / "uno_apply.py").read_text()
    text_source = (OPS_DIR / "apply_text.py").read_text()
    ops = set()
    for kind in ("xlsx", "docx", "pptx"):
        records, _ = plan_task(_ctx(tmp_path / kind, kind))
        for record in records:
            ops.update(step["op"] for step in record["recipe"]["params"]["steps"])
    assert ops
    for op in ops:
        assert f'"{op}"' in uno_source, op
    for op in ("text.splice", "text.set_trailing_newline", "json.reformat", "json.reorder",
               "ini.respace"):
        assert f'"{op}"' in text_source


# --------------------------------------------------------------------------- planning


def test_planning_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    for kind in ("xlsx", "docx", "pptx"):
        first, _ = plan_task(_ctx(tmp_path / f"a-{kind}", kind))
        second, _ = plan_task(_ctx(tmp_path / f"b-{kind}", kind))
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        per_op: dict[str, list[int]] = {}
        for record in first:
            parsed = MutationResult.from_dict(record)
            assert parsed.stratum == "document_model"
            assert parsed.witness.argument.startswith("W-")
            per_op.setdefault(record["operator"], []).append(record["recipe"]["seed"])
            if record["label"] == "should_fail_violation":
                assert set(parsed.witness.req_ids) <= {r.req_id for r in _spec(kind).requirements}
        for seeds in per_op.values():
            assert len(seeds) <= 3 and seeds == [42, 43, 44][: len(seeds)]


def test_tampered_recipe_breaks_the_mutant_id(tmp_path: Path) -> None:
    record = _one(_ctx(tmp_path, "xlsx"), "xlsx.viol.value_perturb")
    tampered = copy.deepcopy(record)
    tampered["recipe"]["params"]["steps"][0]["value"] = ["n", 999.0]
    with pytest.raises(SchemaError, match="mutant_id"):
        MutationResult.from_dict(tampered)


def test_recipes_carry_digests_not_document_text(tmp_path: Path) -> None:
    records, _ = plan_task(_ctx(tmp_path, "docx"))
    for record in records:
        for step in record["recipe"]["params"]["steps"]:
            assert "expect_text" not in step
            if step["op"] not in {"doc.set_property", "docx.set_view"}:
                assert re.fullmatch(r"[0-9a-f]{64}", step["expect_sha256"])


# --------------------------------------------------------------------------- label rules


def test_literal_for_formula_label_follows_the_spec(tmp_path: Path) -> None:
    def label(statement: str, allowed: list[str]) -> str:
        spec = _spec(
            "xlsx",
            requirements=[{"req_id": "R1", "statement": statement, "check_kind": "cell_value",
                           "observable": "Read Data!D5; it equals 13."}],
            allowed_variations=allowed,
        )
        record = _one(_ctx(tmp_path / str(len(statement) + len(allowed)), "xlsx", spec),
                      "xlsx.alt.literal_for_formula")
        return record["label"]

    assert label("D5 holds the grand total of D2:D4.", []) == "should_pass_alt_solution"
    assert label("Use a formula in D5 to total D2:D4.", []) == "should_fail_violation"
    assert label("D5 is a formula total of D2:D4.", []) == "ambiguous"
    assert label("Use a formula in D5 to total D2:D4.",
                 ["whether the total is a formula or a typed value"]) == "should_pass_alt_solution"


def test_equivalence_and_extra_labels_follow_the_spec(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path / "a", "xlsx")
    assert _one(ctx, "xlsx.eq.view_zoom")["label"] == "should_pass_equiv"
    zoom_spec = _spec("xlsx", allowed_variations=[])
    reqs = [r.to_dict() for r in zoom_spec.requirements]
    reqs[0]["statement"] += " Keep the zoom at 100%."
    ctx_zoom = _ctx(tmp_path / "b", "xlsx", _spec("xlsx", requirements=reqs))
    assert _one(ctx_zoom, "xlsx.eq.view_zoom")["label"] == "ambiguous"
    assert _one(ctx, "xlsx.extra.format_unrelated_cell")["label"] == "ambiguous"
    ctx_fmt = _ctx(tmp_path / "c", "xlsx",
                   _spec("xlsx", allowed_variations=["bold or colour of other cells"]))
    assert _one(ctx_fmt, "xlsx.extra.format_unrelated_cell")["label"] == "should_pass_equiv"
    assert _one(ctx, "xlsx.extra.edit_unrelated_value")["label"] == "should_fail_extra_change"


def test_outside_sites_avoid_bound_and_delta_units(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "xlsx")
    planned, _ = plan_operator(registry()["xlsx.extra.edit_unrelated_value"](), ctx)
    for p in planned:
        unit = p.record["recipe"]["params"]["site"]["unit"]
        assert ctx.is_outside(unit)
        assert not unit.endswith(("/B2", "/B3", "/B4", "/C2", "/C3", "/C4"))  # feed bound cells


# --------------------------------------------------------------------------- simulated purity


def test_value_perturb_mutant_is_admitted_and_collateral_is_not(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "xlsx")
    record = _one(ctx, "xlsx.viol.value_perturb", "sheets/Data/cells/B8")
    new = record["recipe"]["params"]["steps"][0]["value"][1]
    good = synth.build_xlsx(tmp_path / "m.xlsx", cells={"Data": {"B8": ("n", new, 0)}})
    assert admitted(check(ctx.base, snapshot(good), _expectation(record)))
    bad = synth.build_xlsx(tmp_path / "x.xlsx",
                           cells={"Data": {"B8": ("n", new, 0), "C11": ("n", 1, 0)}})
    assert not admitted(check(ctx.base, snapshot(bad), _expectation(record)))


def test_formula_alternatives_preserve_the_value(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "xlsx")
    record = _one(ctx, "xlsx.alt.sum_range_expand", "sheets/Data/cells/B5")
    assert record["recipe"]["params"]["steps"][0]["formula"] == "=B2+B3+B4"
    good = synth.build_xlsx(tmp_path / "m.xlsx", cells={"Data": {"B5": ("f", "B2+B3+B4", 0, 10.0)}})
    assert admitted(check(ctx.base, snapshot(good), _expectation(record)))
    wrong = synth.build_xlsx(tmp_path / "w.xlsx", cells={"Data": {"B5": ("f", "B2+B3", 0, 5.0)}})
    results = {r.name: r.passed for r in check(ctx.base, snapshot(wrong), _expectation(record))}
    assert results["observable_preserved"] is False and results["expected_formulas"] is False
    literal = _one(ctx, "xlsx.alt.literal_for_formula", "sheets/Data/cells/D5")
    typed = synth.build_xlsx(tmp_path / "l.xlsx", cells={"Data": {"D5": ("n", 13.0, 2)}})
    assert admitted(check(ctx.base, snapshot(typed), _expectation(literal)))


def test_sheet_deletion_footprint(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "xlsx")
    record = _one(ctx, "xlsx.extra.delete_unrelated_sheet")
    assert record["recipe"]["params"]["steps"] == [{"op": "xlsx.remove_sheet", "sheet": "Notes"}]
    mutant = snapshot(synth.build_xlsx(tmp_path / "m.xlsx"))
    mutant["workbook"]["sheets"] = ["Data"]
    mutant["sheets"].pop("Notes")
    assert admitted(check(ctx.base, mutant, _expectation(record)))


def test_docx_delete_and_align_mutants(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "docx")
    record = _one(ctx, "docx.viol.delete_bound_paragraph")
    gone = int(record["recipe"]["params"]["site"]["unit"].split("/")[1])
    blocks = [b for i, b in enumerate(synth.DEFAULT_DOCX) if i != gone]
    mutant = snapshot(synth.build_docx(tmp_path / "d.docx", blocks=blocks))
    assert admitted(check(ctx.base, mutant, _expectation(record)))
    align = _one(ctx, "docx.viol.para_align_change", "body/2")
    adjust = align["recipe"]["params"]["steps"][0]["props"]["adjust"]
    jc = {"left": "left", "right": "right", "block": "both", "center": "center"}[adjust]
    blocks = copy.deepcopy(synth.DEFAULT_DOCX)
    blocks[2]["jc"] = jc
    mutant = snapshot(synth.build_docx(tmp_path / "a.docx", blocks=blocks))
    assert admitted(check(ctx.base, mutant, _expectation(align)))
    assert align["label"] == "should_fail_violation"


def test_pptx_move_delete_and_zorder_mutants(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "pptx")
    move = _one(ctx, "pptx.viol.move_shape")
    step = move["recipe"]["params"]["steps"][0]
    slides = copy.deepcopy(synth.DEFAULT_SLIDES)
    shape = slides[step["slide"]][step["shape"]]
    shape["off"] = (shape["off"][0] + step["dx_emu"], shape["off"][1] + step["dy_emu"])
    mutant = snapshot(synth.build_pptx(tmp_path / "m.pptx", slides=slides))
    assert admitted(check(ctx.base, mutant, _expectation(move)))

    delete = _one(ctx, "pptx.extra.delete_unrelated_slide")
    mutant = snapshot(synth.build_pptx(tmp_path / "d.pptx", slides=synth.DEFAULT_SLIDES[:1]))
    assert admitted(check(ctx.base, mutant, _expectation(delete)))

    swap = _one(ctx, "pptx.eq.zorder_nonoverlap")
    step = swap["recipe"]["params"]["steps"][0]
    slides = copy.deepcopy(synth.DEFAULT_SLIDES)
    order = slides[step["slide"]]
    order[step["a"]], order[step["b"]] = order[step["b"]], order[step["a"]]
    mutant = snapshot(synth.build_pptx(tmp_path / "z.pptx", slides=slides))
    assert admitted(check(ctx.base, mutant, _expectation(swap)))
    renamed = copy.deepcopy(slides)
    renamed[step["slide"]][step["a"]]["name"] = "PlaceHolder 9"  # regenerated names are ignored
    assert admitted(check(ctx.base, snapshot(synth.build_pptx(tmp_path / "n.pptx",
                                                              slides=renamed)),
                          _expectation(swap)))
    moved = order[step["a"]]
    order[step["a"]] = {**moved, "off": (moved["off"][0] + 360, moved["off"][1])}
    tampered = snapshot(synth.build_pptx(tmp_path / "t.pptx", slides=slides))
    assert not admitted(check(ctx.base, tampered, _expectation(swap)))


def _sh(x: int, y: int, w: int, h: int, **extra) -> dict:
    return {"kind": "sp", "name": f"s{x}-{y}", "off": [x, y], "ext": [w, h], **extra}


def test_zorder_swap_needs_clear_shapes_in_between() -> None:
    from harness.q2_mutation.operators.pptx import CLEARANCE_EMU, zorder_pair_is_inert

    # Review 3 (5cfb9197, slide 2): group 4 and 'Videotapes' (10) do not overlap,
    # but 'Newspapers' (8) lies inside group 4's frame. The old rule swapped them
    # and the filled frame then covered 'Newspapers'.
    group = _sh(3597120, 6396480, 3258720, 3023280, kind="grpSp")
    between = [_sh(7513920, 6396480, 3258720, 3023280, kind="grpSp"),
               _sh(11431080, 6396480, 3258720, 3023280, kind="grpSp"),
               _sh(3791880, 4950720, 2869200, 703080),
               _sh(3791880, 7523280, 2869200, 703080),  # inside the group's frame
               _sh(7707600, 4950720, 2869200, 703080)]
    videotapes = _sh(7707600, 7523280, 2869200, 703080)
    shapes = [_sh(0, 0, 10, 10)] * 4 + [group, *between, videotapes]
    assert not zorder_pair_is_inert(shapes, 4, 10)
    far = 10_000_000
    a, b, c = _sh(0, 0, 1_000_000, 1_000_000), _sh(far, 0, 1_000_000, 1_000_000), \
        _sh(0, far, 1_000_000, 1_000_000)
    assert zorder_pair_is_inert([a, b], 0, 1)  # adjacent, apart
    assert zorder_pair_is_inert([a, c, b], 0, 2)  # the shape between touches neither
    assert not zorder_pair_is_inert([a, _sh(500_000, 0, 9_000_000, 10), b], 0, 2)
    assert not zorder_pair_is_inert([a, {"kind": "sp", "name": "ph"}, b], 0, 2)  # no frame
    near = _sh(1_000_000 + CLEARANCE_EMU - 1, 0, 1_000_000, 1_000_000)
    assert not zorder_pair_is_inert([a, near], 0, 1)  # within the clearance
    # A rotated shape is judged by the bounding box of its rotation.
    tall = _sh(0, 0, 4_000_000, 100_000)
    assert not zorder_pair_is_inert([tall, _sh(0, 150_000, 100_000, 100_000)], 0, 1)
    beside = _sh(1_800_000, 600_000, 100_000, 100_000)
    assert zorder_pair_is_inert([tall, beside], 0, 1)
    assert not zorder_pair_is_inert([{**tall, "rot": str(90 * 60_000)}, beside], 0, 1)


def test_delete_bound_shape_skips_shapes_hidden_under_later_ones(tmp_path: Path) -> None:
    from harness.q2_mutation.operators.pptx import COVERED_SHARE, covered_share

    # Review 3 (4ed5abd0, slide 2): a sparkle group drawn again, piece by
    # piece, by the shapes stacked above it.
    group = _sh(16125120, 779040, 1460880, 1468440, kind="grpSp")
    pieces = [_sh(16125120, 799920, 1254960, 1415880), _sh(17251200, 779040, 334800, 412200),
              _sh(17227080, 1829880, 354960, 417600), _sh(16189920, 846360, 1149840, 1319760),
              _sh(17285760, 821160, 273600, 318240), _sh(17254800, 1864080, 299520, 342360)]
    assert covered_share([group, *pieces], 0) >= COVERED_SHARE
    assert covered_share([*pieces, group], len(pieces)) == 0.0  # nothing above it
    assert covered_share([_sh(0, 0, 100, 100), _sh(0, 0, 50, 100)], 0) == pytest.approx(0.5)
    assert covered_share([_sh(0, 0, 100, 100), _sh(0, 0, 50, 100), _sh(40, 0, 60, 100)], 0) == 1.0

    ctx = _ctx(tmp_path, "pptx")
    planned, _ = plan_operator(registry()["pptx.viol.delete_bound_shape"](), ctx)
    units = {p.record["recipe"]["params"]["site"]["unit"] for p in planned}
    assert units  # the synthetic deck's bound shapes are visible
    slide = ctx.base["slides"][0]["shapes"]
    cover = {**slide[0], "name": "Cover", "off": [0, 0], "ext": [9_144_000, 6_858_000]}
    ctx.base["slides"][0]["shapes"] = [*slide, cover]
    planned, _ = plan_operator(registry()["pptx.viol.delete_bound_shape"](), ctx)
    hidden = {p.record["recipe"]["params"]["site"]["unit"] for p in planned}
    assert not any(u.startswith("slides/0/shapes/") for u in hidden)


# --------------------------------------------------------------------------- text and config


@pytest.mark.parametrize("kind", ["config", "ini", "text"])
def test_text_families_end_to_end(tmp_path: Path, kind: str) -> None:
    name = {"config": "settings.json", "ini": "app.conf", "text": "notes.txt"}[kind]
    if kind == "config":
        base = synth.build_json(tmp_path / name)
        initial = synth.build_json(tmp_path / "init" / name,
                                   {**synth.SETTINGS_JSON, "editor.fontSize": 12})
    else:
        content = synth.APP_INI if kind == "ini" else synth.NOTES_TXT
        base = synth.build_text(tmp_path / name, content)
        initial = None
    spec = RequirementSpec.from_dict(synth.synthetic_spec(kind))
    ctx = make_context(spec.task_id, spec, base, initial)
    records, _ = plan_task(ctx)
    assert {r["label"] for r in records} >= {"should_fail_violation", "should_fail_extra_change",
                                            "should_pass_equiv"}
    logs = {e["mutant_id"]: e for e in apply_text_records(records, base, tmp_path / "mutants")}
    for record in records:
        mutant = tmp_path / "mutants" / record["mutant_id"] / name
        done = verify(record, base, mutant, logs[record["mutant_id"]])
        assert is_admitted(done), (record["operator"], done["purity_checks"])


def _xlsx_spec(
    reqs: list[tuple[str, str, str]], allowed: list[str] | None = None
) -> RequirementSpec:
    return _spec("xlsx", requirements=[
        {"req_id": rid, "statement": text, "check_kind": kind, "observable": text}
        for rid, text, kind in reqs
    ], allowed_variations=allowed or [])


def test_flagged_entries_are_questions_not_freedoms(tmp_path: Path) -> None:
    base_req = [("R1", "D5 holds the grand total of D2:D4 as a formula.", "cell_value")]
    flagged = _xlsx_spec(base_req, ["[AMBIGUOUS] whether D5 may be a typed value or a formula"])
    record = _one(_ctx(tmp_path / "a", "xlsx", flagged), "xlsx.alt.literal_for_formula")
    assert record["label"] == "ambiguous"
    assert record["witness"]["argument"].startswith("W-A-")
    freed = _xlsx_spec(base_req, ["whether D5 is a typed value or a formula"])
    record = _one(_ctx(tmp_path / "b", "xlsx", freed), "xlsx.alt.literal_for_formula")
    assert record["label"] == "should_pass_alt_solution"
    flagged_req = _xlsx_spec([("R1", "[AMBIGUOUS] B8 may hold 12 or 12.0.", "cell_value")])
    record = _one(_ctx(tmp_path / "c", "xlsx", flagged_req), "xlsx.viol.value_perturb")
    assert record["label"] == "ambiguous"
    assert record["witness"]["argument"].startswith("W-R-FLAGGED")


def test_preservation_requirements_bind_the_untouched_cells(tmp_path: Path) -> None:
    spec = _xlsx_spec([
        ("R1", "D5 holds the total of D2:D4.", "cell_value"),
        ("R2", "Cells in A1:D8 that held values initially keep their original values.",
         "cell_value"),
        ("R3", "Cells outside A1:D8 are not touched.", "cell_value"),
    ])
    ctx = _ctx(tmp_path, "xlsx", spec)
    assert ctx.bindings["R1"].units == ("sheets/Data/cells/D5",)
    kept = set(ctx.bindings["R2"].units)
    assert ctx.bindings["R2"].method == "explicit-delta"
    assert "sheets/Data/cells/D5" not in kept and "sheets/Data/cells/B2" in kept
    assert ctx.bindings["R3"].method == "excluded_only" and not ctx.bindings["R3"].units
    perturb = registry()["xlsx.viol.value_perturb"]()
    planned, _ = plan_operator(perturb, ctx)
    assert planned and all(p.record["witness"]["req_ids"] == ["R2"] for p in planned)
    assert all(p.record["label"] == "should_fail_violation" for p in planned)
