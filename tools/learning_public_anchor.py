#!/usr/bin/env python3
"""Validate models used by the public proof anchoring protocol.

This module deliberately has no network client.  It is an offline reference
implementation for unit tests and operator diagnostics; secret-bearing workflow
jobs express their checks directly and never execute a helper from the source
repository.  All remote mutations remain in the workflow itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ANCHOR_KIND = "aegis-learning-proof-release-anchor"
ANCHOR_TAG_PREFIX = "aegis-proof-v1-"
ANCHOR_ASSETS = (
    "ledger.jsonl",
    "manifest.json",
    "manifest.json.sig",
    "signer.pub",
)
PUBLIC_COMMIT_FILES = {
    "docs/index.html",
    "docs/ledger.jsonl",
    "docs/manifest.json",
    "docs/manifest.sha256",
    "docs/public-proof.json",
    "docs/public-proof.sha256",
    "docs/signature-request.json",
    "docs/manifest.json.sig",
    "docs/signer.pub",
}
REQUIRED_RULES = {"deletion", "non_fast_forward"}
REQUIRED_TAG_RULES = {"deletion", "update"}
TAG_RULESET_PATTERN = f"refs/tags/{ANCHOR_TAG_PREFIX}*"
MAX_JSON_BYTES = 8_000_000
GIT_OID_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
TAG_RE = re.compile(rf"{re.escape(ANCHOR_TAG_PREFIX)}([0-9]{{6}})")


class AnchorError(ValueError):
    """Raised when a public proof policy or anchor is not trustworthy."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize an anchor deterministically."""

    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise AnchorError("value is not representable as canonical JSON") from exc
    return rendered.encode("utf-8") + b"\n"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AnchorError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AnchorError(f"non-finite JSON value is forbidden: {value}")


def _read_regular(path: Path, label: str, limit: int = MAX_JSON_BYTES) -> bytes:
    if path.is_symlink():
        raise AnchorError(f"{label} must not be a symbolic link")
    try:
        file_stat = path.stat()
    except FileNotFoundError as exc:
        raise AnchorError(f"{label} does not exist") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise AnchorError(f"{label} must be a regular file")
    if file_stat.st_size > limit:
        raise AnchorError(f"{label} exceeds its size limit")
    return path.read_bytes()


def _load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except AnchorError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnchorError(f"{label} is not valid UTF-8 JSON") from exc


def load_json(path: Path, label: str) -> Any:
    return _load_json_bytes(_read_regular(path, label), label)


def _normalise_oid(value: Any, label: str) -> str:
    if not isinstance(value, str) or GIT_OID_RE.fullmatch(value) is None:
        raise AnchorError(f"{label} is not a complete Git object id")
    return value


def _sha256(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _tag(sequence: int) -> str:
    if sequence < 1 or sequence > 999_999:
        raise AnchorError("anchor sequence is outside the supported range")
    return f"{ANCHOR_TAG_PREFIX}{sequence:06d}"


def _valid_branch(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise AnchorError("the public default branch is invalid")
    if (
        value.startswith(("/", "-"))
        or value.endswith(("/", ".", ".lock"))
        or ".." in value
        or "//" in value
        or "@{" in value
        or any(character.isspace() or ord(character) < 32 for character in value)
        or any(character in "~^:?*[\\" for character in value)
    ):
        raise AnchorError("the public default branch is invalid")
    return value


def verify_policy(
    repository: dict[str, Any],
    ruleset: dict[str, Any],
    effective_rules: list[Any],
    immutable_releases: dict[str, Any],
    *,
    expected_repository: str,
    expected_ruleset_id: int,
) -> dict[str, Any]:
    """Verify the GitHub policy snapshot required before any target mutation."""

    if not isinstance(repository, dict):
        raise AnchorError("repository API response must be an object")
    full_name = repository.get("full_name")
    if (
        not isinstance(full_name, str)
        or full_name.casefold() != expected_repository.casefold()
    ):
        raise AnchorError("repository API response names an unexpected target")
    if (
        repository.get("private") is not False
        or repository.get("visibility") != "public"
    ):
        raise AnchorError("the public proof repository is not public")
    default_branch = _valid_branch(repository.get("default_branch"))

    if not isinstance(ruleset, dict) or ruleset.get("id") != expected_ruleset_id:
        raise AnchorError("the configured repository ruleset was not returned")
    if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
        raise AnchorError("the public ruleset is not an active branch ruleset")
    if ruleset.get("bypass_actors") != []:
        raise AnchorError("the public ruleset has a bypass actor")

    conditions = ruleset.get("conditions")
    ref_names = conditions.get("ref_name") if isinstance(conditions, dict) else None
    if not isinstance(ref_names, dict):
        raise AnchorError("the public ruleset has no ref-name condition")
    include = ref_names.get("include")
    exclude = ref_names.get("exclude")
    accepted_targets = {"~ALL", "~DEFAULT_BRANCH", f"refs/heads/{default_branch}"}
    if (
        not isinstance(include, list)
        or not all(isinstance(item, str) for item in include)
        or not accepted_targets.intersection(include)
        or exclude != []
    ):
        raise AnchorError(
            "the public ruleset does not unconditionally include the default branch"
        )

    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        raise AnchorError("the public ruleset has no rule list")
    configured_types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
    if not REQUIRED_RULES <= configured_types:
        raise AnchorError("the public ruleset lacks deletion or non-fast-forward rules")

    if not isinstance(effective_rules, list):
        raise AnchorError("effective branch rules must be a list")
    effective_types = {
        rule.get("type")
        for rule in effective_rules
        if isinstance(rule, dict) and rule.get("ruleset_id") == expected_ruleset_id
    }
    if not REQUIRED_RULES <= effective_types:
        raise AnchorError(
            "the configured ruleset is not effective on the default branch"
        )

    if (
        not isinstance(immutable_releases, dict)
        or immutable_releases.get("enabled") is not True
    ):
        raise AnchorError("immutable GitHub releases are not enabled")

    return {
        "schema_version": 1,
        "repository": full_name,
        "default_branch": default_branch,
        "ruleset_id": expected_ruleset_id,
        "rules": sorted(REQUIRED_RULES),
        "immutable_releases": True,
    }


def verify_tag_ruleset(
    ruleset: dict[str, Any], *, expected_ruleset_id: int
) -> dict[str, Any]:
    """Verify the exact no-update policy protecting deterministic anchor tags."""

    if not isinstance(ruleset, dict) or ruleset.get("id") != expected_ruleset_id:
        raise AnchorError("the configured tag ruleset was not returned")
    if ruleset.get("target") != "tag" or ruleset.get("enforcement") != "active":
        raise AnchorError("the tag ruleset is not active")
    if ruleset.get("bypass_actors") != []:
        raise AnchorError("the tag ruleset has a bypass actor")
    conditions = ruleset.get("conditions")
    ref_names = conditions.get("ref_name") if isinstance(conditions, dict) else None
    if not isinstance(ref_names, dict) or ref_names != {
        "include": [TAG_RULESET_PATTERN],
        "exclude": [],
    }:
        raise AnchorError("the tag ruleset does not cover exactly the anchor tags")
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        raise AnchorError("the tag ruleset has no rule list")
    configured_types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
    if not REQUIRED_TAG_RULES <= configured_types:
        raise AnchorError("the tag ruleset permits deletion or update")
    return {
        "schema_version": 1,
        "ruleset_id": expected_ruleset_id,
        "pattern": TAG_RULESET_PATTERN,
        "rules": sorted(REQUIRED_TAG_RULES),
    }


def _git(
    repository: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=False,
        capture_output=True,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise AnchorError(f"git {' '.join(args)} failed: {message}")
    return result


def _git_text(repository: Path, *args: str) -> str:
    return _git(repository, *args).stdout.decode("ascii", errors="strict").strip()


def _parse_ledger(raw: bytes, label: str) -> int:
    if not raw or not raw.endswith(b"\n"):
        raise AnchorError(f"{label} is empty or has an incomplete final entry")
    lines = raw.splitlines(keepends=True)
    for expected, line in enumerate(lines, 1):
        entry = _load_json_bytes(line, f"{label} entry {expected}")
        if not isinstance(entry, dict) or entry.get("sequence") != expected:
            raise AnchorError(f"{label} sequence is not contiguous")
        if canonical_json_bytes(entry) != line:
            raise AnchorError(f"{label} entry {expected} is not canonical JSON")
    return len(lines)


def _ledger_at_commit(repository: Path, commit: str) -> tuple[bytes, int]:
    result = _git(repository, "show", f"{commit}:docs/ledger.jsonl", check=False)
    if result.returncode != 0:
        return b"", 0
    return result.stdout, _parse_ledger(result.stdout, "base ledger")


def _commit_parents(repository: Path, commit: str) -> list[str]:
    line = _git_text(repository, "rev-list", "--parents", "-n", "1", commit)
    fields = line.split()
    if not fields or fields[0] != commit:
        raise AnchorError("Git returned an inconsistent commit ancestry")
    return fields[1:]


def _asset_records(docs: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for name in ANCHOR_ASSETS:
        raw = _read_regular(docs / name, name)
        records[name] = {"sha256": _sha256(raw), "size": len(raw)}
    return records


def prepare_plan(
    repository: Path,
    docs: Path,
    *,
    default_branch: str,
    created: bool,
) -> dict[str, Any]:
    """Build a deterministic local transaction plan after the proof commit."""

    default_branch = _valid_branch(default_branch)
    if repository.is_symlink() or docs.is_symlink():
        raise AnchorError("repository and docs paths must not be symbolic links")
    if docs.resolve().parent != repository.resolve():
        raise AnchorError(
            "the publication docs directory must belong to the repository"
        )
    if _git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout:
        raise AnchorError("the public proof checkout is not clean after its commit")

    head = _normalise_oid(_git_text(repository, "rev-parse", "HEAD^{commit}"), "HEAD")
    tree = _normalise_oid(
        _git_text(repository, "rev-parse", "HEAD^{tree}"), "HEAD tree"
    )
    remote_ref = f"refs/remotes/origin/{default_branch}"
    base = _normalise_oid(
        _git_text(repository, "rev-parse", f"{remote_ref}^{{commit}}"),
        "remote default branch",
    )
    parents = _commit_parents(repository, head)

    ledger = _read_regular(docs / "ledger.jsonl", "ledger.jsonl")
    sequence = _parse_ledger(ledger, "ledger.jsonl")
    base_ledger, branch_sequence = _ledger_at_commit(repository, base)
    if base_ledger and not ledger.startswith(base_ledger):
        raise AnchorError(
            "the candidate ledger does not preserve the remote ledger prefix"
        )

    if created:
        if head == base or parents != [base] or sequence != branch_sequence + 1:
            raise AnchorError(
                "a new proof commit must be the direct next ledger commit "
                "after the branch"
            )
        changed = set(
            _git_text(
                repository, "diff-tree", "--no-commit-id", "--name-only", "-r", head
            ).splitlines()
        )
        if not changed or not changed <= PUBLIC_COMMIT_FILES:
            raise AnchorError("the proof commit changes a non-allowlisted public path")
        required_changes = {
            "docs/ledger.jsonl",
            "docs/manifest.json",
            "docs/manifest.json.sig",
        }
        if required_changes - changed:
            raise AnchorError("the proof commit does not update its ledger signature")
        mode = "create-or-recover"
        expected_parent = base
    else:
        if head != base or sequence != branch_sequence:
            raise AnchorError(
                "an unchanged publication must equal the remote default branch"
            )
        if sequence < 1:
            raise AnchorError("an empty public ledger has no release anchor to verify")
        mode = "verify-existing"
        if len(parents) > 1:
            raise AnchorError("a public proof commit must not be a merge commit")
        expected_parent = parents[0] if parents else None

    for name in ANCHOR_ASSETS:
        committed = _git(repository, "show", f"{head}:docs/{name}").stdout
        local = _read_regular(docs / name, name)
        if committed != local:
            raise AnchorError(f"{name} is not byte-identical to the proof commit")

    manifest_raw = _read_regular(docs / "manifest.json", "manifest.json")
    manifest = _load_json_bytes(manifest_raw, "manifest.json")
    if canonical_json_bytes(manifest) != manifest_raw:
        raise AnchorError("manifest.json is not canonical JSON")
    ledger_record = (
        manifest.get("artifacts", {}).get("ledger.jsonl")
        if isinstance(manifest, dict)
        else None
    )
    if ledger_record != {"sha256": _sha256(ledger)}:
        raise AnchorError("manifest.json does not cover ledger.jsonl")

    return {
        "schema_version": 1,
        "mode": mode,
        "default_branch": default_branch,
        "sequence": sequence,
        "branch_sequence": branch_sequence,
        "tag": _tag(sequence),
        "previous_tag": _tag(sequence - 1) if sequence > 1 else None,
        "candidate_commit": head,
        "candidate_tree": tree,
        "branch_commit": base,
        "expected_parent": expected_parent,
        "artifacts": _asset_records(docs),
    }


def anchor_payload(
    plan: dict[str, Any], public_commit: str, previous_commit: str | None
) -> dict[str, Any]:
    sequence = plan.get("sequence")
    if not isinstance(sequence, int) or sequence < 1:
        raise AnchorError("plan has an invalid sequence")
    public_commit = _normalise_oid(public_commit, "public commit")
    if sequence == 1:
        if previous_commit is not None:
            raise AnchorError("the first anchor must not name a previous commit")
        previous: dict[str, Any] | None = None
    else:
        if previous_commit is None:
            raise AnchorError("a non-initial anchor must name its previous commit")
        previous = {
            "sequence": sequence - 1,
            "tag": _tag(sequence - 1),
            "public_commit": _normalise_oid(previous_commit, "previous commit"),
        }
    artifacts = plan.get("artifacts")
    _validate_artifact_records(artifacts, "plan artifacts")
    return {
        "schema_version": 1,
        "kind": ANCHOR_KIND,
        "sequence": sequence,
        "tag": _tag(sequence),
        "public_commit": public_commit,
        "previous_anchor": previous,
        "artifacts": artifacts,
    }


def _normalise_releases(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise AnchorError("release index must be a JSON list")
    if value and all(isinstance(page, list) for page in value):
        value = [release for page in value for release in page]
    if not all(isinstance(release, dict) for release in value):
        raise AnchorError("release index contains a non-object entry")
    return value


def verify_release_index(releases_value: Any, plan: dict[str, Any]) -> dict[str, Any]:
    """Reject gaps, duplicates, future anchors and ambiguous draft states."""

    releases = _normalise_releases(releases_value)
    sequence = plan.get("sequence")
    branch_sequence = plan.get("branch_sequence")
    mode = plan.get("mode")
    if not isinstance(sequence, int) or not isinstance(branch_sequence, int):
        raise AnchorError("plan sequence fields are invalid")
    by_sequence: dict[int, dict[str, Any]] = {}
    for release in releases:
        tag = release.get("tag_name")
        if not isinstance(tag, str):
            continue
        match = TAG_RE.fullmatch(tag)
        if match is None:
            continue
        release_sequence = int(match.group(1))
        if release_sequence in by_sequence:
            raise AnchorError("the release index contains a duplicate anchor sequence")
        if release.get("name") != tag or release.get("prerelease") is not False:
            raise AnchorError(
                "an anchor release has a non-canonical name or prerelease state"
            )
        by_sequence[release_sequence] = release

    if by_sequence and set(by_sequence) != set(range(1, max(by_sequence) + 1)):
        raise AnchorError("the release anchor sequence has a gap")
    if any(item > sequence for item in by_sequence):
        raise AnchorError(
            "the release index contains an anchor ahead of the transaction"
        )

    target = by_sequence.get(sequence)
    for item_sequence, release in by_sequence.items():
        if release.get("draft") is True:
            if item_sequence != sequence or mode != "create-or-recover":
                raise AnchorError("only the current recovery anchor may be a draft")
            if release.get("immutable") is True:
                raise AnchorError("a draft release cannot be treated as immutable")
        elif (
            release.get("draft") is not False
            or release.get("immutable") is not True
            or not isinstance(release.get("published_at"), str)
        ):
            raise AnchorError("a published anchor release is not immutable")

    if mode == "create-or-recover":
        if sequence != branch_sequence + 1:
            raise AnchorError("create/recovery plan is not one sequence ahead")
        required_published = set(range(1, branch_sequence + 1))
        actual_published = {
            item
            for item, release in by_sequence.items()
            if release.get("draft") is False
        }
        if actual_published not in (
            required_published,
            required_published | {sequence},
        ):
            raise AnchorError("published releases do not match the branch prefix")
        state = (
            "absent"
            if target is None
            else "draft"
            if target.get("draft") is True
            else "published-recovery"
        )
    elif mode == "verify-existing":
        if branch_sequence != sequence:
            raise AnchorError("verification plan does not match its branch sequence")
        if target is None or target.get("draft") is not False:
            raise AnchorError("the branch head has no immutable release anchor")
        if set(by_sequence) != set(range(1, sequence + 1)):
            raise AnchorError("release anchors do not exactly match the branch ledger")
        state = "published-current"
    else:
        raise AnchorError("plan has an unknown transaction mode")

    return {
        "schema_version": 1,
        "state": state,
        "sequence": sequence,
        "tag": _tag(sequence),
    }


def _validate_artifact_records(value: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != set(ANCHOR_ASSETS):
        raise AnchorError(f"{label} does not contain the exact anchor asset set")
    for name, record in value.items():
        if not isinstance(record, dict) or set(record) != {"sha256", "size"}:
            raise AnchorError(f"{label}.{name} has an invalid schema")
        digest = record.get("sha256")
        size = record.get("size")
        if (
            not isinstance(digest, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            raise AnchorError(f"{label}.{name} has an invalid digest or size")
    return value


def _release_payload(release: dict[str, Any]) -> dict[str, Any]:
    body = release.get("body")
    if not isinstance(body, str):
        raise AnchorError("anchor release body is missing")
    payload = _load_json_bytes(body.encode("utf-8"), "anchor release body")
    if not isinstance(payload, dict):
        raise AnchorError("anchor release body must be a JSON object")
    return payload


def _verify_release_assets(
    release: dict[str, Any],
    payload: dict[str, Any],
    asset_directory: Path,
    expected: dict[str, dict[str, Any]],
) -> None:
    _validate_artifact_records(expected, "expected artifacts")
    if payload.get("artifacts") != expected:
        raise AnchorError("anchor body does not bind the expected artifacts")
    assets = release.get("assets")
    if not isinstance(assets, list) or not all(
        isinstance(item, dict) for item in assets
    ):
        raise AnchorError("anchor release has an invalid asset list")
    by_name = {asset.get("name"): asset for asset in assets}
    if len(by_name) != len(assets) or set(by_name) != set(ANCHOR_ASSETS):
        raise AnchorError("anchor release does not have the exact asset set")
    if asset_directory.is_symlink() or not asset_directory.is_dir():
        raise AnchorError("downloaded asset directory is invalid")
    if {path.name for path in asset_directory.iterdir()} != set(ANCHOR_ASSETS):
        raise AnchorError("downloaded release has an unexpected or missing asset")
    for name, record in expected.items():
        asset = by_name[name]
        if (
            asset.get("state") != "uploaded"
            or asset.get("size") != record["size"]
            or asset.get("digest") != record["sha256"]
        ):
            raise AnchorError(f"GitHub metadata does not bind {name}")
        raw = _read_regular(asset_directory / name, f"downloaded {name}")
        if len(raw) != record["size"] or _sha256(raw) != record["sha256"]:
            raise AnchorError(f"downloaded anchor asset {name} is corrupt")


def _verify_published_release_envelope(
    release: dict[str, Any], sequence: int, public_commit: str
) -> dict[str, Any]:
    tag = _tag(sequence)
    if (
        release.get("tag_name") != tag
        or release.get("name") != tag
        or release.get("draft") is not False
        or release.get("prerelease") is not False
        or release.get("immutable") is not True
        or not isinstance(release.get("published_at"), str)
    ):
        raise AnchorError("release is not the expected published immutable anchor")
    payload = _release_payload(release)
    if (
        payload.get("schema_version") != 1
        or payload.get("kind") != ANCHOR_KIND
        or payload.get("sequence") != sequence
        or payload.get("tag") != tag
        or payload.get("public_commit") != public_commit
    ):
        raise AnchorError("release body does not identify its immutable tag and commit")
    return payload


def verify_current_release(
    release: dict[str, Any],
    plan: dict[str, Any],
    repository: Path,
    *,
    public_commit: str,
    previous_commit: str | None,
    asset_directory: Path,
) -> None:
    """Verify a current/recovery release against the candidate tree and assets."""

    sequence = plan.get("sequence")
    if not isinstance(sequence, int):
        raise AnchorError("plan sequence is invalid")
    public_commit = _normalise_oid(public_commit, "release tag commit")
    payload = _verify_published_release_envelope(release, sequence, public_commit)
    expected_payload = anchor_payload(plan, public_commit, previous_commit)
    if payload != expected_payload:
        raise AnchorError("release body differs from the expected anchor payload")

    commit_tree = _normalise_oid(
        _git_text(repository, "rev-parse", f"{public_commit}^{{tree}}"),
        "release commit tree",
    )
    if commit_tree != plan.get("candidate_tree"):
        raise AnchorError("release commit tree differs from the candidate proof tree")
    parents = _commit_parents(repository, public_commit)
    expected_parent = plan.get("expected_parent")
    expected_parents = [] if expected_parent is None else [expected_parent]
    if parents != expected_parents:
        raise AnchorError("release commit is not the direct expected ledger successor")

    artifacts = _validate_artifact_records(plan.get("artifacts"), "plan artifacts")
    _verify_release_assets(release, payload, asset_directory, artifacts)


def verify_predecessor_release(
    release: dict[str, Any],
    *,
    sequence: int,
    public_commit: str,
    asset_directory: Path,
) -> None:
    """Verify the immediate immutable predecessor using its self-bound assets."""

    public_commit = _normalise_oid(public_commit, "predecessor tag commit")
    payload = _verify_published_release_envelope(release, sequence, public_commit)
    previous = payload.get("previous_anchor")
    if sequence == 1:
        if previous is not None:
            raise AnchorError("the first immutable anchor has a predecessor")
    elif (
        not isinstance(previous, dict)
        or set(previous) != {"sequence", "tag", "public_commit"}
        or previous.get("sequence") != sequence - 1
        or previous.get("tag") != _tag(sequence - 1)
        or GIT_OID_RE.fullmatch(str(previous.get("public_commit"))) is None
    ):
        raise AnchorError("predecessor anchor body breaks the monotone chain")
    expected = _validate_artifact_records(
        payload.get("artifacts"), "predecessor artifacts"
    )
    _verify_release_assets(release, payload, asset_directory, expected)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(path, canonical_json_bytes(value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate public proof release policies and anchor snapshots."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    policy = commands.add_parser("verify-policy")
    policy.add_argument("--repository-json", required=True, type=Path)
    policy.add_argument("--ruleset-json", required=True, type=Path)
    policy.add_argument("--effective-rules-json", required=True, type=Path)
    policy.add_argument("--immutable-json", required=True, type=Path)
    policy.add_argument("--expected-repository", required=True)
    policy.add_argument("--expected-ruleset-id", required=True, type=int)
    policy.add_argument("--output", required=True, type=Path)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--repository", required=True, type=Path)
    prepare.add_argument("--docs", required=True, type=Path)
    prepare.add_argument("--default-branch", required=True)
    prepare.add_argument("--created", required=True, choices=("true", "false"))
    prepare.add_argument("--output", required=True, type=Path)

    release_index = commands.add_parser("verify-release-index")
    release_index.add_argument("--releases-json", required=True, type=Path)
    release_index.add_argument("--plan", required=True, type=Path)
    release_index.add_argument("--output", required=True, type=Path)

    render = commands.add_parser("render-body")
    render.add_argument("--plan", required=True, type=Path)
    render.add_argument("--public-commit", required=True)
    render.add_argument("--previous-commit")
    render.add_argument("--output", required=True, type=Path)

    current = commands.add_parser("verify-current-release")
    current.add_argument("--release-json", required=True, type=Path)
    current.add_argument("--plan", required=True, type=Path)
    current.add_argument("--repository", required=True, type=Path)
    current.add_argument("--public-commit", required=True)
    current.add_argument("--previous-commit")
    current.add_argument("--asset-directory", required=True, type=Path)

    predecessor = commands.add_parser("verify-predecessor-release")
    predecessor.add_argument("--release-json", required=True, type=Path)
    predecessor.add_argument("--sequence", required=True, type=int)
    predecessor.add_argument("--public-commit", required=True)
    predecessor.add_argument("--asset-directory", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify-policy":
            result = verify_policy(
                load_json(args.repository_json, "repository API response"),
                load_json(args.ruleset_json, "ruleset API response"),
                load_json(args.effective_rules_json, "effective rules API response"),
                load_json(args.immutable_json, "immutable releases API response"),
                expected_repository=args.expected_repository,
                expected_ruleset_id=args.expected_ruleset_id,
            )
            _write_json(args.output, result)
        elif args.command == "prepare":
            result = prepare_plan(
                args.repository,
                args.docs,
                default_branch=args.default_branch,
                created=args.created == "true",
            )
            _write_json(args.output, result)
        elif args.command == "verify-release-index":
            result = verify_release_index(
                load_json(args.releases_json, "release index"),
                load_json(args.plan, "anchor plan"),
            )
            _write_json(args.output, result)
        elif args.command == "render-body":
            result = anchor_payload(
                load_json(args.plan, "anchor plan"),
                args.public_commit,
                args.previous_commit,
            )
            _write_json(args.output, result)
        elif args.command == "verify-current-release":
            verify_current_release(
                load_json(args.release_json, "current release"),
                load_json(args.plan, "anchor plan"),
                args.repository,
                public_commit=args.public_commit,
                previous_commit=args.previous_commit,
                asset_directory=args.asset_directory,
            )
        elif args.command == "verify-predecessor-release":
            verify_predecessor_release(
                load_json(args.release_json, "predecessor release"),
                sequence=args.sequence,
                public_commit=args.public_commit,
                asset_directory=args.asset_directory,
            )
        else:  # pragma: no cover - argparse makes this unreachable.
            raise AnchorError("unknown command")
    except AnchorError as exc:
        print(f"Public anchor refused: {exc}")
        return 1
    print(f"Public anchor {args.command} succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
