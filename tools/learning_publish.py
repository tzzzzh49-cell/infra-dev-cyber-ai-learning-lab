#!/usr/bin/env python3
"""Build a minimal publication from one validated learning day.

The module has no network integration.  It accepts the learner-owned Markdown
file, derived proof/review records and a minimal raw-evidence receipt, validates
their Git revision and checkpoint ancestry, then emits an allowlisted static
bundle.  The JSONL ledger is opened in append-only mode; existing entries are
never rewritten by this program.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import html
import ipaddress
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tools.learn import (
        LearningError as GuideLearningError,
    )
    from tools.learn import (
        activated_day_card,
        guide_references,
    )
except ModuleNotFoundError:  # Direct execution adds tools/, not the repository root.
    from learn import (
        LearningError as GuideLearningError,
    )
    from learn import (
        activated_day_card,
        guide_references,
    )

TOTAL_DAYS = 390
MAX_INPUT_BYTES = 1_000_000
MAX_LEDGER_BYTES = 5_000_000
MAX_PUBLIC_SECTION_CHARS = 4_000
MAX_PUBLIC_LINE_CHARS = 500
DEFAULT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "site" / "public-proof.html"
)

LEARNER_SECTIONS = (
    "Ma prévision",
    "Mes observations",
    "Mon explication",
    "Test positif",
    "Refus attendu",
    "Rollback",
    "Erreur utile",
    "Synthèse personnelle sans notes",
    "Résumé public FR",
    "Résumé public EN approuvé",
    "Assertions publiques",
    "Statut",
)
PUBLIC_SECTION_NAMES = (
    "Résumé public FR",
    "Résumé public EN approuvé",
    "Assertions publiques",
)
PROOF_SECTION_NAMES = (
    "Ma prévision",
    "Mes observations",
    "Mon explication",
    "Test positif",
    "Refus attendu",
    "Rollback",
    "Synthèse personnelle sans notes",
    "Résumé public FR",
    "Résumé public EN approuvé",
    "Assertions publiques",
    "Erreur utile",
    "Statut",
)
REVIEW_SECTION_NAMES = tuple(name for name in PROOF_SECTION_NAMES if name != "Statut")
PROOF_FIELDS = {
    "schema_version",
    "day_id",
    "guide",
    "activation",
    "source_mode",
    "learner_status",
    "commits",
    "checks",
    "review",
    "raw_evidence",
    "section_digests",
    "conformity",
    "timestamps",
}
PHASE_BOUNDARIES = (10, 40, 70, 100, 120, 155, 185, 210, 235, 260, 285, 305, 345, 370)
OUTPUT_FILES = {
    "index.html",
    "ledger.jsonl",
    "manifest.json",
    "manifest.sha256",
    "public-proof.json",
    "public-proof.sha256",
    "signature-request.json",
}
MANIFEST_ARTIFACTS = {
    "index.html",
    "ledger.jsonl",
    "public-proof.json",
    "public-proof.sha256",
}
LEDGER_FIELDS = {
    "schema_version",
    "sequence",
    "day_id",
    "proof_sha256",
    "previous_entry_sha256",
    "progress",
}

PASS_STATUSES = {"conforme", "ok", "pass", "passed", "success", "successful"}
NA_STATUSES = {"n/a", "na", "not_applicable", "not-applicable"}
CREDITABLE_VERSION_STATUSES = {"active", "superseded-creditable"}

HEADING_RE = re.compile(r"^##[ \t]+([^\r\n]+?)[ \t]*$", re.MULTILINE)
DAY_ID_RE = re.compile(r"J(\d{3})")
HEX_DIGEST_RE = re.compile(r"(?:sha256:)?([0-9a-fA-F]{64})")
GIT_DIGEST_RE = re.compile(r"(?:git:|sha1:|sha256:)?([0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
OPAQUE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
RAW_EVIDENCE_FIELDS = {
    "schema_version",
    "id",
    "sha256",
    "copies",
    "retention",
    "verified_at",
}

PROHIBITED_PUBLIC_PATTERNS = (
    ("guide source", re.compile(r"Guide_370_jours_RNCP41996[^\s]*", re.I)),
    ("guide path", re.compile(r"(?:/|\\)AegisOps(?:/|\\)", re.I)),
    ("code block", re.compile(r"(?:```|~~~)")),
    ("source diff", re.compile(r"^(?:diff --git|@@\s|\+\+\+\s|---\s)", re.M)),
    ("source code", re.compile(r"^\s*(?:def|class|import|from)\s+[A-Za-z_]", re.M)),
    (
        "private key",
        re.compile(r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE)-----"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "assigned secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|password|passwd|passphrase|secret|token)"
            r"\s*[:=]\s*['\"]?(?!<|\*|x{3,}|redacted|example|placeholder)"
            r"[^\s'\"]{8,}"
        ),
    ),
    ("credential in URL", re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/:]+:[^\s/@]+@")),
    ("URL", re.compile(r"\b(?:https?|file|data)://", re.I)),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    (
        "DNS hostname",
        re.compile(
            r"(?<![A-Za-z0-9_-])"
            r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
            r"[A-Za-z]{2,63}\b"
        ),
    ),
    (
        "private filesystem path",
        re.compile(r"(?<![A-Za-z0-9])/(?:home|root|opt|srv|var|tmp|mnt|media)/[^\s]*"),
    ),
    ("Windows user path", re.compile(r"\b[A-Za-z]:\\Users\\[^\s]+", re.I)),
    (
        "repository path",
        re.compile(
            r"(?<![A-Za-z0-9])(?:\.{0,2}/)?(?:[A-Za-z0-9_.-]+/)+"
            r"[A-Za-z0-9_.-]+\.(?:py|sh|yml|yaml|json|toml|env|md)\b"
        ),
    ),
    (
        "private network address",
        re.compile(
            r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
        ),
    ),
    (
        "private IPv6 address",
        re.compile(
            r"(?<![0-9A-Fa-f:])f[cd][0-9A-Fa-f]{2}"
            r"(?::[0-9A-Fa-f]{0,4}){1,7}(?![0-9A-Fa-f:])",
            re.I,
        ),
    ),
    (
        "raw terminal output",
        re.compile(r"^(?:stdout|stderr|raw output|sortie brute)\s*:", re.I | re.M),
    ),
    ("terminal transcript", re.compile(r"^(?:\$|#|>>>)[ \t]+\S", re.M)),
    ("active HTML", re.compile(r"<\s*(?:script|iframe|object|embed|style)\b", re.I)),
)

IP_ADDRESS_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9])\[?([0-9A-Fa-f:.]+)(?:%[A-Za-z0-9_.-]+)?\]?(?![A-Za-z0-9])"
)


class PublicationError(ValueError):
    """Raised when an input or existing publication is unsafe or inconsistent."""


@dataclass(frozen=True)
class InputDigests:
    learner: str
    proof: str
    review: str


@dataclass(frozen=True)
class PreparedInputs:
    day_id: str
    activation: dict[str, Any]
    summaries: dict[str, str]
    assertions: list[str]
    corrected_lesson: dict[str, str] | None
    source_revision: str
    commits: list[str]
    raw_evidence_sha256: str
    digests: InputDigests


def sha256_bytes(data: bytes) -> str:
    """Return an explicitly labelled SHA-256 digest."""

    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically, with one final newline."""

    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise PublicationError("value cannot be represented as canonical JSON") from exc
    return rendered.encode("utf-8") + b"\n"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise PublicationError(f"non-finite JSON number is forbidden: {value}")


def _read_regular_file(path: Path, label: str, limit: int = MAX_INPUT_BYTES) -> bytes:
    if path.is_symlink():
        raise PublicationError(f"{label} must not be a symbolic link")
    try:
        file_stat = path.stat()
    except FileNotFoundError as exc:
        raise PublicationError(f"{label} does not exist") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise PublicationError(f"{label} must be a regular file")
    if file_stat.st_size > limit:
        raise PublicationError(f"{label} exceeds its size limit")
    return path.read_bytes()


def _decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicationError(f"{label} must be UTF-8") from exc


def _load_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(
            _decode_utf8(data, label),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except PublicationError:
        raise
    except json.JSONDecodeError as exc:
        raise PublicationError(f"{label} is not valid JSON") from exc


def _load_json_file(path: Path, label: str) -> tuple[Any, bytes]:
    raw = _read_regular_file(path, label)
    return _load_json_bytes(raw, label), raw


def _normalise_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise PublicationError(f"{field} must be a SHA-256 string")
    match = HEX_DIGEST_RE.fullmatch(value.strip())
    if match is None:
        raise PublicationError(f"{field} must contain a complete SHA-256 digest")
    return f"sha256:{match.group(1).lower()}"


def _normalise_commit(value: Any) -> str:
    if not isinstance(value, str):
        raise PublicationError("proof.commits entries must be Git digests")
    match = GIT_DIGEST_RE.fullmatch(value.strip())
    if match is None:
        raise PublicationError("proof.commits contains an invalid Git digest")
    return f"git:{match.group(1).lower()}"


def _parse_sections(markdown: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(markdown))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        if name in sections:
            raise PublicationError(f"duplicate learner.md section: {name}")
        sections[name] = markdown[start:end].strip()

    missing = [name for name in LEARNER_SECTIONS if name not in sections]
    if missing:
        raise PublicationError(
            "learner.md is missing required sections: " + ", ".join(missing)
        )
    return sections


def _validate_public_text(value: str, label: str) -> str:
    text = value.strip()
    if not text:
        raise PublicationError(f"{label} must not be empty")
    if len(text) > MAX_PUBLIC_SECTION_CHARS:
        raise PublicationError(f"{label} exceeds the public section size limit")
    if any(len(line) > MAX_PUBLIC_LINE_CHARS for line in text.splitlines()):
        raise PublicationError(f"{label} contains an overlong line")
    if any(ord(character) < 32 and character not in "\n\t\r" for character in text):
        raise PublicationError(f"{label} contains control characters")
    if "\x1b[" in text:
        raise PublicationError(f"{label} contains terminal control sequences")
    for reason, pattern in PROHIBITED_PUBLIC_PATTERNS:
        if pattern.search(text):
            raise PublicationError(f"{label} contains prohibited {reason}")
    for match in IP_ADDRESS_CANDIDATE_RE.finditer(text):
        candidate = match.group(1).rstrip(".")
        if "." not in candidate and ":" not in candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        raise PublicationError(f"{label} contains prohibited IP address")
    return text


def _parse_assertions(value: str) -> list[str]:
    assertions: list[str] = []
    for line in value.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.fullmatch(r"[-*][ \t]+(.+)", stripped)
        assertion = match.group(1) if match is not None else stripped
        if re.match(r"(?:#{1,6}|>|\d+[.)])[ \t]+", assertion):
            raise PublicationError(
                "Assertions publiques must contain one plain assertion per line"
            )
        assertions.append(_validate_public_text(assertion, "a public assertion"))
    if not assertions:
        raise PublicationError("Assertions publiques must contain at least one item")
    if len(assertions) > 20:
        raise PublicationError("Assertions publiques contains too many items")
    if len(set(assertions)) != len(assertions):
        raise PublicationError("Assertions publiques contains a duplicate")
    return assertions


def _parse_corrected_lesson(value: str) -> dict[str, str] | None:
    if not value.strip():
        return None
    significant = re.search(r"(?mi)^Significative\s*:\s*(oui|non)\s*$", value)
    if significant is None or significant.group(1).lower() != "oui":
        return None

    fields: dict[str, str] = {}
    for line in value.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(
            r"\s*(Significative|Erreur|Correction)\s*:\s*(.*?)\s*", line
        )
        if match is None:
            raise PublicationError(
                "a significant Erreur utile must use one-line Erreur and "
                "Correction fields"
            )
        key = match.group(1).lower()
        if key in fields:
            raise PublicationError(f"duplicate Erreur utile field: {match.group(1)}")
        fields[key] = match.group(2)

    if not fields.get("erreur") or not fields.get("correction"):
        raise PublicationError(
            "a significant Erreur utile requires both Erreur and Correction"
        )
    return {
        "error": _validate_public_text(fields["erreur"], "public corrected error"),
        "correction": _validate_public_text(
            fields["correction"], "public corrected lesson"
        ),
    }


def _status_is_pass(value: Any, *, allow_na: bool = False) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    status = value.strip().lower()
    return status in PASS_STATUSES or (allow_na and status in NA_STATUSES)


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise PublicationError(f"{field} must be an ISO-8601 string")
    rendered = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(rendered)
    except ValueError as exc:
        raise PublicationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PublicationError(f"{field} must include a timezone")


def _validate_raw_evidence_receipt(
    proof_path: Path,
    proof: dict[str, Any],
    day_id: str,
) -> tuple[Path, str]:
    receipt_path = proof_path.parent / "raw-evidence.json"
    receipt, _raw = _load_json_file(receipt_path, "raw-evidence.json")
    if not isinstance(receipt, dict) or set(receipt) != RAW_EVIDENCE_FIELDS:
        raise PublicationError("raw-evidence.json has an invalid strict schema")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise PublicationError("raw-evidence.schema_version must be 1")
    expected_id = re.compile(rf"{re.escape(day_id.lower())}-[0-9a-f]{{32}}")
    if (
        not isinstance(receipt["id"], str)
        or expected_id.fullmatch(receipt["id"]) is None
    ):
        raise PublicationError(
            "raw-evidence.id must bind the day to a 32-hex opaque identifier"
        )
    if (
        not isinstance(receipt["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]) is None
    ):
        raise PublicationError("raw-evidence.sha256 must be 64 lowercase hex digits")
    if type(receipt["copies"]) is not int or receipt["copies"] != 2:
        raise PublicationError("raw-evidence.copies must be exactly 2")
    if receipt["retention"] != "one-year-after-pathway-completion":
        raise PublicationError("raw-evidence.retention has an invalid policy")
    _validate_timestamp(receipt["verified_at"], "raw-evidence.verified_at")

    projection = {"id": receipt["id"], "sha256": receipt["sha256"]}
    if proof["raw_evidence"] != projection:
        raise PublicationError(
            "proof.raw_evidence does not match the minimal raw-evidence receipt"
        )
    return receipt_path, f"sha256:{receipt['sha256']}"


def _validate_activation_receipt(
    proof_path: Path, proof: dict[str, Any], day_id: str
) -> Path | None:
    path = proof_path.parent / "activation.json"
    if _phase_for_day(day_id) is not None:
        if path.exists() or path.is_symlink():
            raise PublicationError(
                "main-day proof must not contain a consolidation activation receipt"
            )
        return None
    receipt, _raw = _load_json_file(path, "activation.json")
    if not isinstance(receipt, dict):
        raise PublicationError("activation.json must contain one object")
    base_fields = {"schema_version", "day_id", "activation"}
    activation = proof["activation"]
    expected_fields = set(base_fields)
    if activation.get("kind") == "blocked-day":
        expected_fields.add("resume_source_branch")
    if set(receipt) != expected_fields:
        raise PublicationError("activation.json has an invalid strict schema")
    if (
        receipt["schema_version"] != 1
        or receipt["day_id"] != day_id
        or receipt["activation"] != activation
    ):
        raise PublicationError("activation.json does not match proof activation")
    if activation.get("kind") == "blocked-day":
        trigger = str(activation["triggered_by"])
        source = receipt["resume_source_branch"]
        if (
            not isinstance(source, str)
            or re.fullmatch(
                rf"learn/{trigger.lower()}(?:-(?:retry|resume)-\d+)?", source
            )
            is None
        ):
            raise PublicationError(
                "activation.json has an invalid blocked-day source branch"
            )
    return path


def _run_git(
    repository: Path, arguments: list[str]
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublicationError("Git validation could not be executed") from exc


def _resolve_git_commit(repository: Path, revision: str, label: str) -> str:
    result = _run_git(repository, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    resolved = result.stdout.strip().lower()
    if (
        result.returncode != 0
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", resolved) is None
    ):
        raise PublicationError(f"{label} is not a real Git commit")
    return resolved


def _validate_git_history(
    paths: tuple[Path, ...],
    source_revision: str,
    commits: list[str],
    *,
    forbidden_history_paths: tuple[Path, ...] = (),
) -> None:
    repository_result = _run_git(paths[0].parent, ["rev-parse", "--show-toplevel"])
    if repository_result.returncode != 0 or not repository_result.stdout.strip():
        raise PublicationError("publication inputs must belong to a Git repository")
    repository = Path(repository_result.stdout.strip()).resolve()

    relative_paths: list[str] = []
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_relative_to(repository):
            raise PublicationError(
                "all publication inputs must use the same Git repository"
            )
        relative_paths.append(resolved.relative_to(repository).as_posix())

    source_raw = source_revision.removeprefix("git:")
    source_commit = _resolve_git_commit(repository, source_raw, "source revision")
    head_commit = _resolve_git_commit(repository, "HEAD", "checked-out HEAD")
    if source_commit != head_commit:
        raise PublicationError("source revision does not match the checked-out HEAD")

    for forbidden in forbidden_history_paths:
        resolved = forbidden.resolve()
        if not resolved.is_relative_to(repository):
            raise PublicationError("training receipt escapes the Git repository")
        if forbidden.exists() or forbidden.is_symlink():
            raise PublicationError(
                "training-only source-mode receipt makes this proof non-creditable"
            )
        relative = resolved.relative_to(repository).as_posix()
        history = _run_git(
            repository,
            [
                "log",
                "--full-history",
                "--format=%H",
                source_commit,
                "--",
                relative,
            ],
        )
        if history.returncode != 0:
            raise PublicationError("training receipt history could not be verified")
        if history.stdout.strip():
            raise PublicationError(
                "training-only source-mode receipt exists in source ancestry"
            )

    checkpoint_commits = [
        _resolve_git_commit(
            repository,
            commit.removeprefix("git:"),
            f"checkpoint {index}",
        )
        for index, commit in enumerate(commits, start=1)
    ]
    ancestry = (
        (checkpoint_commits[0], checkpoint_commits[1], "prediction", "attempt"),
        (checkpoint_commits[1], source_commit, "attempt", "source revision"),
    )
    for ancestor, descendant, ancestor_label, descendant_label in ancestry:
        if ancestor == descendant:
            raise PublicationError(
                f"{ancestor_label} and {descendant_label} must be distinct commits"
            )
        result = _run_git(
            repository,
            ["merge-base", "--is-ancestor", ancestor, descendant],
        )
        if result.returncode == 1:
            raise PublicationError(
                f"{ancestor_label} checkpoint is not an ancestor of {descendant_label}"
            )
        if result.returncode != 0:
            raise PublicationError("Git checkpoint ancestry could not be verified")

    for relative_path in relative_paths:
        tracked = _run_git(
            repository,
            ["ls-files", "--error-unmatch", "--", relative_path],
        )
        if tracked.returncode != 0:
            raise PublicationError(
                f"publication input is not tracked by Git: {relative_path}"
            )
        unchanged = _run_git(
            repository,
            ["diff", "--quiet", source_commit, "--", relative_path],
        )
        if unchanged.returncode == 1:
            raise PublicationError(
                f"publication input does not match source revision: {relative_path}"
            )
        if unchanged.returncode != 0:
            raise PublicationError("Git input integrity could not be verified")


def _phase_for_day(day_id: str) -> int | None:
    number = int(day_id.removeprefix("J"))
    for phase, boundary in enumerate(PHASE_BOUNDARIES):
        if number <= boundary:
            return phase
    return None


def _validate_activation(
    activation: Any,
    day_id: str,
    version_audited: list[int],
) -> None:
    if not isinstance(activation, dict):
        raise PublicationError("proof.activation must be an object")
    phase = _phase_for_day(day_id)
    if phase is not None:
        if activation != {"kind": "audited-phase", "phase": phase}:
            raise PublicationError("proof activation does not match its main phase")
        if phase not in version_audited:
            raise PublicationError(
                f"phase {phase} was not audited for this guide version"
            )
        return
    kind = activation.get("kind")
    trigger = activation.get("triggered_by")
    if set(activation) != {"kind", "triggered_by"}:
        raise PublicationError("consolidation activation has an invalid schema")
    if kind == "blocked-day":
        match = DAY_ID_RE.fullmatch(str(trigger))
        if match is None or not 1 <= int(match.group(1)) <= TOTAL_DAYS - 20:
            raise PublicationError("consolidation trigger is invalid")
        trigger_phase = _phase_for_day(str(trigger))
        if trigger_phase not in version_audited:
            raise PublicationError(
                f"consolidation trigger phase {trigger_phase} was not audited "
                "for this guide version"
            )
    elif kind == "pathway-completion":
        if trigger != "J370":
            raise PublicationError("pathway completion must be triggered by J370")
    else:
        raise PublicationError("consolidation has no recorded activation")


def _validate_curriculum(
    curriculum_path: Path, proof: dict[str, Any], day_id: str
) -> None:
    if curriculum_path.name != "active.json":
        raise PublicationError("curriculum manifest must be named active.json")
    manifest, _raw = _load_json_file(curriculum_path, "curriculum active.json")
    if not isinstance(manifest, dict):
        raise PublicationError("curriculum active.json must contain an object")
    required = {
        "active_version",
        "guide_path",
        "sha256",
        "versions",
        "audited_phases",
        "audit_reports",
    }
    if not required <= set(manifest):
        raise PublicationError("curriculum active.json is incomplete")
    proof_guide = proof["guide"]
    versions = manifest["versions"]
    active_record = (
        versions.get(manifest["active_version"]) if isinstance(versions, dict) else None
    )
    if (
        not isinstance(active_record, dict)
        or active_record.get("status") != "active"
        or active_record.get("guide_path") != manifest["guide_path"]
        or active_record.get("sha256") != manifest["sha256"]
        or active_record.get("audited_phases") != manifest["audited_phases"]
        or active_record.get("audit_reports") != manifest["audit_reports"]
    ):
        raise PublicationError("active curriculum pointer is inconsistent")
    version = proof_guide["version"]
    version_record = versions.get(version) if isinstance(versions, dict) else None
    if not isinstance(version_record, dict) or not {
        "status",
        "guide_path",
        "sha256",
    } <= set(version_record):
        raise PublicationError(f"proof guide version {version!r} is not registered")
    version_status = version_record["status"]
    if version_status == "historical-source":
        raise PublicationError("historical-source guide versions are not creditable")
    if version_status not in CREDITABLE_VERSION_STATUSES:
        raise PublicationError(
            f"proof guide version {version!r} has a non-creditable status"
        )
    if not {"audited_phases", "audit_reports"} <= set(version_record):
        raise PublicationError(
            "creditable guide versions must declare their own audit boundary"
        )

    version_audited = version_record["audited_phases"]
    if (
        not isinstance(version_audited, list)
        or not version_audited
        or any(type(value) is not int for value in version_audited)
        or len(version_audited) != len(set(version_audited))
        or any(not 0 <= value < len(PHASE_BOUNDARIES) for value in version_audited)
    ):
        raise PublicationError(
            "registered guide audited_phases must be unique valid phase integers"
        )
    version_reports = version_record["audit_reports"]
    expected_report_keys = {f"phase-{phase}" for phase in version_audited}
    if not isinstance(version_reports, dict) or set(version_reports) != (
        expected_report_keys
    ):
        raise PublicationError(
            "registered guide audit_reports must exactly cover its audited phases"
        )
    _validate_activation(proof.get("activation"), day_id, version_audited)

    repository_root = curriculum_path.resolve().parent.parent
    guide_path = (repository_root / str(version_record["guide_path"])).resolve()
    if not guide_path.is_relative_to(repository_root):
        raise PublicationError("registered guide escapes the repository")
    guide_bytes = _read_regular_file(guide_path, "registered guide", 20_000_000)
    guide_digest = sha256_bytes(guide_bytes)
    declared_digest = _normalise_sha256(
        version_record["sha256"], "curriculum version sha256"
    )
    if guide_digest != declared_digest:
        raise PublicationError("registered guide digest does not match its manifest")
    if (
        _normalise_sha256(proof_guide["sha256"], "proof.guide.sha256")
        != declared_digest
    ):
        raise PublicationError("proof guide does not match its registered version")
    try:
        activation = proof.get("activation")
        canonical_card = activated_day_card(
            guide_path,
            day_id,
            activation if isinstance(activation, dict) else None,
        )
        canonical_references = guide_references(canonical_card)
    except (GuideLearningError, OSError, UnicodeError, ValueError) as exc:
        raise PublicationError(
            f"registered guide does not contain a canonical entry for {day_id}"
        ) from exc
    if proof_guide["refs"] != canonical_references:
        raise PublicationError(
            "proof.guide.refs does not match the canonical registered-guide reference"
        )

    for version_phase in version_audited:
        report_key = f"phase-{version_phase}"
        report = version_reports[report_key]
        if not isinstance(report, dict) or set(report) != {"path", "sha256"}:
            raise PublicationError(
                f"registered guide audit report is invalid for phase {version_phase}"
            )
        report_path = (repository_root / str(report["path"])).resolve()
        if not report_path.is_relative_to(repository_root):
            raise PublicationError(
                "registered guide audit report escapes the repository"
            )
        report_bytes = _read_regular_file(
            report_path, f"registered guide phase {version_phase} audit report"
        )
        if sha256_bytes(report_bytes) != _normalise_sha256(
            report["sha256"],
            f"registered guide phase {version_phase} audit sha256",
        ):
            raise PublicationError(
                "registered guide audit report digest mismatch for "
                f"phase {version_phase}"
            )

    audited = manifest["audited_phases"]
    if not isinstance(audited, list) or any(
        type(value) is not int for value in audited
    ):
        raise PublicationError("curriculum audited_phases must be an integer list")


def _validate_proof(proof: Any, sections: dict[str, str]) -> tuple[str, list[str], str]:
    if not isinstance(proof, dict):
        raise PublicationError("proof.json must contain one JSON object")
    fields = set(proof)
    if fields != PROOF_FIELDS:
        missing = sorted(PROOF_FIELDS - fields)
        extra = sorted(fields - PROOF_FIELDS)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise PublicationError("proof.json schema mismatch: " + "; ".join(details))
    if proof["schema_version"] != 1:
        raise PublicationError("proof.schema_version must be 1")

    day_id = proof["day_id"]
    if not isinstance(day_id, str):
        raise PublicationError("proof.day_id must use the J001 form")
    day_match = DAY_ID_RE.fullmatch(day_id)
    if day_match is None or not 1 <= int(day_match.group(1)) <= TOTAL_DAYS:
        raise PublicationError("proof.day_id must be between J001 and J390")

    guide = proof["guide"]
    if not isinstance(guide, dict) or set(guide) != {"version", "sha256", "refs"}:
        raise PublicationError("proof.guide must contain version, sha256 and refs")
    if not isinstance(guide["version"], str) or not guide["version"].strip():
        raise PublicationError("proof.guide.version must not be empty")
    _normalise_sha256(guide["sha256"], "proof.guide.sha256")
    if (
        not isinstance(guide["refs"], list)
        or not guide["refs"]
        or any(not isinstance(item, str) or not item.strip() for item in guide["refs"])
    ):
        raise PublicationError("proof.guide.refs must be a non-empty string list")

    if proof["source_mode"] != "guide-only":
        raise PublicationError("only source_mode=guide-only is publishable")
    if proof["learner_status"] != "Validé":
        raise PublicationError("proof.learner_status must be Validé")

    commits = proof["commits"]
    if not isinstance(commits, list) or len(commits) != 2:
        raise PublicationError(
            "proof.commits must contain exactly the prediction and attempt checkpoints"
        )
    normalised_commits = [_normalise_commit(item) for item in commits]
    if len(set(normalised_commits)) != len(normalised_commits):
        raise PublicationError("proof.commits contains a duplicate")

    checks = proof["checks"]
    expected_checks = {"positive", "negative", "rollback", "ci"}
    if not isinstance(checks, dict) or set(checks) != expected_checks:
        raise PublicationError(
            "proof.checks must contain positive, negative, rollback and ci"
        )
    if not _status_is_pass(checks["positive"]):
        raise PublicationError("proof.checks.positive is not successful")
    if not _status_is_pass(checks["negative"], allow_na=True):
        raise PublicationError("proof.checks.negative is neither successful nor N/A")
    if not _status_is_pass(checks["rollback"], allow_na=True):
        raise PublicationError("proof.checks.rollback is neither successful nor N/A")
    if not _status_is_pass(checks["ci"]):
        raise PublicationError("proof.checks.ci is not successful")

    embedded_review = proof["review"]
    if not isinstance(embedded_review, dict):
        raise PublicationError("proof.review must be an object")
    if embedded_review.get("status") != "ready":
        raise PublicationError("proof.review is not ready")
    embedded_statuses = _criterion_statuses(embedded_review.get("criteria"))
    if any(status == "to_redo" for status in embedded_statuses):
        raise PublicationError("proof.review still contains a to_redo criterion")

    raw_evidence = proof["raw_evidence"]
    if not isinstance(raw_evidence, dict) or set(raw_evidence) != {"id", "sha256"}:
        raise PublicationError("proof.raw_evidence must contain only id and sha256")
    if (
        not isinstance(raw_evidence["id"], str)
        or OPAQUE_ID_RE.fullmatch(raw_evidence["id"]) is None
    ):
        raise PublicationError("proof.raw_evidence.id must be an opaque identifier")
    raw_digest = _normalise_sha256(raw_evidence["sha256"], "proof.raw_evidence.sha256")

    section_digests = proof["section_digests"]
    expected_sections = set(PROOF_SECTION_NAMES)
    if (
        not isinstance(section_digests, dict)
        or set(section_digests) != expected_sections
    ):
        raise PublicationError(
            "proof.section_digests must contain exactly the cockpit proof sections"
        )
    for section_name in PROOF_SECTION_NAMES:
        recorded = _normalise_sha256(
            section_digests[section_name],
            f"proof.section_digests.{section_name}",
        )
        observed = sha256_bytes(sections[section_name].encode("utf-8"))
        if recorded != observed:
            raise PublicationError(
                f"proof.section_digests does not match learner.md for {section_name}"
            )

    conformity = proof["conformity"]
    if isinstance(conformity, dict):
        conformity = conformity.get("status")
    if not isinstance(conformity, str) or conformity.strip().lower() != "conforme":
        raise PublicationError("only a Conforme proof can be published")

    timestamps = proof["timestamps"]
    if not isinstance(timestamps, dict) or not timestamps:
        raise PublicationError("proof.timestamps must not be empty")
    for key, value in timestamps.items():
        if not isinstance(key, str) or not key:
            raise PublicationError("proof.timestamps contains an invalid key")
        _validate_timestamp(value, f"proof.timestamps.{key}")

    return day_id, normalised_commits, raw_digest


def _criterion_statuses(criteria: Any) -> list[str]:
    statuses: list[str] = []
    if isinstance(criteria, dict):
        values = list(criteria.values())
    elif isinstance(criteria, list):
        values = criteria
    else:
        raise PublicationError("review criteria must be an object or a list")

    for value in values:
        if isinstance(value, str):
            status_value = value
        elif isinstance(value, dict):
            status_value = value.get("status", value.get("result"))
        else:
            status_value = None
        if not isinstance(status_value, str):
            raise PublicationError("each review criterion needs a status")
        status = status_value.strip().lower()
        if status not in {"acquired", "to_redo"}:
            raise PublicationError("criterion status must be acquired or to_redo")
        statuses.append(status)
    if not statuses:
        raise PublicationError("review criteria must not be empty")
    return statuses


def _validate_review_json(
    review: Any,
    day_id: str,
    proof: dict[str, Any],
    sections: dict[str, str],
) -> None:
    if not isinstance(review, dict):
        raise PublicationError("review.json must contain one JSON object")
    status = review.get("status")
    if status is not None and status != "ready":
        raise PublicationError("review is not ready")
    is_ready = review.get("ready") is True or status == "ready"
    if not is_ready:
        raise PublicationError("review is not ready")
    if review.get("day_id", day_id) != day_id:
        raise PublicationError("review day_id does not match proof.day_id")
    statuses = _criterion_statuses(review.get("criteria"))
    if any(status == "to_redo" for status in statuses):
        raise PublicationError("review still contains a to_redo criterion")
    if _normalise_sha256(
        review.get("guide_sha256"), "review.guide_sha256"
    ) != _normalise_sha256(proof["guide"]["sha256"], "proof.guide.sha256"):
        raise PublicationError("review guide does not match proof guide")
    digests = review.get("section_digests")
    if not isinstance(digests, dict) or set(digests) != set(REVIEW_SECTION_NAMES):
        raise PublicationError("review.section_digests has an invalid section set")
    for name in REVIEW_SECTION_NAMES:
        if _normalise_sha256(
            digests[name], f"review.section_digests.{name}"
        ) != sha256_bytes(sections[name].encode("utf-8")):
            raise PublicationError(f"review is stale for learner.md section {name}")


def prepare_inputs(
    learner_path: Path,
    proof_path: Path,
    review_path: Path,
    curriculum_path: Path,
    source_revision: str,
) -> PreparedInputs:
    if learner_path.name != "learner.md":
        raise PublicationError("the learner input must be named learner.md")
    if proof_path.name != "proof.json":
        raise PublicationError("the proof input must be named proof.json")
    if review_path.name != "review.json":
        raise PublicationError("the review input must be review.json")

    learner_bytes = _read_regular_file(learner_path, "learner.md")
    learner_text = _decode_utf8(learner_bytes, "learner.md")
    sections = _parse_sections(learner_text)
    status = sections["Statut"].strip()
    if re.fullmatch(r"(?:Statut\s*:\s*)?Validé", status, re.I) is None:
        raise PublicationError("learner.md Statut must be Validé")

    summaries = {
        "fr": _validate_public_text(sections["Résumé public FR"], "Résumé public FR"),
        "en": _validate_public_text(
            sections["Résumé public EN approuvé"],
            "Résumé public EN approuvé",
        ),
    }
    assertions = _parse_assertions(sections["Assertions publiques"])
    corrected_lesson = _parse_corrected_lesson(sections["Erreur utile"])

    proof, _proof_raw = _load_json_file(proof_path, "proof.json")
    day_id, commits, raw_evidence_sha256 = _validate_proof(proof, sections)
    heading = re.search(r"(?m)^#[ \t]+(J\d{3})\b", learner_text)
    if heading is None or heading.group(1) != day_id:
        raise PublicationError("learner.md heading does not match proof.day_id")
    receipt_path, receipt_digest = _validate_raw_evidence_receipt(
        proof_path, proof, day_id
    )
    if raw_evidence_sha256 != receipt_digest:
        raise PublicationError("raw-evidence receipt digest does not match proof.json")
    _validate_curriculum(curriculum_path, proof, day_id)
    activation_receipt = _validate_activation_receipt(proof_path, proof, day_id)
    proof_canonical = canonical_json_bytes(proof)

    review_raw = _read_regular_file(review_path, review_path.name)
    review = _load_json_bytes(review_raw, "review.json")
    _validate_review_json(review, day_id, proof, sections)
    review_projection = {
        "status": "ready",
        "criteria": review.get("criteria"),
        "guide_sha256": review.get("guide_sha256"),
        "section_digests": review.get("section_digests"),
    }
    if proof["review"] != review_projection:
        raise PublicationError("proof.review does not match review.json")
    review_digest_bytes = canonical_json_bytes(review)
    normalised_source_revision = _normalise_commit(source_revision)
    git_inputs = [
        learner_path,
        proof_path,
        review_path,
        receipt_path,
        curriculum_path,
    ]
    if activation_receipt is not None:
        git_inputs.append(activation_receipt)
    _validate_git_history(
        tuple(git_inputs),
        normalised_source_revision,
        commits,
        forbidden_history_paths=(proof_path.parent / "source-mode.json",),
    )

    return PreparedInputs(
        day_id=day_id,
        activation=proof["activation"],
        summaries=summaries,
        assertions=assertions,
        corrected_lesson=corrected_lesson,
        source_revision=normalised_source_revision,
        commits=commits,
        raw_evidence_sha256=raw_evidence_sha256,
        digests=InputDigests(
            learner=sha256_bytes(learner_bytes),
            proof=sha256_bytes(proof_canonical),
            review=sha256_bytes(review_digest_bytes),
        ),
    )


def _read_ledger(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    if not path.exists():
        return b"", []
    raw = _read_regular_file(path, "ledger.jsonl", MAX_LEDGER_BYTES)
    if not raw:
        return raw, []
    if not raw.endswith(b"\n"):
        raise PublicationError("ledger.jsonl has an incomplete final entry")

    entries: list[dict[str, Any]] = []
    previous_digest: str | None = None
    seen_days: set[str] = set()
    for sequence, line in enumerate(raw.splitlines(keepends=True), start=1):
        entry = _load_json_bytes(line, f"ledger entry {sequence}")
        if not isinstance(entry, dict) or set(entry) != LEDGER_FIELDS:
            raise PublicationError(f"ledger entry {sequence} has an invalid schema")
        if canonical_json_bytes(entry) != line:
            raise PublicationError(f"ledger entry {sequence} is not canonical JSON")
        if entry["schema_version"] != 1 or entry["sequence"] != sequence:
            raise PublicationError(f"ledger entry {sequence} has an invalid sequence")
        if entry["previous_entry_sha256"] != previous_digest:
            raise PublicationError(f"ledger entry {sequence} breaks the hash chain")
        day_match = DAY_ID_RE.fullmatch(str(entry["day_id"]))
        if day_match is None or not 1 <= int(day_match.group(1)) <= TOTAL_DAYS:
            raise PublicationError(f"ledger entry {sequence} has an invalid day_id")
        if entry["day_id"] in seen_days:
            raise PublicationError(f"ledger day {entry['day_id']} is duplicated")
        seen_days.add(entry["day_id"])
        _normalise_sha256(entry["proof_sha256"], "ledger proof_sha256")
        expected_progress = {
            "conforming_days": sequence,
            "total_days": TOTAL_DAYS,
        }
        if entry["progress"] != expected_progress:
            raise PublicationError(f"ledger entry {sequence} has invalid progress")
        previous_digest = sha256_bytes(line)
        entries.append(entry)
    return raw, entries


def _text_as_html(value: str) -> str:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", value) if item.strip()]
    return "".join(
        f"<p>{html.escape(item).replace(chr(10), '<br>')}</p>" for item in paragraphs
    )


def _render_html(public_proof: dict[str, Any], template_path: Path) -> bytes:
    template_bytes = _read_regular_file(template_path, "public site template", 100_000)
    template = _decode_utf8(template_bytes, "public site template")
    content = public_proof["content"]
    digests = public_proof["digests"]
    assertions = "".join(
        f"<li>{html.escape(assertion)}</li>" for assertion in content["assertions"]
    )
    lesson = content.get("corrected_lesson")
    if lesson is None:
        lesson_html = ""
    else:
        lesson_html = (
            '<section aria-labelledby="lesson-title"><h2 id="lesson-title">'
            "Leçon significative corrigée</h2>"
            f"<p><strong>Erreur&nbsp;:</strong> {html.escape(lesson['error'])}</p>"
            f"<p><strong>Correction&nbsp;:</strong> "
            f"{html.escape(lesson['correction'])}</p></section>"
        )
    digest_items = [
        ("Journal d’apprentissage", digests["learner_sha256"]),
        ("Preuve structurée", digests["proof_sha256"]),
        ("Revue", digests["review_sha256"]),
        ("Preuve brute hors Git", digests["raw_evidence_sha256"]),
        ("Révision source publiée", digests["source_revision"]),
    ]
    digest_items.extend(
        (f"Commit {index}", digest)
        for index, digest in enumerate(digests["commits"], start=1)
    )
    digest_html = "".join(
        f"<dt>{html.escape(label)}</dt><dd><code>{html.escape(digest)}</code></dd>"
        for label, digest in digest_items
    )
    replacements = {
        "{{DAY_ID}}": html.escape(public_proof["day_id"]),
        "{{PROGRESS_LABEL}}": html.escape(public_proof["progress"]["label"]),
        "{{SUMMARY_FR}}": _text_as_html(content["summary_fr"]),
        "{{SUMMARY_EN}}": _text_as_html(content["summary_en_approved"]),
        "{{ASSERTIONS}}": assertions,
        "{{CORRECTED_LESSON}}": lesson_html,
        "{{DIGESTS}}": digest_html,
    }
    rendered = template
    for marker, value in replacements.items():
        if marker not in rendered:
            raise PublicationError(f"public site template marker is invalid: {marker}")
        rendered = rendered.replace(marker, value)
    if re.search(r"\{\{[A-Z0-9_]+}}", rendered):
        raise PublicationError("public site template contains an unknown marker")
    return rendered.encode("utf-8")


def _public_proof(prepared: PreparedInputs, sequence: int) -> dict[str, Any]:
    content: dict[str, Any] = {
        "summary_fr": prepared.summaries["fr"],
        "summary_en_approved": prepared.summaries["en"],
        "assertions": prepared.assertions,
    }
    if prepared.corrected_lesson is not None:
        content["corrected_lesson"] = prepared.corrected_lesson
    return {
        "schema_version": 1,
        "day_id": prepared.day_id,
        "progress": {
            "conforming_days": sequence,
            "total_days": TOTAL_DAYS,
            "label": f"{sequence}/{TOTAL_DAYS}",
            "meaning": "progression du parcours, pas un score de maîtrise",
        },
        "content": content,
        "digests": {
            "learner_sha256": prepared.digests.learner,
            "proof_sha256": prepared.digests.proof,
            "review_sha256": prepared.digests.review,
            "raw_evidence_sha256": prepared.raw_evidence_sha256,
            "source_revision": prepared.source_revision,
            "commits": prepared.commits,
        },
    }


def _ledger_with_entry(
    ledger_raw: bytes,
    entries: list[dict[str, Any]],
    prepared: PreparedInputs,
) -> tuple[bytes, dict[str, Any], bool]:
    published_days = {str(entry["day_id"]) for entry in entries}
    day_number = int(prepared.day_id.removeprefix("J"))
    if day_number <= TOTAL_DAYS - 20:
        missing_previous = next(
            (
                f"J{number:03d}"
                for number in range(1, day_number)
                if f"J{number:03d}" not in published_days
            ),
            None,
        )
        if missing_previous is not None:
            raise PublicationError(
                f"main day publication is out of order; {missing_previous} is missing"
            )
    else:
        missing_consolidation = next(
            (
                f"J{number:03d}"
                for number in range(TOTAL_DAYS - 19, day_number)
                if f"J{number:03d}" not in published_days
            ),
            None,
        )
        if missing_consolidation is not None:
            raise PublicationError(
                "consolidation publication is out of order; "
                f"{missing_consolidation} is missing"
            )
        trigger = str(prepared.activation.get("triggered_by", ""))
        if prepared.activation.get("kind") == "blocked-day":
            trigger_number = int(trigger.removeprefix("J"))
            missing_previous = next(
                (
                    f"J{number:03d}"
                    for number in range(1, trigger_number)
                    if f"J{number:03d}" not in published_days
                ),
                None,
            )
            if missing_previous is not None:
                raise PublicationError(
                    "blocked-day consolidation is premature; "
                    f"{missing_previous} is missing before trigger {trigger}"
                )
            if trigger in published_days:
                raise PublicationError(
                    f"blocked-day consolidation requires unpublished trigger {trigger}"
                )
        elif "J370" not in published_days:
            raise PublicationError(
                "pathway-completion consolidation requires published J370"
            )
    existing = next(
        (entry for entry in entries if entry["day_id"] == prepared.day_id), None
    )
    if existing is not None:
        if existing is not entries[-1]:
            raise PublicationError("only the latest ledger day can be rebuilt")
        sequence = existing["sequence"]
    else:
        sequence = len(entries) + 1

    public_proof = _public_proof(prepared, sequence)
    proof_digest = sha256_bytes(canonical_json_bytes(public_proof))
    if existing is not None:
        if existing["proof_sha256"] != proof_digest:
            raise PublicationError(
                "an existing ledger day is immutable and its proof has changed"
            )
        return ledger_raw, public_proof, False

    previous_digest = (
        sha256_bytes(canonical_json_bytes(entries[-1])) if entries else None
    )
    entry = {
        "schema_version": 1,
        "sequence": sequence,
        "day_id": prepared.day_id,
        "proof_sha256": proof_digest,
        "previous_entry_sha256": previous_digest,
        "progress": {"conforming_days": sequence, "total_days": TOTAL_DAYS},
    }
    return ledger_raw + canonical_json_bytes(entry), public_proof, True


def _sidecar(filename: str, data: bytes) -> bytes:
    digest = hashlib.sha256(data).hexdigest()
    return f"{digest}  {filename}\n".encode()


def _build_expected_files(
    ledger_bytes: bytes, public_proof: dict[str, Any], template_path: Path
) -> dict[str, bytes]:
    proof_bytes = canonical_json_bytes(public_proof)
    files: dict[str, bytes] = {
        "index.html": _render_html(public_proof, template_path),
        "ledger.jsonl": ledger_bytes,
        "public-proof.json": proof_bytes,
        "public-proof.sha256": _sidecar("public-proof.json", proof_bytes),
    }
    ledger_lines = ledger_bytes.splitlines(keepends=True)
    ledger_head = sha256_bytes(ledger_lines[-1]) if ledger_lines else None
    manifest = {
        "schema_version": 1,
        "artifacts": {
            name: {"sha256": sha256_bytes(files[name])}
            for name in sorted(MANIFEST_ARTIFACTS)
        },
        "ledger_head_sha256": ledger_head,
        "signature": {"embedded": False, "mode": "external-detached"},
    }
    manifest_bytes = canonical_json_bytes(manifest)
    files["manifest.json"] = manifest_bytes
    files["manifest.sha256"] = _sidecar("manifest.json", manifest_bytes)
    files["signature-request.json"] = canonical_json_bytes(
        {
            "schema_version": 1,
            "kind": "external-detached-signature-request",
            "payload": "manifest.json",
            "payload_sha256": sha256_bytes(manifest_bytes),
            "status": "external_signature_expected",
        }
    )
    if set(files) != OUTPUT_FILES:
        raise PublicationError("internal output allowlist mismatch")
    return files


def _validate_output_path(
    output: Path, learner: Path, proof: Path, review: Path, template: Path
) -> None:
    if output.is_symlink():
        raise PublicationError("output directory must not be a symbolic link")
    resolved = output.resolve()
    forbidden = {Path("/").resolve(), Path.home().resolve(), Path.cwd().resolve()}
    if resolved in forbidden:
        raise PublicationError("output directory is too broad")
    for source in (learner, proof, review, template):
        source_resolved = source.resolve()
        if source_resolved == resolved or resolved in source_resolved.parents:
            raise PublicationError("output directory must not contain an input file")
    if output.exists() and not output.is_dir():
        raise PublicationError("output path must be a directory")


def _validate_existing_bundle(output: Path) -> tuple[bytes, list[dict[str, Any]]]:
    if not output.exists():
        return b"", []
    paths = list(output.iterdir())
    unexpected = sorted(path.name for path in paths if path.name not in OUTPUT_FILES)
    if unexpected:
        raise PublicationError(
            "output contains non-allowlisted entries: " + ", ".join(unexpected)
        )
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise PublicationError(f"output entry is not a regular file: {path.name}")

    ledger_raw, entries = _read_ledger(output / "ledger.jsonl")
    if not paths:
        return ledger_raw, entries
    if not entries:
        raise PublicationError("a non-empty output must contain a non-empty ledger")
    missing = sorted(OUTPUT_FILES - {path.name for path in paths})
    if missing:
        raise PublicationError(
            "existing output bundle is incomplete: " + ", ".join(missing)
        )

    manifest_raw = _read_regular_file(output / "manifest.json", "manifest.json")
    manifest = _load_json_bytes(manifest_raw, "manifest.json")
    if canonical_json_bytes(manifest) != manifest_raw:
        raise PublicationError("manifest.json is not canonical JSON")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise PublicationError("manifest.json has an invalid schema")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != MANIFEST_ARTIFACTS:
        raise PublicationError("manifest.json has an invalid artifact allowlist")
    for name in MANIFEST_ARTIFACTS:
        artifact_bytes = _read_regular_file(output / name, name, MAX_LEDGER_BYTES)
        if artifacts[name] != {"sha256": sha256_bytes(artifact_bytes)}:
            raise PublicationError(f"manifest digest mismatch for {name}")
    expected_head = sha256_bytes(ledger_raw.splitlines(keepends=True)[-1])
    if manifest.get("ledger_head_sha256") != expected_head:
        raise PublicationError("manifest ledger head does not match ledger.jsonl")
    if manifest.get("signature") != {
        "embedded": False,
        "mode": "external-detached",
    }:
        raise PublicationError("manifest must request an external detached signature")

    proof_raw = _read_regular_file(output / "public-proof.json", "public-proof.json")
    public_proof = _load_json_bytes(proof_raw, "public-proof.json")
    if canonical_json_bytes(public_proof) != proof_raw:
        raise PublicationError("public-proof.json is not canonical JSON")
    if entries[-1]["proof_sha256"] != sha256_bytes(proof_raw):
        raise PublicationError("latest ledger entry does not match public-proof.json")

    if _read_regular_file(
        output / "public-proof.sha256", "public-proof.sha256"
    ) != _sidecar("public-proof.json", proof_raw):
        raise PublicationError("public-proof.sha256 does not match public-proof.json")
    if _read_regular_file(output / "manifest.sha256", "manifest.sha256") != _sidecar(
        "manifest.json", manifest_raw
    ):
        raise PublicationError("manifest.sha256 does not match manifest.json")

    request_raw = _read_regular_file(
        output / "signature-request.json", "signature-request.json"
    )
    request = _load_json_bytes(request_raw, "signature-request.json")
    if canonical_json_bytes(request) != request_raw:
        raise PublicationError("signature-request.json is not canonical JSON")
    expected_request = {
        "schema_version": 1,
        "kind": "external-detached-signature-request",
        "payload": "manifest.json",
        "payload_sha256": sha256_bytes(manifest_raw),
        "status": "external_signature_expected",
    }
    if request != expected_request:
        raise PublicationError("signature request does not match manifest.json")
    return ledger_raw, entries


def _atomic_write(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o644)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _append_ledger(path: Path, previous: bytes, expected: bytes) -> None:
    addition = expected[len(previous) :]
    if not addition:
        return
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "r+b", closefd=True) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.seek(0)
            current = stream.read()
            if current != previous:
                raise PublicationError(
                    "ledger changed concurrently; nothing was appended"
                )
            stream.seek(0, os.SEEK_END)
            stream.write(addition)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # fdopen owns and closes the descriptor after successful construction.
        raise


def publish(
    learner_path: Path,
    proof_path: Path,
    review_path: Path,
    output: Path,
    *,
    curriculum_path: Path,
    source_revision: str,
    template_path: Path | None = None,
    check: bool = False,
) -> None:
    """Build or verify one allowlisted publication bundle."""

    template_path = template_path or DEFAULT_TEMPLATE_PATH
    _validate_output_path(output, learner_path, proof_path, review_path, template_path)
    prepared = prepare_inputs(
        learner_path,
        proof_path,
        review_path,
        curriculum_path,
        source_revision,
    )
    existing_ledger, entries = _validate_existing_bundle(output)
    expected_ledger, public_proof, has_new_entry = _ledger_with_entry(
        existing_ledger, entries, prepared
    )
    expected_files = _build_expected_files(expected_ledger, public_proof, template_path)

    if check:
        if not output.exists():
            raise PublicationError("output bundle does not exist")
        for name, expected in expected_files.items():
            path = output / name
            if (
                not path.exists()
                or _read_regular_file(path, name, MAX_LEDGER_BYTES) != expected
            ):
                raise PublicationError(f"output check failed for {name}")
        return

    output.mkdir(parents=True, exist_ok=True)
    if has_new_entry:
        _append_ledger(output / "ledger.jsonl", existing_ledger, expected_ledger)
    elif not (output / "ledger.jsonl").exists():
        raise PublicationError("internal ledger state is inconsistent")
    for name in sorted(OUTPUT_FILES - {"ledger.jsonl"}):
        _atomic_write(output / name, expected_files[name])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local, allowlisted public proof bundle from a verified Git "
            "revision. This command never uses the network or a publishing service."
        )
    )
    parser.add_argument("--learner", required=True, type=Path)
    parser.add_argument("--proof", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--curriculum", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the exact expected bundle without writing anything",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        publish(
            args.learner,
            args.proof,
            args.review,
            args.output,
            curriculum_path=args.curriculum,
            source_revision=args.source_revision,
            template_path=args.template,
            check=args.check,
        )
    except PublicationError as exc:
        print(f"Publication refused: {exc}")
        return 1
    action = "verified" if args.check else "built locally"
    print(f"Public proof {action}: {args.output}")
    if not args.check:
        print("No signature was generated; use signature-request.json externally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
