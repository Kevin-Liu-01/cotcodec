"""Core machinery of the Q2 mutation operators: formulas, snapshots, diff, purity, specs."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from harness.q2_mutation.operators import _formula as fx
from harness.q2_mutation.operators import _jsonspan as js
from harness.q2_mutation.operators import _synth as synth
from harness.q2_mutation.operators._diff import diff, resolve
from harness.q2_mutation.operators._purity import Expectation, admitted, check, xlsx_dependents
from harness.q2_mutation.operators._snapshot import snapshot
from harness.q2_mutation.operators._spec import bind, delta_units, mentions
from harness.q2_mutation.operators.apply_text import TextApplyError, apply_steps
from harness.q2_mutation.schema import RequirementSpec


def _req(spec: dict, req_id: str):
    return next(
        r for r in RequirementSpec.from_dict(spec).requirements if r.req_id == req_id
    )


# --------------------------------------------------------------------------- formulas


def test_formula_shift_absolutize_and_api_grammar() -> None:
    assert fx.shift_formula("=SUM(A1:B$2)+$C3", 2, 1) == "=SUM(B3:C$2)+$C5"
    assert fx.absolutize("=Sheet2!A1+B2") == "=Sheet2!$A$1+$B$2"
    assert fx.to_api_grammar('=IF(A1>0,"a,b",B1)') == '=IF(A1>0;"a,b";B1)'
    assert fx.referenced_cells("=SUM(A1:A3)+'My Sheet'!B2", "S") == {
        ("S", 1, 1), ("S", 2, 1), ("S", 3, 1), ("My Sheet", 2, 2)
    }
    assert fx.single_call("=SUM(B2:B4)", "SUM") is not None
    assert fx.single_call("=SUM(B2:B4)+1", "SUM") is None
    with pytest.raises(fx.FormulaError):
        fx.tokenize("=A1 ~ B2")


def test_function_names_are_not_cell_references() -> None:
    kinds = [(t.kind, t.text) for t in fx.tokenize("=LOG10(A1)") if t.kind != "space"]
    assert kinds[0] == ("func", "LOG10")
    assert ("ref", "A1") in kinds


# --------------------------------------------------------------------------- snapshots


def test_xlsx_snapshot_values_formulas_and_styles(tmp_path: Path) -> None:
    snap = snapshot(synth.build_xlsx(tmp_path / "w.xlsx"))
    cells = snap["sheets"]["Data"]["cells"]
    assert cells["B2"]["v"] == ["n", 3.0]
    assert cells["D5"]["f"] == "=D2+D3+D4"
    assert cells["B7"]["v"] == ["s", "Apple-Pear"]
    assert cells["A1"]["style"]["font"]["b"] is True
    assert cells["D2"]["style"]["numfmt"] == "0.00"
    assert cells["A5"]["style"]["fill"]["fg"] == "rgb:FFFF00"
    assert snap["workbook"]["sheets"] == ["Data", "Notes"]


def test_xlsx_shared_formulas_are_expanded(tmp_path: Path) -> None:
    path = synth.build_xlsx(tmp_path / "w.xlsx")
    with zipfile.ZipFile(path) as archive:
        parts = {n: archive.read(n) for n in archive.namelist()}
    sheet = parts["xl/worksheets/sheet1.xml"].decode()
    sheet = sheet.replace("<f>B2*C2</f>", '<f t="shared" ref="D2:D4" si="0">B2*C2</f>')
    sheet = sheet.replace("<f>B3*C3</f>", '<f t="shared" si="0"/>')
    sheet = sheet.replace("<f>B4*C4</f>", '<f t="shared" si="0"/>')
    parts["xl/worksheets/sheet1.xml"] = sheet.encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    cells = snapshot(path)["sheets"]["Data"]["cells"]
    assert [cells[a]["f"] for a in ("D2", "D3", "D4")] == ["=B2*C2", "=B3*C3", "=B4*C4"]


def test_docx_snapshot_merges_runs_with_equal_properties(tmp_path: Path) -> None:
    split = [{"runs": [("Hello ", {}), ("world", {})]}]
    joined = [{"runs": [("Hello world", {})]}]
    a = snapshot(synth.build_docx(tmp_path / "a.docx", blocks=split))
    b = snapshot(synth.build_docx(tmp_path / "b.docx", blocks=joined))
    assert a["body"] == b["body"]
    assert diff(a, b) == []


def test_docx_snapshot_reads_tables_styles_and_highlight(tmp_path: Path) -> None:
    snap = snapshot(synth.build_docx(tmp_path / "r.docx"))
    body = snap["body"]
    assert body[0]["style"] == "Title" and body[0]["text"] == "ANNUAL REPORT"
    assert body[1]["spans"][1] == ["strongly", {"b": True}]
    assert body[3]["spans"][1][1]["highlight"] == "yellow"
    assert body[4]["type"] == "tbl"
    assert resolve(snap, "body/4/cell/1/0/0/text") == "North"
    assert snap["styles"]["para"]["Title"]["rpr"]["b"] is True


def test_pptx_snapshot_shapes_tables_and_placeholders(tmp_path: Path) -> None:
    snap = snapshot(synth.build_pptx(tmp_path / "d.pptx"))
    shapes = snap["slides"][0]["shapes"]
    assert shapes[0]["placeholder"]["type"] == "title"
    assert shapes[0]["text"] == "QUARTERLY RESULTS"
    assert shapes[1]["paras"][0]["spans"][1] == ["north", {"b": True}]
    assert shapes[2]["kind"] == "table"
    assert shapes[2]["table"]["rows"][1][0]["text"] == "North"
    assert shapes[1]["off"] == [457200, 1600200]


# --------------------------------------------------------------------------- diff


def test_diff_aligns_paragraph_deletion(tmp_path: Path) -> None:
    base = snapshot(synth.build_docx(tmp_path / "a.docx"))
    blocks = [b for i, b in enumerate(synth.DEFAULT_DOCX) if i != 2]
    actual = snapshot(synth.build_docx(tmp_path / "b.docx", blocks=blocks))
    changes = diff(base, actual)
    assert [(c.loc, c.op) for c in changes] == [("body/2", "removed")]


def test_diff_detects_renamed_sheet_without_content_churn(tmp_path: Path) -> None:
    base = snapshot(synth.build_xlsx(tmp_path / "a.xlsx"))
    actual = json.loads(json.dumps(base))
    actual["sheets"]["Notes old"] = actual["sheets"].pop("Notes")
    actual["workbook"]["sheets"] = ["Data", "Notes old"]
    actual["workbook"]["states"] = {"Data": "visible", "Notes old": "visible"}
    assert [(c.loc, c.op) for c in diff(base, actual)] == [("sheets/Notes/name", "changed")]


def test_diff_reports_shape_move_as_layout(tmp_path: Path) -> None:
    slides = [[dict(s) for s in synth.DEFAULT_SLIDES[0]], synth.DEFAULT_SLIDES[1]]
    slides[0][1] = {**slides[0][1], "off": (457200 + 540000, 1600200)}
    base = snapshot(synth.build_pptx(tmp_path / "a.pptx"))
    actual = snapshot(synth.build_pptx(tmp_path / "b.pptx", slides=slides))
    changes = diff(base, actual)
    assert [(c.loc, c.kind) for c in changes] == [("slides/0/shapes/1/off", "layout")]


# --------------------------------------------------------------------------- purity


def test_purity_flags_collateral_and_missing_edits(tmp_path: Path) -> None:
    base = snapshot(synth.build_xlsx(tmp_path / "a.xlsx"))
    actual = snapshot(synth.build_xlsx(
        tmp_path / "b.xlsx", cells={"Data": {"B8": ("n", 13, 0), "C10": ("n", 8, 0)}}
    ))
    unit = "sheets/Data/cells/B8"
    ok = Expectation(allow=[f"{unit}/v"], must_change=[f"{unit}/v"])
    results = {r.name: r.passed for r in check(base, actual, ok)}
    assert results["edit_landed"] is True
    assert results["no_collateral_change"] is False
    clean = snapshot(synth.build_xlsx(
        tmp_path / "c.xlsx", cells={"Data": {"B8": ("n", 13, 0)}}
    ))
    assert admitted(check(base, clean, ok))
    assert not admitted(check(base, base, ok))  # nothing changed: normalized away


def test_purity_tolerates_formula_dependents_only(tmp_path: Path) -> None:
    base = snapshot(synth.build_xlsx(tmp_path / "a.xlsx"))
    deps = xlsx_dependents(base, ["sheets/Data/cells/B2"])
    assert "sheets/Data/cells/D2/v" in deps
    assert "sheets/Data/cells/D5/v" in deps  # transitive through D2
    assert "sheets/Data/cells/C2/v" not in deps


def test_purity_appearance_check_resolves_styles(tmp_path: Path) -> None:
    styled = [{"style": "Title", "runs": [("Heading", {})]}]
    direct = [{"jc": "center", "runs": [("Heading", {"b": True})]}]
    base = snapshot(synth.build_docx(tmp_path / "a.docx", blocks=styled))
    actual = snapshot(synth.build_docx(tmp_path / "b.docx", blocks=direct))
    exp = Expectation(allow=["body/0/*"], must_change=["body/0/style"], appearance=["body/0"])
    names = {r.name: r for r in check(base, actual, exp)}
    # Title also sets 20 pt and spacing; the direct version lacks them, so it is not equal.
    assert names["appearance_preserved"].passed is False


# --------------------------------------------------------------------------- specs and binding


def test_binding_uses_explicit_references_and_delta(tmp_path: Path) -> None:
    base = snapshot(synth.build_xlsx(tmp_path / "a.xlsx"))
    initial = snapshot(synth.build_xlsx(tmp_path / "i.xlsx", drop=("Data!D5",)))
    delta = delta_units(diff(base, initial), "xlsx")
    assert "sheets/Data/cells/D5" in delta
    spec = synth.synthetic_spec("xlsx")
    binding = bind(_req(spec, "R1"), base, delta)
    assert binding.units == ("sheets/Data/cells/D5",)
    assert (binding.method, binding.confidence) == ("explicit+delta", "high")
    header = bind(_req(spec, "R3"), base, delta)
    assert len(header.units) == 4 and header.confidence == "medium"


def test_binding_docx_quotes_and_pptx_slides(tmp_path: Path) -> None:
    docx = snapshot(synth.build_docx(tmp_path / "r.docx"))
    b = bind(_req(synth.synthetic_spec("docx"), "R3"), docx, {})
    assert b.units == ("body/2",)
    pptx = snapshot(synth.build_pptx(tmp_path / "d.pptx"))
    title = bind(_req(synth.synthetic_spec("pptx"), "R1"), pptx, {})
    assert title.units == ("slides/0/shapes/0",)
    cell = bind(_req(synth.synthetic_spec("pptx"), "R2"), pptx, {})
    assert "slides/0/shapes/2/table/rows/1/0" in cell.units


def test_aspect_mentions_are_word_level() -> None:
    assert mentions("Make the header bold", "bold") == ["bold"]
    assert mentions("Use a formula in D5", "formula") == ["formula"]
    assert mentions("Boldly go", "bold") == ["Bold"]  # documented: prefix match
    assert mentions("the total", "formula") == []


# --------------------------------------------------------------------------- text and json


def test_jsonspan_delete_keeps_json_valid() -> None:
    text = '{\n  "a": 1, // first\n  "b": {"c": true},\n  "d": "x",\n}\n'
    root = js.parse(text)
    for path in (["a"], ["d"], ["b", "c"]):
        _node, parent, index = js.find(root, path)
        start, end = js.delete_span(text, parent, index)
        edited = text[:start] + text[end:]
        from harness.q2_mutation.operators._snapshot import strip_jsonc

        data = json.loads(strip_jsonc(edited))
        node = data
        for key in path[:-1]:
            node = node[key]
        assert path[-1] not in node


def test_apply_text_guards_and_transforms() -> None:
    text = '{"b": 1, "a": 2}\n'
    with pytest.raises(TextApplyError):
        apply_steps(text, [{"op": "text.splice", "start": 6, "end": 7, "new": "5",
                            "expect_sha256": "0" * 64}])
    reordered = apply_steps(text, [{"op": "json.reorder", "path": [], "order": ["a", "b"],
                                    "indent": 2}])
    assert list(json.loads(reordered)) == ["a", "b"] and reordered.endswith("\n")
    ini = "[s]\nk=v\nx = y\n"
    assert apply_steps(ini, [{"op": "ini.respace", "style": "spaced"}]) == "[s]\nk = v\nx = y\n"
    assert apply_steps("a\n", [{"op": "text.set_trailing_newline", "value": False}]) == "a"


def test_delta_expectations_are_relative_to_the_reference(tmp_path: Path) -> None:
    slides = [[dict(s) for s in synth.DEFAULT_SLIDES[0]], synth.DEFAULT_SLIDES[1]]
    base = snapshot(synth.build_pptx(tmp_path / "a.pptx", slides=slides))
    slides[0][3] = {**slides[0][3], "off": (slides[0][3]["off"][0] + 360, slides[0][3]["off"][1])}
    actual = snapshot(synth.build_pptx(tmp_path / "b.pptx", slides=slides))
    loc = "slides/0/shapes/3/off"
    good = Expectation(allow=[loc], must_change=[loc], deltas=[(loc, [360, 0])])
    assert admitted(check(base, actual, good))
    wrong = Expectation(allow=[loc], must_change=[loc], deltas=[(loc, [0, 360])])
    assert not admitted(check(base, actual, wrong))
    roundtrip = Expectation.from_dict(json.loads(json.dumps(good.as_dict())))
    assert roundtrip.deltas == good.deltas


def test_rotated_or_flipped_shapes_are_not_moved() -> None:
    from harness.q2_mutation.operators.pptx import movable

    assert movable({"off": [0, 0]})
    assert not movable({"off": [0, 0], "rot": "5400000"})
    assert not movable({"off": [0, 0], "flipH": "1"})
    assert not movable({"ext": [1, 1]})
