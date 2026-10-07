from __future__ import annotations

import io
import json
import urllib.error
import zipfile
from email.message import Message

import numpy as np
import pytest
from scipy import stats

from harness import holo3_rerun_audit as audit
from harness import osworld_source, remote_zip
from tests import _holo3_world as world_mod


def context(world: world_mod.World) -> audit.FetchContext:
    return audit.FetchContext(world_mod.opener(world), cache=None, max_workers=2)


def matrix(world: world_mod.World) -> tuple[audit.VerifiedPackage, audit.V1Matrix, audit.HRuns]:
    ctx = context(world)
    pkg = audit.load_verified_package(ctx)
    web = {t: audit.web_dependent(c) for t, c in world_mod.configs(world).items()}
    m = audit.build_v1_matrix(pkg, web)
    h = audit.load_h_runs(ctx, pkg.universe, with_steps=True)
    return pkg, m, h


# --------------------------------------------------------------------------- #
# Positive controls and tamper cases on the synthetic package
# --------------------------------------------------------------------------- #


def test_synthetic_package_passes_every_positive_control() -> None:
    world = world_mod.build_world()
    pkg, m, h = matrix(world)
    assert audit.holo3_domain_control(m)["status"] == "PASS"
    assert audit.summary_control(pkg, m)["status"] == "PASS"
    assert m.v1_source[world.repaired[0]] == "repair"
    assert m.v1_source[world.errors[0]] == "error"
    assert m.flags[world.universe["os"][0]][0] >= {"F2"}
    assert world.errors[1] in {t.split("/")[1] for t in h.null_rewards["072452"]}
    assert h.err_files["073458"] and not h.err_files["072452"]
    assert h.steps["072452"][world.tasks[5]] == 3
    assert pkg.tarball["sha256_from_sha256sums"]


def test_flipping_one_score_fails_the_domain_control() -> None:
    world = world_mod.build_world()
    victim = next(t for t in world.universe["vlc"] if world.run2[t] == 1.0)
    world.run2[victim] = 0.0
    _, m, _ = matrix(world)
    control = audit.holo3_domain_control(m)
    assert control["status"] == "FAIL"
    assert any("vlc" in p for p in control["problems"])


def test_dropped_member_fails_closed() -> None:
    world = world_mod.build_world()
    world.drop = {f"{audit.RUN_DIRS['run2']}/benchmark.log"}
    with pytest.raises(remote_zip.MissingMemberError):
        audit.load_verified_package(context(world))


def test_sha256sums_mismatch_fails_closed() -> None:
    world = world_mod.build_world()
    world.corrupt_sha256sums = True
    with pytest.raises(remote_zip.ZipIntegrityError, match="SHA256SUMS"):
        audit.load_verified_package(context(world))


def test_changed_revision_fails_closed() -> None:
    world = world_mod.build_world()
    blob = world_mod.verified_zip(world)
    spec = audit.VERIFIED_ARCHIVE

    def resolve(request, timeout):
        headers = Message()
        headers["X-Repo-Commit"] = "f" * 40
        headers["X-Linked-Size"] = str(spec.size)
        headers["X-Linked-Etag"] = spec.lfs_sha256
        headers["Location"] = "https://cdn/x"
        raise urllib.error.HTTPError(request.full_url, 302, "Found", headers, None)

    def refuse_read(request, timeout):
        raise AssertionError("no byte may be read from an unverified source")

    def open_archive(s: audit.ArchiveSpec) -> remote_zip.RangeSource:
        return remote_zip.HFRangeSource(
            audit.DATASET_REPO,
            audit.DATASET_REVISION,
            s.path,
            expected_size=s.size,
            expected_sha256=s.lfs_sha256,
            resolve_open=resolve,
            range_open=refuse_read,
        )

    assert blob  # the bytes exist, but the identity check must refuse them
    with pytest.raises(remote_zip.SourceIdentityError, match="commit"):
        audit.load_verified_package(audit.FetchContext(open_archive))


def test_logs_are_parsed_in_memory_and_never_cached(tmp_path) -> None:
    world = world_mod.build_world()
    ctx = audit.FetchContext(world_mod.opener(world), cache=remote_zip.MemberCache(tmp_path))
    audit.load_verified_package(ctx)
    cached = [path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()]
    assert cached and not any(b"Env prep failed" in blob for blob in cached)
    env_prep, agp = audit.parse_env_prep_log(
        b"x surferH.benchmark_retry ERROR [VM-1][abcdef01] Env prep failed (env 1/2): boom\n"
        b"x surferH.benchmark_retry INFO [VM-1][abcdef01] AGP done in 5s: Completed\n"
        b"x other INFO [VM-1][abcdef02] Env prep failed\n"
    )
    assert env_prep == {"abcdef01": 1} and agp == {"abcdef01": 1}


def test_label_swap_flips_mcnemar_sign() -> None:
    tasks = [f"t{i}" for i in range(40)]
    a = {t: float(i % 3 == 0) for i, t in enumerate(tasks)}
    b = {t: float(i % 5 == 0) for i, t in enumerate(tasks)}
    forward = audit.mcnemar(tasks, a, b)
    backward = audit.mcnemar(tasks, b, a)
    assert (forward.n10, forward.n01) == (backward.n01, backward.n10)
    assert forward.z == -backward.z and forward.z != 0
    assert forward.p == backward.p
    k = forward.discordant
    assert forward.p == pytest.approx(stats.binomtest(forward.n10, k, 0.5).pvalue)


def test_synthetic_v1_analysis_runs_and_swapping_runs_flips_the_gap() -> None:
    world = world_mod.build_world()
    _, m, h = matrix(world)
    result = audit.analyze_v1(m, h, seed=42, sign_flip_draws=2000, model_draws=2000)
    assert result["sets"]["common"] == 359
    assert result["errors"]["run1"][world.errors[0]] == "setup_cdp_timeout"
    assert result["errors"]["run1"][world.errors[1]] == "evaluator_month_out_of_range"
    audit.assert_public_safe(result)
    swapped = audit.V1Matrix(
        m.tasks,
        m.domain_of,
        m.v2,
        {t: "main" for t in m.tasks},
        m.v1,
        m.s2,
        m.s1,
        {t: (b, a) for t, (a, b) in m.flags.items()},
        m.web,
    )
    other = audit.analyze_v1(swapped, h, seed=42, sign_flip_draws=2000, model_draws=2000)
    assert other["decomposition"]["gap_pp"] == pytest.approx(-result["decomposition"]["gap_pp"])
    assert other["mcnemar"]["ge"]["C"]["z"] == pytest.approx(-result["mcnemar"]["ge"]["C"]["z"])


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def test_holm_matches_hand_computation() -> None:
    assert audit.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert audit.holm([0.5]) == [0.5]


def test_sign_flip_chunking_reproduces_a_single_draw() -> None:
    diffs = [1.0, -1.0, 0.5, 0.0, 1.0, 1.0, -0.25, 1.0]
    chunked = audit.sign_flip_p(diffs, np.random.default_rng(42), draws=20_000, chunk_rows=777)
    rng = np.random.default_rng(42)
    nonzero = np.abs(np.array([d for d in diffs if d]))
    signs = rng.choice([-1.0, 1.0], size=(20_000, nonzero.size))
    one_shot = float((np.abs((signs * nonzero).sum(1)) >= abs(sum(diffs)) - 1e-12).mean())
    assert chunked == one_shot


def test_variance_ratio_detects_a_run_effect_and_not_its_absence() -> None:
    rng = np.random.default_rng(42)
    p = rng.uniform(0.1, 0.9, size=400)
    null = (rng.random((400, 3)) < p[:, None]).astype(float)
    shifted = null.copy()
    shifted[:, 0] = (rng.random(400) < np.clip(p + 0.15, 0, 1)).astype(float)
    ratio_null = audit.pooled_variance_ratio([audit.two_way_variance_ratio(null)])
    ratio_shift = audit.pooled_variance_ratio([audit.two_way_variance_ratio(shifted)])
    assert ratio_null["ratio"] < 4 and ratio_null["df_runs"] == 2
    assert ratio_shift["ratio"] > 10 and ratio_shift["p_upper"] < 0.001


def test_mde_matches_closed_form() -> None:
    assert 100 * audit.mde_two_run_contrast(0.0993, 359) == pytest.approx(4.66, abs=0.01)


# --------------------------------------------------------------------------- #
# Public-repository safety
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "pattern"),
    [
        ("connect to 192.0.2.77 failed", "ipv4"),
        ("group sg-0123456789abcdef0", "aws_security_group"),
        ("subnet-0a1b2c3d4e5f6a7b8", "aws_subnet"),
        ("image ami-0123abcd", "aws_ami"),
        ("instance i-0abc1234def567890", "aws_instance"),
        ("arn:aws:iam::123456789012:user/x", "aws_account_id"),
        ("/home/someone/run", "home_path"),
        ("/Users/someone/run", "home_path"),
        ("fsx/someone/trajectories_tianbao/x", "shared_fs_path"),
        ("ws://host:9222/devtools/browser/1", "websocket_url"),
        ("https://cdn/x?X-Amz-Signature=abc", "signed_url"),
        ("AKIA" + "Z" * 16, "aws_access_key"),
    ],
)
def test_receipt_injection_is_caught(value: str, pattern: str) -> None:
    with pytest.raises(audit.PublicSafetyError, match=pattern):
        audit.assert_public_safe({"results": {"note": value}})
    with pytest.raises(audit.PublicSafetyError):
        audit.assert_public_safe({value: 1})
    assert pattern not in audit.public_safety_hits(audit.scrub(value))


def test_ordinary_receipt_values_are_not_flagged() -> None:
    clean = {
        "task": "06fe7178-4491-4589-810f-2e2bc9502122",
        "uuid_all_digits": "00000001-0000-4000-8000-123456789012",
        "p": 0.959588724584,
        "p_text": "0.959588724584",
        "sha": "a" * 64,
        "path": "program/preregistrations/q2-holo3-rerun-audit-v2.md",
        "version": "1.17.1",
    }
    audit.assert_public_safe(clean)
    assert audit.error_class(f"Flask not available at http://{world_mod.FAKE_PRIVATE_IP}:5000") == (
        "vm_flask_unavailable"
    )


# --------------------------------------------------------------------------- #
# Leaderboard and OpenCUA
# --------------------------------------------------------------------------- #


def _xlsx(rows: dict[int, dict[str, str]]) -> bytes:
    strings: list[str] = []
    sheet_rows = []
    for number, cells in sorted(rows.items()):
        parts = []
        for column, text in cells.items():
            strings.append(text)
            parts.append(f'<c r="{column}{number}" t="s"><v>{len(strings) - 1}</v></c>')
        sheet_rows.append(f'<row r="{number}">{"".join(parts)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    shared = "".join(f"<si><t>{s}</t></si>" for s in strings)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/sharedStrings.xml", f"<sst {ns}>{shared}</sst>")
        book.writestr(
            "xl/worksheets/sheet1.xml",
            f"<worksheet {ns}><sheetData>{''.join(sheet_rows)}</sheetData></worksheet>",
        )
    return buffer.getvalue()


def test_leaderboard_constants_check_and_rank() -> None:
    rows = world_mod.leaderboard_rows()
    parsed = osworld_source.read_xlsx_first_sheet(_xlsx(rows))
    assert parsed[139]["P"] == "41.55/47"
    assert audit.check_leaderboard_constants(parsed)["status"] == "PASS"
    parsed[140]["M"] = "31.97/44"
    result = audit.check_leaderboard_constants(parsed)
    assert result["status"] == "FAIL" and "chrome" in result["problems"][0]
    rank = audit.rank_by_group_mean(rows, "Holo3-35B-A3B", "100")
    assert rank["rank"] == 2 and rank["runs"] == 2


def test_opencua_turn_totals_control_and_reference() -> None:
    world = world_mod.build_world()
    ctx = context(world)
    sets = [audit.load_opencua(ctx, spec) for spec in audit.OPENCUA_ARCHIVES.values()]
    control = audit.opencua_leaderboard_control(sets)
    assert control["status"] == "PASS" and control["turns_checked"] == 18
    ref = audit.opencua_reference(sets, holo3_z=2.74, h_pairs=[{"z": 0.1}])
    assert ref["reference_pairs"] == 19
    assert ref["label"].startswith("EXPLORATORY")
    sets[0].turns["turn_1"][next(iter(sets[0].turns["turn_1"]))] += 1.0
    assert audit.opencua_leaderboard_control(sets)["status"] == "FAIL"


def test_git_blob_verification_rejects_tampered_config(tmp_path) -> None:
    good = json.dumps({"evaluator": {"func": "f"}}).encode()
    blob = osworld_source.git_blob_sha1(good)
    tree = json.dumps(
        {"truncated": False, "tree": [{"path": "a.json", "type": "blob", "sha": blob}]}
    )
    served = {"tree": tree.encode(), "file": good}

    def fetch(url: str) -> bytes:
        return served["tree"] if "/git/trees/" in url else served["file"]

    files = osworld_source.GitHubCommitFiles("o/r", "c" * 40, cache_dir=tmp_path, fetch=fetch)
    assert files.read("a.json") == good
    tampered = osworld_source.GitHubCommitFiles("o/r", "d" * 40, fetch=fetch)
    served["file"] = good + b" "
    with pytest.raises(osworld_source.SourceFetchError):
        tampered.read("a.json")
    with pytest.raises(osworld_source.SourceFetchError):
        osworld_source.fetch_pinned_file("u", "0" * 64, fetch=lambda url: b"x")
