# Operator items for the q2-0a evaluator-mutation preregistration (draft input)

Input for the preregistration author. Not frozen. Copy the items below into
the experiment's preregistration before `scripts/preregister.py freeze`.

## Identity

- Operator catalog `q2-mut-operators-v1`, `catalog_sha256`
  `2e2f24069c833c54bba23650481edec6ffff97176d07377327019e3a7f51d1fe` (hash over the operator descriptions and the
  sources of `harness/q2_mutation/operators/`), 64 operators.
- Validated at commit `7c429bcb793369649bc7970ccad0fba290ad2772` in image
  `sha256:894b2623dceb43e8468a2adbd6e03a532ea9683d4b7754cd79fa0d58a331f909`
  (the OSWorld VM's LibreOffice 7.3.7.2 30(Build:2)).
- Any operator added or changed after the freeze is exploratory and reported
  separately.

## Catalog

- **E, equivalence (should pass)**, 14 operators: `xlsx.eq.doc_property`, `xlsx.eq.view_zoom`, `xlsx.eq.view_selection`, `xlsx.eq.active_sheet`, `docx.eq.doc_property`, `docx.eq.view_zoom`, `pptx.eq.doc_property`, `pptx.eq.subvisible_nudge`, `pptx.eq.zorder_nonoverlap`, `text.eq.trailing_newline`, `config.eq.trailing_newline`, `config.eq.json_reformat`, `config.eq.json_key_reorder`, `config.eq.ini_kv_spacing`.
- **A, alternative valid solution (should pass)**, 15 operators: `xlsx.alt.literal_for_formula`, `xlsx.alt.reference_for_literal`, `xlsx.alt.sum_range_expand`, `xlsx.alt.plus_chain_to_sum`, `xlsx.alt.average_to_sum_count`, `xlsx.alt.absolute_refs`, `xlsx.alt.concat_to_ampersand`, `xlsx.alt.named_style_for_direct`, `docx.alt.char_style_for_direct`, `docx.alt.para_direct_for_style`, `docx.alt.highlight_as_shading`, `docx.alt.case_via_format`, `pptx.alt.textbox_for_placeholder`, `pptx.alt.case_via_format`, `config.alt.json_number_repr`.
- **R, requirement violation (should fail)**, 18 operators: `xlsx.viol.value_perturb`, `xlsx.viol.formula_ref_shift`, `xlsx.viol.clear_bound_cell`, `xlsx.viol.drop_char_format`, `xlsx.viol.number_format_change`, `docx.viol.text_edit`, `docx.viol.drop_char_format`, `docx.viol.para_align_change`, `docx.viol.line_spacing_change`, `docx.viol.delete_bound_paragraph`, `pptx.viol.text_edit`, `pptx.viol.table_cell_text` (probe-informed), `pptx.viol.drop_char_format`, `pptx.viol.move_shape`, `pptx.viol.delete_bound_shape`, `text.viol.line_edit`, `config.viol.value_change`, `config.viol.key_delete`.
- **F, unrequested extra change (should fail)**, 17 operators: `xlsx.extra.edit_unrelated_value`, `xlsx.extra.clear_unrelated_row`, `xlsx.extra.rename_unrelated_sheet`, `xlsx.extra.delete_unrelated_sheet`, `xlsx.extra.format_unrelated_cell`, `docx.extra.edit_unrelated_paragraph`, `docx.extra.delete_unrelated_paragraph`, `docx.extra.edit_unrelated_table_cell` (probe-informed), `docx.extra.format_unrelated_run`, `pptx.extra.edit_unrelated_text`, `pptx.extra.delete_unrelated_slide`, `pptx.extra.add_textbox`, `pptx.extra.edit_notes`, `text.extra.unrelated_line_edit`, `text.extra.unrelated_line_delete`, `config.extra.unrelated_value_change`, `config.extra.unrelated_key_delete`.

All operators are in the `document_model` stratum: office edits go through
LibreOffice's UNO API on the saved gold and are saved with `.uno:Save` under
Xvfb with the VM's LibreOffice profile; text and config edits splice the
original characters. The two probe-informed operators touch table text, a
defect class the scoping probes found; their cells are exploratory.

## Inputs and reference

- Base: LibreOffice-save of the gold file (a `uno_apply.py` row with no
  steps). Task delta: structural diff between the base and the
  LibreOffice-saved initial file.
- Purity reference: the null mutant, the base saved once more through the same
  path. LibreOffice 7.3 is not a load-save fixed point (validation evidence:
  Impress shrinks shape extents by 1/100 mm per round trip and can change a
  slide's layout association; Writer adds a default-style property on the
  second save; placeholder names are regenerated from export order).
- At scoring, the harness reachability stage re-saves every mutant through the
  task's own postconfig save, as for every other candidate. Purity should be
  re-checked on those outputs against the reachability output of the null
  mutant.

## Sites, seeds and labels

- Requirement binding from the blind spec only: explicit references or quotes
  that the task delta also touches (`explicit+delta`, high); for preservation
  requirements ("keep", "unchanged", "not touched"), explicit units minus the
  delta (`explicit-delta`, medium); other explicit references (medium); delta
  units of the matching check kind (`delta_kind`, low). A requirement whose
  only references are exclusions ("cells outside B1:E30") binds nothing.
- At most 3 sites per (task, operator), ordered by a SHA-256 of
  (task, operator), assigned seeds 42, 43, 44. A unit bound to several
  requirements cites the most strongly bound one. Outside sites exclude every
  unit in the task delta or a binding, and cells that feed them.
- Labels are fixed at planning time from the spec (witness rules W-E, W-A,
  W-R, W-F in the package docstring). `should_fail_violation` needs a high or
  medium binding and a requirement that pins the attacked aspect; otherwise
  the mutant is `ambiguous`. Requirements and allowed variations the author
  marked `[AMBIGUOUS]` are questions, not freedoms: an operator touching them
  is labelled `ambiguous` (W-*-FLAGGED). Ambiguous mutants never enter FN or
  FP rates; they go to the blind audit (D9).

## Admission and exclusions

- A mutant is admitted only if every purity check passes: `applied`,
  `survived_save`, `edit_landed`, `no_collateral_change`, and the declared
  `forbidden_kinds_absent`, `observable_preserved`, `appearance_preserved`,
  `same_items`, `expected_values`, `expected_deltas`, `expected_formulas`.
- Consequences LibreOffice applies to the edited unit itself are inside the
  footprint: automatic row height of an edited spreadsheet row, the recognized
  number format of a cleared cell, the height of an auto-growing text box or
  table row after a text edit, regenerated placeholder names on an edited
  slide, and child offsets of a moved group.
- `edit_landed` failures of R operators are equivalent mutants (the edit did
  not change the observable); they are counted per operator, never relabelled.
- `survived_save` failures are normalization findings, reported per operator.
- An apply error (UNO exception, timeout, a text-digest guard mismatch) or a
  snapshot parse error is an infrastructure exclusion, counted per operator.
- Admitted mutants with identical snapshot digests within a
  (task, operator) cell are deduplicated, keeping the lowest seed.

## Dev-split exposure

The operator runs on OSWorld files used only development-split tasks (14,
listed in `devsmoke-dev.json` and `devplan-dev.json`), never the confirmatory
split, and ran no checker.
