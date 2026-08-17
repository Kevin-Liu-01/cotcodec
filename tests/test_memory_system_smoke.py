from __future__ import annotations

from scripts.run_memory_system_smoke import run_smoke


def test_reference_memory_system_smoke_separates_estimands() -> None:
    artifact = run_smoke(
        system_id="reference",
        task_id="memory-000002",
        embedding_base_url=None,
        embedding_model="unused",
        embedding_dimensions=384,
    )
    assert artifact["status"] == "NATIVE_INTERFACE_SMOKE_PASS"
    assert artifact["scientific_evidence"] is False
    assert artifact["gates"]["semantic_aa_replay"] is True
    assert artifact["gates"]["publication_provenance"] is False
    modes = {cell["treatment_mode"] for cell in artifact["cells"]}
    assert modes == {"serve_only", "storage_and_service"}
