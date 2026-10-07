"""The operator registry and the KernelBench-M rule mapping are complete and honest."""

from __future__ import annotations

from harness.q1.mutate.operators import OPERATORS, registry_fingerprint, registry_table
from harness.q1.mutate.rules import (
    KERNELBENCH_M_INACTIVE,
    KERNELBENCH_M_RULES,
    NOT_APPLICABLE,
    mapping_markdown,
    rule_mapping,
    unmapped_rules,
)
from harness.q1.schema import MUTATION_FAMILIES, OPERATOR_RE, RULE_ORIGINS


def test_every_kernelbench_m_rule_is_accounted_for_once():
    assert len(KERNELBENCH_M_RULES) == 127
    assert len(KERNELBENCH_M_RULES) - len(KERNELBENCH_M_INACTIVE) == 124
    assert unmapped_rules() == []
    mapping = rule_mapping()
    assert set(mapping) == set(KERNELBENCH_M_RULES)
    claimed = [op.kbm_rule for op in OPERATORS if op.kbm_rule] + [
        r for op in OPERATORS for r in op.ports
    ]
    # A rule may be the primary of several operators (e.g. stride confusions in
    # device and launch scope) but never both ported and not-applicable.
    assert not set(claimed) & set(NOT_APPLICABLE)
    assert set(claimed) | set(NOT_APPLICABLE) == set(KERNELBENCH_M_RULES)


def test_operator_metadata_matches_the_shared_schema():
    names = [op.name for op in OPERATORS]
    assert len(names) == len(set(names))
    for op in OPERATORS:
        assert OPERATOR_RE.fullmatch(op.name)
        assert op.family in MUTATION_FAMILIES
        assert op.origin in RULE_ORIGINS
        if op.origin == "paper":
            assert op.kbm_rule in KERNELBENCH_M_RULES
            assert all(rule in KERNELBENCH_M_RULES for rule in op.ports)
        else:
            assert op.kbm_rule is None and not op.ports


def test_ported_operators_keep_the_paper_family():
    for op in OPERATORS:
        if op.origin == "paper":
            assert KERNELBENCH_M_RULES[op.kbm_rule] == op.family, op.name


def test_every_family_has_paper_operators():
    families = {op.family for op in OPERATORS if op.origin == "paper"}
    assert families == set(MUTATION_FAMILIES)


def test_not_applicable_rules_have_reasons():
    assert all(len(reason) > 30 for reason in NOT_APPLICABLE.values())
    statuses = {entry["status"] for entry in rule_mapping().values()}
    assert statuses == {"ported", "subsumed", "not-applicable"}


def test_registry_fingerprint_is_stable_and_tracks_metadata():
    assert registry_fingerprint() == registry_fingerprint()
    assert len(registry_table()) == len(OPERATORS)
    assert len(registry_fingerprint()) == 64


def test_mapping_markdown_lists_every_rule():
    table = mapping_markdown()
    assert table.count("\n") == len(KERNELBENCH_M_RULES) + 1


def test_readme_tables_are_current():
    from harness.q1.mutate.rules import README_PATH, render_readme

    text = README_PATH.read_text()
    assert text == render_readme(text), "run: python -m harness.q1.mutate.rules"
