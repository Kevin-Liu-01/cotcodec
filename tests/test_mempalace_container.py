from pathlib import Path

DOCKERFILE = Path("infra/memory-baselines/mempalace/Dockerfile")


def test_mempalace_image_binds_current_source_lock_and_offline_model() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    final_stage = content.split("FROM ${COTCODEC_IMAGE}\n", maxsplit=1)[1]
    assert final_stage.startswith("\nARG COTCODEC_IMAGE\n")
    assert "COPY --from=mempalace_source" in content
    assert "test -f .cotcodec-original-dockerignore" in content
    assert "mv .cotcodec-original-dockerignore .dockerignore" in content
    assert "COTCODEC_IMAGE must be immutable name@sha256" in content
    assert 'org.opencontainers.image.cotcodec-base-reference="${COTCODEC_IMAGE}"' in content
    assert "prepare_mempalace_source_context.py" in content
    assert "--verify-only" in content
    assert "906b918a7c6ebb2a9198a6bf5a78f30a173fea56" in content
    assert "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d" in content
    assert "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da" in content
    assert "importlib.metadata.version('chromadb') == '1.5.7'" in content
    assert "COPY --from=minilm_model" in content
    assert "prepare_chroma_minilm.py" in content
    assert "--verify-only" in content
    assert "ANONYMIZED_TELEMETRY=FALSE" in content
    assert "run_mempalace_upstream_reproduction.py" in content
    assert "org.opencontainers.image.cotcodec-publication-ready=\"false\"" in content
