from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tools import learning_public_anchor as anchor

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/publish-learning.yml"


def _policy_fixture():
    repository = {
        "full_name": "learner/public-proof",
        "private": False,
        "visibility": "public",
        "default_branch": "main",
    }
    ruleset = {
        "id": 42,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
    }
    effective = [
        {"type": "deletion", "ruleset_id": 42},
        {"type": "non_fast_forward", "ruleset_id": 42},
    ]
    immutable = {"enabled": True, "enforced_by_owner": False}
    return repository, ruleset, effective, immutable


def _verify_policy(repository, ruleset, effective, immutable):
    return anchor.verify_policy(
        repository,
        ruleset,
        effective,
        immutable,
        expected_repository="learner/public-proof",
        expected_ruleset_id=42,
    )


def test_policy_requires_active_no_bypass_ruleset_and_immutable_releases():
    policy = _verify_policy(*_policy_fixture())

    assert policy == {
        "schema_version": 1,
        "repository": "learner/public-proof",
        "default_branch": "main",
        "ruleset_id": 42,
        "rules": ["deletion", "non_fast_forward"],
        "immutable_releases": True,
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda _repo, ruleset, _effective, _immutable: ruleset.update(
                enforcement="evaluate"
            ),
            "active",
        ),
        (
            lambda _repo, ruleset, _effective, _immutable: ruleset.update(
                bypass_actors=[{"actor_type": "RepositoryRole", "actor_id": 5}]
            ),
            "bypass",
        ),
        (
            lambda _repo, ruleset, _effective, _immutable: ruleset.update(
                rules=[{"type": "deletion"}]
            ),
            "lacks",
        ),
        (
            lambda _repo, ruleset, _effective, _immutable: ruleset["conditions"][
                "ref_name"
            ].update(exclude=["refs/heads/main"]),
            "unconditionally",
        ),
        (
            lambda _repo, _ruleset, effective, _immutable: effective.clear(),
            "effective",
        ),
        (
            lambda _repo, _ruleset, _effective, immutable: immutable.update(
                enabled=False
            ),
            "not enabled",
        ),
    ],
)
def test_policy_fails_closed_for_weakened_github_controls(mutation, message):
    values = _policy_fixture()
    mutation(*values)

    with pytest.raises(anchor.AnchorError, match=message):
        _verify_policy(*values)


def _tag_ruleset_fixture():
    return {
        "id": 84,
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": ["refs/tags/aegis-proof-v1-*"],
                "exclude": [],
            }
        },
        "rules": [{"type": "deletion"}, {"type": "update"}],
    }


def test_tag_ruleset_forbids_every_update_without_blocking_creation():
    assert anchor.verify_tag_ruleset(
        _tag_ruleset_fixture(), expected_ruleset_id=84
    ) == {
        "schema_version": 1,
        "ruleset_id": 84,
        "pattern": "refs/tags/aegis-proof-v1-*",
        "rules": ["deletion", "update"],
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda ruleset: ruleset.update(enforcement="evaluate"), "active"),
        (
            lambda ruleset: ruleset.update(
                bypass_actors=[{"actor_type": "RepositoryRole", "actor_id": 5}]
            ),
            "bypass",
        ),
        (
            lambda ruleset: ruleset["conditions"]["ref_name"].update(
                include=["refs/tags/*"]
            ),
            "exactly",
        ),
        (
            lambda ruleset: ruleset.update(
                rules=[{"type": "deletion"}, {"type": "non_fast_forward"}]
            ),
            "update",
        ),
    ],
)
def test_tag_ruleset_fails_closed_for_a_movable_tag(mutation, message):
    ruleset = _tag_ruleset_fixture()
    mutation(ruleset)

    with pytest.raises(anchor.AnchorError, match=message):
        anchor.verify_tag_ruleset(ruleset, expected_ruleset_id=84)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(root: Path, message: str) -> str:
    return _git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    ) or _git(root, "rev-parse", "HEAD")


def _write_public_bundle(root: Path, sequence: int = 1) -> None:
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    ledger_lines = []
    for number in range(1, sequence + 1):
        ledger_lines.append(
            anchor.canonical_json_bytes(
                {
                    "schema_version": 1,
                    "sequence": number,
                    "day_id": f"J{number:03d}",
                }
            )
        )
    ledger = b"".join(ledger_lines)
    (docs / "ledger.jsonl").write_bytes(ledger)
    manifest = {
        "schema_version": 1,
        "artifacts": {"ledger.jsonl": {"sha256": _digest(ledger)}},
    }
    (docs / "manifest.json").write_bytes(anchor.canonical_json_bytes(manifest))
    (docs / "manifest.json.sig").write_text("test signature\n", encoding="utf-8")
    (docs / "signer.pub").write_text("test public key\n", encoding="utf-8")
    for name in (
        "index.html",
        "manifest.sha256",
        "public-proof.json",
        "public-proof.sha256",
        "signature-request.json",
    ):
        (docs / name).write_text(f"{name} sequence {sequence}\n", encoding="utf-8")


def _repository_with_plan(tmp_path: Path):
    root = tmp_path / "public-proof"
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(root)], check=True
    )
    (root / "README.md").write_text("public proof\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _commit(root, "Initialize")
    base = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", base)

    _write_public_bundle(root)
    _git(root, "add", "docs")
    _commit(root, "Publish J001")
    plan = anchor.prepare_plan(root, root / "docs", default_branch="main", created=True)
    return root, plan


def _digest(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _release(
    sequence: int,
    *,
    immutable: bool = True,
    draft: bool = False,
    commit: str = "a" * 40,
    artifacts: dict | None = None,
):
    tag = f"{anchor.ANCHOR_TAG_PREFIX}{sequence:06d}"
    if artifacts is None:
        artifacts = {
            name: {"sha256": f"sha256:{number:064x}", "size": number}
            for number, name in enumerate(anchor.ANCHOR_ASSETS, 1)
        }
    previous = (
        None
        if sequence == 1
        else {
            "sequence": sequence - 1,
            "tag": f"{anchor.ANCHOR_TAG_PREFIX}{sequence - 1:06d}",
            "public_commit": "b" * 40,
        }
    )
    return {
        "tag_name": tag,
        "name": tag,
        "draft": draft,
        "prerelease": False,
        "immutable": immutable,
        "published_at": None if draft else "2026-08-25T00:00:00Z",
        "body": anchor.canonical_json_bytes(
            {
                "schema_version": 1,
                "kind": anchor.ANCHOR_KIND,
                "sequence": sequence,
                "tag": tag,
                "public_commit": commit,
                "previous_anchor": previous,
                "artifacts": artifacts,
            }
        ).decode(),
        "assets": [
            {
                "name": name,
                "state": "uploaded",
                "digest": record["sha256"],
                "size": record["size"],
            }
            for name, record in artifacts.items()
        ],
    }


def _index_plan(sequence: int, branch_sequence: int, mode: str):
    return {
        "sequence": sequence,
        "branch_sequence": branch_sequence,
        "mode": mode,
    }


def test_release_index_accepts_absent_draft_published_recovery_and_current_states():
    create = _index_plan(2, 1, "create-or-recover")
    assert anchor.verify_release_index([_release(1)], create)["state"] == "absent"
    assert (
        anchor.verify_release_index(
            [_release(1), _release(2, immutable=False, draft=True)], create
        )["state"]
        == "draft"
    )
    assert (
        anchor.verify_release_index([_release(1), _release(2)], create)["state"]
        == "published-recovery"
    )
    verify = _index_plan(2, 2, "verify-existing")
    assert (
        anchor.verify_release_index([_release(1), _release(2)], verify)["state"]
        == "published-current"
    )


@pytest.mark.parametrize(
    "releases",
    [
        [_release(2)],
        [_release(1), _release(1)],
        [_release(1), _release(2), _release(3)],
        [_release(1, immutable=False)],
        [_release(1, draft=True, immutable=False)],
    ],
)
def test_release_index_rejects_gaps_duplicates_future_or_mutable_history(releases):
    with pytest.raises(anchor.AnchorError):
        anchor.verify_release_index(releases, _index_plan(2, 1, "create-or-recover"))


def test_prepare_plan_binds_direct_parent_tree_ledger_and_four_assets(tmp_path):
    root, plan = _repository_with_plan(tmp_path)

    assert plan["mode"] == "create-or-recover"
    assert plan["sequence"] == 1
    assert plan["branch_sequence"] == 0
    assert plan["candidate_commit"] == _git(root, "rev-parse", "HEAD")
    assert plan["expected_parent"] == _git(root, "rev-parse", "HEAD^")
    assert set(plan["artifacts"]) == set(anchor.ANCHOR_ASSETS)


def test_prepare_plan_rejects_non_allowlisted_changes(tmp_path):
    root, _plan = _repository_with_plan(tmp_path)
    base = _git(root, "rev-parse", "HEAD^")
    _git(root, "reset", "--soft", base)
    (root / "unexpected.txt").write_text("not public\n", encoding="utf-8")
    _git(root, "add", "unexpected.txt")
    _commit(root, "Publish with unexpected file")

    with pytest.raises(anchor.AnchorError, match="non-allowlisted"):
        anchor.prepare_plan(root, root / "docs", default_branch="main", created=True)


def _release_from_plan(plan, public_commit):
    payload = anchor.anchor_payload(plan, public_commit, None)
    release = _release(
        plan["sequence"], commit=public_commit, artifacts=plan["artifacts"]
    )
    release["body"] = anchor.canonical_json_bytes(payload).decode()
    return release


def _copy_assets(source: Path, target: Path) -> None:
    target.mkdir()
    for name in anchor.ANCHOR_ASSETS:
        shutil.copyfile(source / name, target / name)


def test_current_release_verification_binds_tag_commit_tree_parent_and_assets(tmp_path):
    root, plan = _repository_with_plan(tmp_path)
    release = _release_from_plan(plan, plan["candidate_commit"])
    downloads = tmp_path / "downloads"
    _copy_assets(root / "docs", downloads)

    anchor.verify_current_release(
        release,
        plan,
        root,
        public_commit=plan["candidate_commit"],
        previous_commit=None,
        asset_directory=downloads,
    )


@pytest.mark.parametrize("tamper", ["body", "metadata", "download"])
def test_current_release_verification_rejects_every_asset_binding_tamper(
    tmp_path, tamper
):
    root, plan = _repository_with_plan(tmp_path)
    release = _release_from_plan(plan, plan["candidate_commit"])
    downloads = tmp_path / "downloads"
    _copy_assets(root / "docs", downloads)
    if tamper == "body":
        payload = json.loads(release["body"])
        payload["artifacts"]["ledger.jsonl"]["size"] += 1
        release["body"] = json.dumps(payload)
    elif tamper == "metadata":
        release["assets"][0]["digest"] = f"sha256:{'0' * 64}"
    else:
        (downloads / "ledger.jsonl").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(anchor.AnchorError):
        anchor.verify_current_release(
            release,
            plan,
            root,
            public_commit=plan["candidate_commit"],
            previous_commit=None,
            asset_directory=downloads,
        )


def test_release_body_is_monotone_and_names_previous_anchor():
    plan = {
        "sequence": 2,
        "artifacts": {
            name: {"sha256": f"sha256:{number:064x}", "size": number}
            for number, name in enumerate(anchor.ANCHOR_ASSETS, 1)
        },
    }

    payload = anchor.anchor_payload(plan, "a" * 40, "b" * 40)

    assert payload["tag"] == "aegis-proof-v1-000002"
    assert payload["public_commit"] == "a" * 40
    assert payload["previous_anchor"] == {
        "sequence": 1,
        "tag": "aegis-proof-v1-000001",
        "public_commit": "b" * 40,
    }


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(anchor.AnchorError, match="duplicate"):
        anchor._load_json_bytes(b'{"enabled":true,"enabled":false}', "response")


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen unavailable")
def test_ed25519_sshsig_is_byte_identical_for_safe_recovery(tmp_path):
    key = tmp_path / "signer"
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(anchor.canonical_json_bytes({"schema_version": 1}))
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
    )

    signatures = []
    for _attempt in range(2):
        subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "sign",
                "-f",
                str(key),
                "-n",
                "aegis-learning-manifest",
                str(manifest),
            ],
            check=True,
            capture_output=True,
        )
        signature = manifest.with_suffix(".json.sig")
        signatures.append(signature.read_bytes())
        signature.unlink()

    assert signatures[0] == signatures[1]


def test_workflow_uses_fresh_jobs_and_data_only_artifacts_for_each_secret():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    document = yaml.safe_load(workflow)
    jobs = document["jobs"]

    assert list(jobs) == ["build", "sign", "policy", "publish"]
    assert jobs["sign"]["needs"] == "build"
    assert jobs["policy"]["needs"] == ["build", "sign"]
    assert jobs["publish"]["needs"] == ["build", "sign", "policy"]
    assert "secrets." not in json.dumps(jobs["build"])
    assert "PUBLIC_PROOF_SIGNING_KEY" in json.dumps(jobs["sign"])
    assert "PUBLIC_PROOF_POLICY_TOKEN" not in json.dumps(jobs["sign"])
    assert "PUBLIC_PROOF_TOKEN" not in json.dumps(jobs["sign"])
    assert "PUBLIC_PROOF_POLICY_TOKEN" in json.dumps(jobs["policy"])
    assert "PUBLIC_PROOF_SIGNING_KEY" not in json.dumps(jobs["policy"])
    assert "PUBLIC_PROOF_TOKEN" not in json.dumps(jobs["policy"])
    assert "PUBLIC_PROOF_TOKEN" in json.dumps(jobs["publish"])
    assert "PUBLIC_PROOF_POLICY_TOKEN" not in json.dumps(jobs["publish"])
    assert "PUBLIC_PROOF_SIGNING_KEY" not in json.dumps(jobs["publish"])
    assert workflow.count("${{ secrets.PUBLIC_PROOF_POLICY_TOKEN }}") == 1
    assert workflow.count("${{ secrets.PUBLIC_PROOF_TOKEN }}") == 1
    assert workflow.count("${{ secrets.PUBLIC_PROOF_SIGNING_KEY }}") == 1
    for job_name in ("sign", "policy", "publish"):
        assert "source/tools/" not in json.dumps(jobs[job_name])
        assert "python3" not in json.dumps(jobs[job_name])
    assert workflow.count("actions/upload-artifact@") == 2
    assert workflow.count("actions/download-artifact@") == 2
    assert workflow.count("persist-credentials: false") == 2
    assert workflow.count("fetch-depth: 0") == 2
    assert workflow.count('test "$signer_type" = ssh-ed25519') == 2


def test_workflow_requires_distinct_public_source_and_target_repositories():
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    boundary = document["jobs"]["build"]["steps"][0]["run"]

    assert 'test "${SOURCE_REPOSITORY,,}" != "${PUBLIC_REPOSITORY,,}"' in boundary
    assert '--json visibility,isPrivate' in boundary
    assert 'test "$(jq -r .visibility <<< "$source_metadata")" = "PUBLIC"' in boundary
    assert 'test "$(jq -r .isPrivate <<< "$source_metadata")" = "false"' in boundary
    assert 'test "$(jq -r .visibility <<< "$target_metadata")" = "PUBLIC"' in boundary
    assert '"PRIVATE"' not in boundary


def test_workflow_hardcoded_publisher_hashes_match_the_executed_sources():
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))

    assert (
        document["env"]["PUBLISHER_SHA256"]
        == hashlib.sha256(
            (REPOSITORY_ROOT / "tools/learning_publish.py").read_bytes()
        ).hexdigest()
    )
    assert (
        document["env"]["LEARN_CORE_SHA256"]
        == hashlib.sha256((REPOSITORY_ROOT / "tools/learn.py").read_bytes()).hexdigest()
    )
    assert (
        document["env"]["PUBLIC_TEMPLATE_SHA256"]
        == hashlib.sha256(
            (REPOSITORY_ROOT / "site/public-proof.html").read_bytes()
        ).hexdigest()
    )
    build = json.dumps(document["jobs"]["build"])
    assert "env -i" in build
    assert "python3 -B -I" in build
    assert "source/site/public-proof.html" in build
    assert "$trusted/public-proof.html" in build
    assert build.count("--template") == 2


def test_workflow_enforces_policy_and_release_before_fast_forward():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    document = yaml.safe_load(workflow)
    policy_steps = document["jobs"]["policy"]["steps"]
    policy = policy_steps[0]["run"]
    steps = document["jobs"]["publish"]["steps"]
    mutation = next(
        step["run"]
        for step in steps
        if step["name"] == "Anchor immutable release and advance branch"
    )

    assert "rulesets/$BRANCH_RULESET_ID" in policy
    assert "rulesets/$TAG_RULESET_ID" in policy
    assert "rules/branches/$encoded_branch" in policy
    assert "rules/tags/" not in policy
    assert '.conditions.ref_name.include == ["refs/tags/aegis-proof-v1-*"]' in policy
    assert '[.rules[].type] | contains(["deletion", "update"])' in policy
    assert policy.count(".bypass_actors == []") == 2
    assert "immutable-releases" in policy
    assert "X-GitHub-Api-Version: $api_version" in policy
    assert mutation.index("gh release create") < mutation.index("--draft=false")
    assert mutation.index("--draft=false") < mutation.index(
        'post_release_tag_state="$(remote_tag_state "$tag")"'
    )
    assert mutation.index("post_release_tag_state") < mutation.rindex(
        "$anchor_commit:refs/heads/$PUBLIC_DEFAULT_BRANCH"
    )
    assert "$anchor_commit:refs/tags/$tag" in mutation
    assert "git -c credential.helper= push origin" in mutation
    assert '[[ "$POLICY_TOKEN_SHA256" =~ ^[0-9a-f]{64}$ ]]' in mutation
    assert "core.hooksPath" in json.dumps(document["jobs"]["publish"])
    assert "BASH_ENV" in mutation
    assert "--force" not in mutation


def test_signed_manifest_covers_every_public_payload_at_both_boundaries():
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    sign_validation = document["jobs"]["sign"]["steps"][1]["run"]
    publish_validation = document["jobs"]["publish"]["steps"][2]["run"]

    for validation in (sign_validation, publish_validation):
        assert "manifest_artifacts=(" in validation
        for name in (
            "index.html",
            "ledger.jsonl",
            "public-proof.json",
            "public-proof.sha256",
        ):
            assert name in validation
        assert ".artifacts[$name].sha256" in validation
        assert ".ledger_head_sha256" in validation
        assert ".proof_sha256" in validation
        assert 'payload: "manifest.json"' in validation


def test_candidate_commit_blobs_are_checked_before_the_immutable_plan(tmp_path):
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assembly = document["jobs"]["publish"]["steps"][2]["run"]
    show_blob = 'git -C "$repository" show "$candidate_commit:docs/$name"'
    compare_blob = '| cmp -- - "$incoming/$name"'
    assert show_blob in assembly
    assert compare_blob in assembly
    assert assembly.index(show_blob) < assembly.index(compare_blob)
    assert assembly.index(compare_blob) < assembly.index(
        'plan="$RUNNER_TEMP/anchor-plan.json"'
    )

    root = tmp_path / "filtered-public"
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(root)], check=True
    )
    _git(root, "config", "filter.proof.clean", "sed s/incoming/transformed/g")
    _git(root, "config", "filter.proof.smudge", "cat")
    (root / ".gitattributes").write_text(
        "docs/index.html filter=proof\n", encoding="utf-8"
    )
    _git(root, "add", ".gitattributes")
    _commit(root, "Configure target clean filter")
    incoming = tmp_path / "index.html"
    incoming.write_bytes(b"incoming bytes\n")
    docs = root / "docs"
    docs.mkdir()
    shutil.copy2(incoming, docs / "index.html")
    _git(root, "add", "docs/index.html")
    _commit(root, "Publish filtered candidate")
    candidate = _git(root, "rev-parse", "HEAD")
    blob = subprocess.run(
        ["git", "-C", str(root), "show", f"{candidate}:docs/index.html"],
        check=True,
        capture_output=True,
    ).stdout

    assert blob == b"transformed bytes\n"
    assert blob != incoming.read_bytes()


def test_every_workflow_shell_block_parses_as_bash():
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    blocks = [
        step["run"]
        for job in document["jobs"].values()
        for step in job["steps"]
        if "run" in step
    ]

    for block in blocks:
        result = subprocess.run(
            ["bash", "-n"], input=block, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stderr


def test_release_fixture_copy_does_not_hide_mutation_between_cases():
    release = _release(1)
    changed = copy.deepcopy(release)
    changed["assets"][0]["size"] += 1

    assert release["assets"][0]["size"] != changed["assets"][0]["size"]
