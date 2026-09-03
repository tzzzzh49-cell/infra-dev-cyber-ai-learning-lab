import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "learning_publish.py"
WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github/workflows/publish-learning.yml"
)
SPEC = importlib.util.spec_from_file_location("learning_publish", SCRIPT_PATH)
assert SPEC is not None
learning_publish = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = learning_publish
SPEC.loader.exec_module(learning_publish)


SECTIONS = (
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


def _fixture_guide() -> bytes:
    lines = ["# Guide fixture"]
    for number in range(1, 371):
        lines.extend(
            (
                f"### JOUR {number:03d} — Fixture day {number:03d}",
                f"#### Fixture objective {number:03d}",
                "",
            )
        )
    lines.extend(
        (
            "## Appendice A — Consolidations",
            "| Journée | Type | Travail | Validation |",
            "|---:|---|---|---|",
        )
    )
    for number in range(371, 391):
        lines.append(
            f"| {number} | Consolidation | Atelier {number} | Validation {number} |"
        )
    return ("\n".join(lines) + "\n").encode()


def _fixture_reference(day_id: str) -> str:
    number = int(day_id.removeprefix("J"))
    if number <= 370:
        return f"JOUR {number:03d} — Fixture day {number:03d}"
    return f"Appendice A, journée {number}"


FIXTURE_GUIDE = _fixture_guide()
FIXTURE_GUIDE_SHA256 = hashlib.sha256(FIXTURE_GUIDE).hexdigest()


def _git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _initialise_repository(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root / ".git").exists():
        return
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=master", str(root)],
        check=True,
    )
    _git(root, "config", "user.name", "Publisher tests")
    _git(root, "config", "user.email", "publisher-tests@example.invalid")


def _commit_all(root, message):
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "--allow-empty", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _learner_markdown(
    *,
    day_id="J001",
    summary_fr="J’ai reproduit le contrôle et je peux expliquer son résultat.",
    error="Significative: non",
):
    content = {
        "Ma prévision": "Le contrôle devrait réussir.",
        "Mes observations": "Le comportement correspond à ma prévision.",
        "Mon explication": "Le contrôle compare l’état obtenu à l’état attendu.",
        "Test positif": "Réussi.",
        "Refus attendu": "Réussi.",
        "Rollback": "Réussi sur la cible jetable.",
        "Erreur utile": error,
        "Synthèse personnelle sans notes": "Je sais refaire et expliquer le contrôle.",
        "Résumé public FR": summary_fr,
        "Résumé public EN approuvé": (
            "I reproduced the check and can explain its result."
        ),
        "Assertions publiques": (
            "- Le test positif est conforme.\n"
            "- Le refus attendu et le rollback ont été vérifiés."
        ),
        "Statut": "Statut: Validé",
    }
    sections = "\n\n".join(f"## {name}\n\n{content[name]}" for name in SECTIONS)
    return f"# {day_id} — Journée de test\n\n{sections}\n"


def _proof(markdown, review, commits, day_id="J001"):
    sections = learning_publish._parse_sections(markdown)
    phase = learning_publish._phase_for_day(day_id)
    activation = (
        {"kind": "audited-phase", "phase": phase}
        if phase is not None
        else {"kind": "blocked-day", "triggered_by": "J001"}
    )
    references = [_fixture_reference(day_id)]
    if activation["kind"] == "blocked-day":
        references.append(_fixture_reference(activation["triggered_by"]))
    return {
        "schema_version": 1,
        "day_id": day_id,
        "guide": {
            "version": "2.0.0",
            "sha256": FIXTURE_GUIDE_SHA256,
            "refs": references,
        },
        "activation": activation,
        "source_mode": "guide-only",
        "learner_status": "Validé",
        "commits": commits,
        "checks": {
            "positive": "passed",
            "negative": "passed",
            "rollback": "passed",
            "ci": "conforme",
        },
        "review": {
            "status": "ready",
            "criteria": review["criteria"],
            "guide_sha256": review["guide_sha256"],
            "section_digests": review["section_digests"],
        },
        "raw_evidence": {
            "id": f"{day_id.lower()}-{'a' * 32}",
            "sha256": "b" * 64,
        },
        "section_digests": {
            name: hashlib.sha256(sections[name].encode("utf-8")).hexdigest()
            for name in learning_publish.PROOF_SECTION_NAMES
        },
        "conformity": "conforme",
        "timestamps": {"validated_at": "2026-08-20T10:00:00+02:00"},
    }


def _review(markdown):
    sections = learning_publish._parse_sections(markdown)
    return {
        "day_id": "J001",
        "status": "ready",
        "guide_sha256": FIXTURE_GUIDE_SHA256,
        "section_digests": {
            name: hashlib.sha256(sections[name].encode("utf-8")).hexdigest()
            for name in learning_publish.REVIEW_SECTION_NAMES
        },
        "criteria": [
            {"criterion": "explanation", "result": "acquired"},
            {"criterion": "rollback", "result": "acquired"},
        ],
        "private_comment": "This review detail must never be published.",
    }


def _write_inputs(root, *, day_id="J001", summary_fr=None, error=None):
    _initialise_repository(root)
    curriculum = root / "curriculum"
    curriculum.mkdir(parents=True, exist_ok=True)
    (curriculum / "guide.md").write_bytes(FIXTURE_GUIDE)
    audit = curriculum / "audits/phase-00.md"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("# Audit fixture\n", encoding="utf-8")
    (curriculum / "active.json").write_text(
        json.dumps(
            {
                "active_version": "2.0.0",
                "guide_path": "curriculum/guide.md",
                "sha256": FIXTURE_GUIDE_SHA256,
                "audited_phases": [0],
                "versions": {
                    "2.0.0": {
                        "status": "active",
                        "guide_path": "curriculum/guide.md",
                        "sha256": FIXTURE_GUIDE_SHA256,
                        "audited_phases": [0],
                        "audit_reports": {
                            "phase-0": {
                                "path": "curriculum/audits/phase-00.md",
                                "sha256": hashlib.sha256(
                                    b"# Audit fixture\n"
                                ).hexdigest(),
                            }
                        },
                    }
                },
                "audit_reports": {
                    "phase-0": {
                        "path": "curriculum/audits/phase-00.md",
                        "sha256": hashlib.sha256(b"# Audit fixture\n").hexdigest(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    day = root / day_id
    proof_dir = day / ".proof"
    proof_dir.mkdir(parents=True)
    learner = day / "learner.md"
    learner_options = {}
    if summary_fr is not None:
        learner_options["summary_fr"] = summary_fr
    if error is not None:
        learner_options["error"] = error
    learner_options["day_id"] = day_id
    learner_markdown = _learner_markdown(**learner_options)
    learner.write_text(learner_markdown, encoding="utf-8")
    prediction_commit = _commit_all(root, f"{day_id} prediction")
    attempt_commit = _commit_all(root, f"{day_id} attempt")
    review_payload = _review(learner_markdown)
    review_payload["day_id"] = day_id
    proof = proof_dir / "proof.json"
    proof_payload = _proof(
        learner_markdown,
        review_payload,
        [prediction_commit, attempt_commit],
        day_id,
    )
    proof.write_text(
        json.dumps(proof_payload, indent=2),
        encoding="utf-8",
    )
    if learning_publish._phase_for_day(day_id) is None:
        activation_receipt = {
            "schema_version": 1,
            "day_id": day_id,
            "activation": proof_payload["activation"],
        }
        if proof_payload["activation"]["kind"] == "blocked-day":
            trigger = proof_payload["activation"]["triggered_by"]
            activation_receipt["resume_source_branch"] = f"learn/{trigger.lower()}"
        (proof_dir / "activation.json").write_text(
            json.dumps(activation_receipt, indent=2), encoding="utf-8"
        )
    review = proof_dir / "review.json"
    review.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
    (proof_dir / "raw-evidence.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": f"{day_id.lower()}-{'a' * 32}",
                "sha256": "b" * 64,
                "copies": 2,
                "retention": "one-year-after-pathway-completion",
                "verified_at": "2026-08-20T10:00:00+02:00",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _commit_all(root, f"{day_id} final")
    return learner, proof, review


def _publish(inputs, output, *, check=False):
    learner = inputs[0]
    repository = learner.parents[1]
    curriculum = repository / "curriculum/active.json"
    learning_publish.publish(
        *inputs,
        output,
        curriculum_path=curriculum,
        source_revision=_git(repository, "rev-parse", "HEAD"),
        check=check,
    )


def _refresh_proof_section_digests(learner, proof, review=None):
    sections = learning_publish._parse_sections(learner.read_text(encoding="utf-8"))
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["section_digests"] = {
        name: hashlib.sha256(sections[name].encode("utf-8")).hexdigest()
        for name in learning_publish.PROOF_SECTION_NAMES
    }
    if review is not None:
        review_payload = json.loads(review.read_text(encoding="utf-8"))
        review_payload["section_digests"] = {
            name: hashlib.sha256(sections[name].encode("utf-8")).hexdigest()
            for name in learning_publish.REVIEW_SECTION_NAMES
        }
        review.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
        payload["review"]["section_digests"] = review_payload["section_digests"]
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _commit_all(proof.parents[2], "Refresh proof section digests")


def _set_activation(proof, activation):
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["activation"] = activation
    references = [_fixture_reference(payload["day_id"])]
    if activation.get("kind") == "blocked-day":
        references.append(_fixture_reference(activation["triggered_by"]))
    payload["guide"]["refs"] = references
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    activation_receipt = {
        "schema_version": 1,
        "day_id": payload["day_id"],
        "activation": activation,
    }
    if activation.get("kind") == "blocked-day":
        activation_receipt["resume_source_branch"] = (
            f"learn/{activation['triggered_by'].lower()}"
        )
    (proof.parent / "activation.json").write_text(
        json.dumps(activation_receipt, indent=2), encoding="utf-8"
    )
    _commit_all(proof.parents[2], "Update proof activation")


def test_workflow_isolated_wrapper_executes_a_real_publication(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    repository = inputs[0].parents[1]
    trusted = tmp_path / "trusted-publisher"
    trusted.mkdir()
    shutil.copy2(SCRIPT_PATH, trusted / "learning_publish.py")
    shutil.copy2(SCRIPT_PATH.with_name("learn.py"), trusted / "learn.py")
    template = trusted / "public-proof.html"
    shutil.copy2(SCRIPT_PATH.parents[1] / "site/public-proof.html", template)

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"python3 -B -I -c '\n(?P<code>.*?)\n\s*' "
        r'"\$trusted" "\$trusted/learning_publish.py"',
        workflow,
        re.DOTALL,
    )
    assert match is not None
    wrapper = textwrap.dedent(match.group("code"))
    output = tmp_path / "public"
    isolated_home = tmp_path / "isolated-home"
    isolated_home.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-c",
            wrapper,
            str(trusted),
            str(trusted / "learning_publish.py"),
            "--learner",
            str(inputs[0]),
            "--proof",
            str(inputs[1]),
            "--review",
            str(inputs[2]),
            "--curriculum",
            str(repository / "curriculum/active.json"),
            "--template",
            str(template),
            "--source-revision",
            _git(repository, "rev-parse", "HEAD"),
            "--output",
            str(output),
        ],
        cwd=repository,
        env={
            "HOME": str(isolated_home),
            "LANG": "C.UTF-8",
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (output / "index.html").is_file()


def _replace_registered_guide(inputs, guide_bytes):
    learner, proof, review = inputs
    curriculum = learner.parents[1] / "curriculum"
    guide = curriculum / "guide.md"
    guide.write_bytes(guide_bytes)
    digest = hashlib.sha256(guide_bytes).hexdigest()

    manifest_path = curriculum / "active.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = digest
    manifest["versions"]["2.0.0"]["sha256"] = digest
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    proof_payload = json.loads(proof.read_text(encoding="utf-8"))
    proof_payload["guide"]["sha256"] = digest
    proof_payload["review"]["guide_sha256"] = digest
    proof.write_text(json.dumps(proof_payload, indent=2), encoding="utf-8")

    review_payload = json.loads(review.read_text(encoding="utf-8"))
    review_payload["guide_sha256"] = digest
    review.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
    _commit_all(learner.parents[1], "Replace registered guide")


def test_build_emits_only_allowlisted_public_content_and_external_signing_request(
    tmp_path,
):
    inputs = _write_inputs(
        tmp_path / "inputs",
        error=(
            "Significative: oui\n"
            "Erreur: J’ai confondu succès applicatif et disponibilité.\n"
            "Correction: Je vérifie séparément les deux propriétés."
        ),
    )
    output = tmp_path / "public"

    _publish(inputs, output)

    assert {path.name for path in output.iterdir()} == learning_publish.OUTPUT_FILES
    public_proof = json.loads((output / "public-proof.json").read_text())
    assert public_proof["day_id"] == "J001"
    assert public_proof["progress"] == {
        "conforming_days": 1,
        "label": "1/390",
        "meaning": "progression du parcours, pas un score de maîtrise",
        "total_days": 390,
    }
    repository = inputs[0].parents[1]
    assert public_proof["digests"]["source_revision"] == (
        "git:" + _git(repository, "rev-parse", "HEAD")
    )
    assert public_proof["content"]["corrected_lesson"] == {
        "error": "J’ai confondu succès applicatif et disponibilité.",
        "correction": "Je vérifie séparément les deux propriétés.",
    }
    all_output = b"\n".join(path.read_bytes() for path in output.iterdir())
    assert b"Le contr\xc3\xb4le devrait r\xc3\xa9ussir" not in all_output
    assert b"private_comment" not in all_output
    assert b"v2.0.0" not in all_output
    assert f"j001-{'a' * 32}".encode() not in all_output

    request = json.loads((output / "signature-request.json").read_text())
    manifest_bytes = (output / "manifest.json").read_bytes()
    assert request == {
        "kind": "external-detached-signature-request",
        "payload": "manifest.json",
        "payload_sha256": learning_publish.sha256_bytes(manifest_bytes),
        "schema_version": 1,
        "status": "external_signature_expected",
    }
    assert not any(path.suffix == ".sig" for path in output.iterdir())


def test_check_verifies_without_writing(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    output = tmp_path / "public"
    _publish(inputs, output)
    before = {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in output.iterdir()
    }

    _publish(inputs, output, check=True)

    after = {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in output.iterdir()
    }
    assert after == before


def test_ledger_appends_a_hash_chained_entry_without_changing_the_prefix(tmp_path):
    root = tmp_path / "inputs"
    output = tmp_path / "public"
    day_one = _write_inputs(root, day_id="J001")
    day_two = _write_inputs(root, day_id="J002")
    _publish(day_one, output)
    first_ledger = (output / "ledger.jsonl").read_bytes()

    _publish(day_two, output)

    ledger = (output / "ledger.jsonl").read_bytes()
    assert ledger.startswith(first_ledger)
    assert len(ledger.splitlines()) == 2
    entries = [json.loads(line) for line in ledger.splitlines()]
    assert entries[1]["previous_entry_sha256"] == learning_publish.sha256_bytes(
        first_ledger
    )
    assert entries[1]["progress"] == {"conforming_days": 2, "total_days": 390}
    public_proof = json.loads((output / "public-proof.json").read_text())
    assert public_proof["progress"]["label"] == "2/390"


def test_existing_day_is_immutable(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    output = tmp_path / "public"
    _publish(inputs, output)
    original_ledger = (output / "ledger.jsonl").read_bytes()
    learner, proof, review = inputs
    learner.write_text(
        _learner_markdown(
            day_id="J001",
            summary_fr="Un nouveau résumé ne doit pas réécrire la preuve.",
        ),
        encoding="utf-8",
    )
    _refresh_proof_section_digests(learner, proof, review)

    with pytest.raises(learning_publish.PublicationError, match="immutable"):
        _publish((learner, proof, review), output)

    assert (output / "ledger.jsonl").read_bytes() == original_ledger


def test_proof_section_digests_bind_the_published_learner_content(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    learner.write_text(
        _learner_markdown(
            day_id="J001",
            summary_fr="Ce résumé a été modifié après la génération de la preuve.",
        ),
        encoding="utf-8",
    )

    with pytest.raises(learning_publish.PublicationError, match="does not match"):
        _publish((learner, proof, review), tmp_path / "public")


def test_learner_heading_must_match_the_proof_day(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    markdown = learner.read_text(encoding="utf-8").replace("# J001 —", "# J002 —", 1)
    learner.write_text(markdown, encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="heading"):
        _publish((learner, proof, review), tmp_path / "public")


def test_review_is_rejected_after_a_reviewed_section_changes(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    learner.write_text(
        _learner_markdown(
            day_id="J001",
            summary_fr="Ce résumé a changé après la revue professorale.",
        ),
        encoding="utf-8",
    )
    _refresh_proof_section_digests(learner, proof)

    with pytest.raises(learning_publish.PublicationError, match="review is stale"):
        _publish((learner, proof, review), tmp_path / "public")


def test_new_current_phase_does_not_retroactively_audit_an_older_version(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs", day_id="J011")
    curriculum = inputs[0].parents[1] / "curriculum"
    phase_one_audit = b"# Audit phase 1 fixture\n"
    (curriculum / "audits/phase-01.md").write_bytes(phase_one_audit)
    manifest_path = curriculum / "active.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["active_version"] = "3.0.0"
    manifest["audited_phases"] = [0, 1]
    manifest["audit_reports"]["phase-1"] = {
        "path": "curriculum/audits/phase-01.md",
        "sha256": hashlib.sha256(phase_one_audit).hexdigest(),
    }
    manifest["versions"]["2.0.0"]["status"] = "superseded-creditable"
    manifest["versions"]["3.0.0"] = {
        "status": "active",
        "guide_path": "curriculum/guide.md",
        "sha256": FIXTURE_GUIDE_SHA256,
        "audited_phases": [0, 1],
        "audit_reports": manifest["audit_reports"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(
        learning_publish.PublicationError, match="phase 1 was not audited"
    ):
        _publish(inputs, tmp_path / "public")


def test_proof_reference_must_match_the_canonical_registered_guide_day(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["guide"]["refs"] = ["JOUR 001"]
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="canonical"):
        _publish((learner, proof, review), tmp_path / "public")


def test_registered_guide_must_really_contain_the_proof_day(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    guide_without_day = FIXTURE_GUIDE.replace(
        b"### JOUR 001 \xe2\x80\x94 Fixture day 001\n",
        b"### OMITTED 001 \xe2\x80\x94 Fixture day 001\n",
        1,
    )
    _replace_registered_guide(inputs, guide_without_day)

    with pytest.raises(learning_publish.PublicationError, match="does not contain"):
        _publish(inputs, tmp_path / "public")


def test_superseded_creditable_guide_remains_publishable_after_activation_changes(
    tmp_path,
):
    inputs = _write_inputs(tmp_path / "inputs")
    curriculum = inputs[0].parents[1] / "curriculum"
    next_guide = FIXTURE_GUIDE + b"<!-- version 3 -->\n"
    next_digest = hashlib.sha256(next_guide).hexdigest()
    (curriculum / "guide-v3.md").write_bytes(next_guide)
    manifest_path = curriculum / "active.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["active_version"] = "3.0.0"
    manifest["guide_path"] = "curriculum/guide-v3.md"
    manifest["sha256"] = next_digest
    manifest["versions"]["2.0.0"]["status"] = "superseded-creditable"
    manifest["versions"]["3.0.0"] = {
        "status": "active",
        "guide_path": "curriculum/guide-v3.md",
        "sha256": next_digest,
        "audited_phases": [0],
        "audit_reports": manifest["audit_reports"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _commit_all(inputs[0].parents[1], "Activate curriculum 3.0.0")

    _publish(inputs, tmp_path / "public")

    public_proof = json.loads((tmp_path / "public/public-proof.json").read_text())
    assert public_proof["day_id"] == "J001"


def test_historical_source_guide_version_is_not_creditable(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    curriculum = learner.parents[1] / "curriculum/active.json"
    manifest = json.loads(curriculum.read_text(encoding="utf-8"))
    manifest["versions"]["1.0.0"] = {
        "status": "historical-source",
        "guide_path": "curriculum/guide.md",
        "sha256": FIXTURE_GUIDE_SHA256,
    }
    curriculum.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["guide"]["version"] = "1.0.0"
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="historical-source"):
        _publish((learner, proof, review), tmp_path / "public")


def test_unregistered_proof_guide_version_is_rejected(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["guide"]["version"] = "1.9.0"
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="not registered"):
        _publish((learner, proof, review), tmp_path / "public")


@pytest.mark.parametrize(
    "commits",
    [
        ["1" * 40],
        ["1" * 40, "2" * 40, "3" * 40],
    ],
)
def test_proof_requires_exactly_prediction_and_attempt_commits(tmp_path, commits):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["commits"] = commits
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="exactly"):
        _publish((learner, proof, review), tmp_path / "public")


def test_source_revision_must_be_the_real_checked_out_head(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    curriculum = learner.parents[1] / "curriculum/active.json"

    with pytest.raises(learning_publish.PublicationError, match="real Git commit"):
        learning_publish.publish(
            learner,
            proof,
            review,
            tmp_path / "public",
            curriculum_path=curriculum,
            source_revision="f" * 40,
        )

    payload = json.loads(proof.read_text(encoding="utf-8"))
    with pytest.raises(learning_publish.PublicationError, match="checked-out HEAD"):
        learning_publish.publish(
            learner,
            proof,
            review,
            tmp_path / "public",
            curriculum_path=curriculum,
            source_revision=payload["commits"][1],
        )


def test_prediction_and_attempt_must_be_real_ancestral_checkpoints(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    repository = learner.parents[1]
    tree = _git(repository, "write-tree")
    divergent_attempt = _git(repository, "commit-tree", tree, "-m", "Divergent")
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["commits"][1] = divergent_attempt
    proof.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _commit_all(repository, "Record divergent checkpoint")

    with pytest.raises(learning_publish.PublicationError, match="not an ancestor"):
        _publish((learner, proof, review), tmp_path / "public")


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("copies", 1, "copies"),
        ("retention", "forever", "retention"),
        ("verified_at", "2026-08-20T10:00:00", "timezone"),
        ("id", "raw-j001", "bind the day"),
        ("sha256", "c" * 64, "does not match"),
    ],
)
def test_minimal_raw_evidence_receipt_is_strict_and_matches_proof(
    tmp_path, field, value, error
):
    inputs = _write_inputs(tmp_path / "inputs")
    receipt = inputs[1].parent / "raw-evidence.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload[field] = value
    receipt.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match=error):
        _publish(inputs, tmp_path / "public")


def test_minimal_raw_evidence_receipt_must_exist_with_no_extra_fields(tmp_path):
    missing_inputs = _write_inputs(tmp_path / "missing-inputs")
    (missing_inputs[1].parent / "raw-evidence.json").unlink()
    with pytest.raises(learning_publish.PublicationError, match="does not exist"):
        _publish(missing_inputs, tmp_path / "missing-public")

    extra_inputs = _write_inputs(tmp_path / "extra-inputs")
    receipt = extra_inputs[1].parent / "raw-evidence.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["private_path"] = "/forbidden"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(learning_publish.PublicationError, match="strict schema"):
        _publish(extra_inputs, tmp_path / "extra-public")


def test_git_tracked_inputs_must_match_the_source_revision(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    receipt = inputs[1].parent / "raw-evidence.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["verified_at"] = "2026-08-20T11:00:00+02:00"
    receipt.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(
        learning_publish.PublicationError, match="does not match source"
    ):
        _publish(inputs, tmp_path / "public")


def test_training_taint_is_rejected_in_worktree_and_reachable_history(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    repository = inputs[0].parents[1]
    clean_commit = _git(repository, "rev-parse", "HEAD")
    taint = inputs[1].parent / "source-mode.json"
    taint.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "day_id": "J001",
                "source_mode": "training-only",
            }
        ),
        encoding="utf-8",
    )
    _commit_all(repository, "Record training-only source")

    with pytest.raises(learning_publish.PublicationError, match="non-creditable"):
        _publish(inputs, tmp_path / "tainted-public")

    taint.unlink()
    _commit_all(repository, "Delete the visible taint")
    with pytest.raises(learning_publish.PublicationError, match="source ancestry"):
        _publish(inputs, tmp_path / "deleted-taint-public")

    _git(repository, "switch", "-c", "clean-retry", clean_commit)
    _publish(inputs, tmp_path / "clean-public")
    assert (tmp_path / "clean-public/public-proof.json").is_file()

    _git(repository, "merge", "--no-ff", "master", "-m", "Merge tainted attempt")
    with pytest.raises(learning_publish.PublicationError, match="source ancestry"):
        _publish(inputs, tmp_path / "merged-taint-public")


def test_consolidation_requires_and_accepts_a_recorded_activation(tmp_path):
    first = _write_inputs(tmp_path / "inputs", day_id="J001")
    learner, proof, review = _write_inputs(tmp_path / "inputs", day_id="J371")
    output = tmp_path / "public"

    _publish((learner, proof, review), output)
    assert json.loads((output / "public-proof.json").read_text())["day_id"] == "J371"
    _publish(first, output)
    assert [
        json.loads(line)["day_id"]
        for line in (output / "ledger.jsonl").read_text().splitlines()
    ] == ["J371", "J001"]

    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["activation"] = {"kind": "unrecorded"}
    proof.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(learning_publish.PublicationError, match="activation"):
        _publish((learner, proof, review), tmp_path / "other-public")


def test_consolidation_requires_an_exact_versioned_activation_receipt(tmp_path):
    missing = _write_inputs(tmp_path / "missing-inputs", day_id="J371")
    (missing[1].parent / "activation.json").unlink()
    with pytest.raises(learning_publish.PublicationError, match="activation.json"):
        _publish(missing, tmp_path / "missing-public")

    mismatched = _write_inputs(tmp_path / "mismatch-inputs", day_id="J371")
    receipt = mismatched[1].parent / "activation.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["activation"]["triggered_by"] = "J002"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(learning_publish.PublicationError, match="does not match"):
        _publish(mismatched, tmp_path / "mismatch-public")


def test_blocked_consolidation_rejects_an_unaudited_trigger_phase(tmp_path):
    consolidation = _write_inputs(tmp_path / "inputs", day_id="J371")
    _set_activation(consolidation[1], {"kind": "blocked-day", "triggered_by": "J200"})

    with pytest.raises(
        learning_publish.PublicationError, match="trigger phase 7 was not audited"
    ):
        _publish(consolidation, tmp_path / "public")


def test_blocked_consolidation_requires_prior_main_days_and_an_absent_trigger(
    tmp_path,
):
    root = tmp_path / "inputs"
    day_one = _write_inputs(root, day_id="J001")
    day_two = _write_inputs(root, day_id="J002")
    day_three = _write_inputs(root, day_id="J003")
    consolidation = _write_inputs(root, day_id="J371")
    _set_activation(consolidation[1], {"kind": "blocked-day", "triggered_by": "J003"})

    with pytest.raises(learning_publish.PublicationError, match="J001 is missing"):
        _publish(consolidation, tmp_path / "premature-public")

    output = tmp_path / "valid-public"
    _publish(day_one, output)
    _publish(day_two, output)
    _publish(consolidation, output)
    assert json.loads((output / "public-proof.json").read_text())["day_id"] == "J371"

    output_with_trigger = tmp_path / "trigger-public"
    _publish(day_one, output_with_trigger)
    _publish(day_two, output_with_trigger)
    _publish(day_three, output_with_trigger)
    with pytest.raises(
        learning_publish.PublicationError, match="unpublished trigger J003"
    ):
        _publish(consolidation, output_with_trigger)


def test_consolidations_are_published_in_identifier_order(tmp_path):
    root = tmp_path / "inputs"
    day_371 = _write_inputs(root, day_id="J371")
    day_one = _write_inputs(root, day_id="J001")
    day_372 = _write_inputs(root, day_id="J372")
    _set_activation(day_372[1], {"kind": "blocked-day", "triggered_by": "J002"})

    with pytest.raises(learning_publish.PublicationError, match="J371 is missing"):
        _publish(day_372, tmp_path / "out-of-order-public")

    output = tmp_path / "ordered-public"
    _publish(day_371, output)
    _publish(day_one, output)
    _publish(day_372, output)
    assert [
        json.loads(line)["day_id"]
        for line in (output / "ledger.jsonl").read_text().splitlines()
    ] == ["J371", "J001", "J372"]


def test_pathway_completion_consolidation_requires_published_j370(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs", day_id="J371")
    _set_activation(proof, {"kind": "pathway-completion", "triggered_by": "J370"})
    curriculum = learner.parents[1] / "curriculum/active.json"
    prepared = learning_publish.prepare_inputs(
        learner,
        proof,
        review,
        curriculum,
        _git(learner.parents[1], "rev-parse", "HEAD"),
    )

    with pytest.raises(learning_publish.PublicationError, match="published J370"):
        learning_publish._ledger_with_entry(b"", [], prepared)

    j370_entry = {
        "schema_version": 1,
        "sequence": 1,
        "day_id": "J370",
        "proof_sha256": "sha256:" + "a" * 64,
        "previous_entry_sha256": None,
        "progress": {"conforming_days": 1, "total_days": 390},
    }
    ledger = learning_publish.canonical_json_bytes(j370_entry)
    updated, public_proof, appended = learning_publish._ledger_with_entry(
        ledger, [j370_entry], prepared
    )

    assert appended is True
    assert len(updated.splitlines()) == 2
    assert public_proof["day_id"] == "J371"


def test_main_days_cannot_be_published_out_of_order(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs", day_id="J002")

    with pytest.raises(learning_publish.PublicationError, match="J001 is missing"):
        _publish(inputs, tmp_path / "public")


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "La clé est token=super-secret-value.",
        "Jeton fin copié: github_pat_11AA22BB33CC44DD55EE66FF77GG88HH99II.",
        "La preuve se trouve dans /home/alice/private/evidence.txt.",
        "J’ai copié Guide_370_jours_RNCP41996_Secure_AI_Ops_pas_a_pas.md.",
        "```python\nprint('source')\n```",
        "Le changement est dans app/main.py.",
        "stdout: sortie complète de la commande",
        "Contact: private@example.org",
        "Le service privé répond sur 192.168.1.20.",
        "Le service privé répond sur fd12:3456:789a::42.",
        "Le VPS répond sur 8.8.8.8.",
        "Le VPS répond sur 2001:4860:4860::8888.",
        "Le VPS réel porte le nom prod.example.net.",
    ],
)
def test_public_sections_reject_secrets_sources_raw_data_and_private_paths(
    tmp_path, unsafe_text
):
    inputs = _write_inputs(tmp_path / "inputs", summary_fr=unsafe_text)

    with pytest.raises(learning_publish.PublicationError):
        _publish(inputs, tmp_path / "public")

    assert not (tmp_path / "public").exists()


def test_non_significant_error_is_not_published(tmp_path):
    inputs = _write_inputs(
        tmp_path / "inputs",
        error=(
            "Significative: non\n"
            "Erreur: Détail privé sans intérêt public.\n"
            "Correction: Correction locale."
        ),
    )
    output = tmp_path / "public"

    _publish(inputs, output)

    public_proof = json.loads((output / "public-proof.json").read_text())
    assert "corrected_lesson" not in public_proof["content"]
    assert "Détail privé" not in (output / "index.html").read_text()


def test_assertions_can_follow_the_template_one_plain_line_at_a_time(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    learner.write_text(
        learner.read_text().replace(
            "- Le test positif est conforme.\n"
            "- Le refus attendu et le rollback ont été vérifiés.",
            "Le test positif est conforme.\n"
            "Le refus attendu et le rollback ont été vérifiés.",
        ),
        encoding="utf-8",
    )
    _refresh_proof_section_digests(learner, proof, review)

    _publish((learner, proof, review), tmp_path / "public")

    public_proof = json.loads((tmp_path / "public/public-proof.json").read_text())
    assert public_proof["content"]["assertions"] == [
        "Le test positif est conforme.",
        "Le refus attendu et le rollback ont été vérifiés.",
    ]


def test_review_must_be_ready_with_every_criterion_acquired(tmp_path):
    learner, proof, review = _write_inputs(tmp_path / "inputs")
    unsafe_review = json.loads(review.read_text(encoding="utf-8"))
    unsafe_review["criteria"][1]["result"] = "to_redo"
    review.write_text(json.dumps(unsafe_review), encoding="utf-8")

    with pytest.raises(learning_publish.PublicationError, match="to_redo"):
        _publish((learner, proof, review), tmp_path / "public")


def test_existing_output_rejects_unknown_files_and_tampered_ledger(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    output = tmp_path / "public"
    _publish(inputs, output)
    (output / "unexpected.txt").write_text("must not be published")

    with pytest.raises(learning_publish.PublicationError, match="non-allowlisted"):
        _publish(inputs, output, check=True)

    (output / "unexpected.txt").unlink()
    ledger = output / "ledger.jsonl"
    ledger.write_bytes(ledger.read_bytes().replace(b'"sequence":1', b'"sequence":2'))
    with pytest.raises(learning_publish.PublicationError):
        _publish(inputs, output, check=True)


@pytest.mark.parametrize("day_id", ["J000", "J391", "J999"])
def test_existing_ledger_rejects_days_outside_the_pathway(tmp_path, day_id):
    entry = {
        "schema_version": 1,
        "sequence": 1,
        "day_id": day_id,
        "proof_sha256": "sha256:" + "a" * 64,
        "previous_entry_sha256": None,
        "progress": {"conforming_days": 1, "total_days": 390},
    }
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_bytes(learning_publish.canonical_json_bytes(entry))

    with pytest.raises(learning_publish.PublicationError, match="invalid day_id"):
        learning_publish._read_ledger(ledger)


def test_json_artifacts_and_ledger_entries_are_canonical_and_have_sha256_sidecars(
    tmp_path,
):
    inputs = _write_inputs(tmp_path / "inputs")
    output = tmp_path / "public"
    _publish(inputs, output)

    for name in ("public-proof.json", "manifest.json", "signature-request.json"):
        raw = (output / name).read_bytes()
        assert raw == learning_publish.canonical_json_bytes(json.loads(raw))
    ledger_line = (output / "ledger.jsonl").read_bytes()
    assert ledger_line == learning_publish.canonical_json_bytes(json.loads(ledger_line))
    for name in ("public-proof.json", "manifest.json"):
        raw = (output / name).read_bytes()
        expected = f"{hashlib.sha256(raw).hexdigest()}  {name}\n"
        assert (output / f"{name.removesuffix('.json')}.sha256").read_text() == expected


def test_check_fails_without_creating_a_bundle(tmp_path):
    inputs = _write_inputs(tmp_path / "inputs")
    output = tmp_path / "missing-public"

    with pytest.raises(learning_publish.PublicationError, match="does not exist"):
        _publish(inputs, output, check=True)

    assert not output.exists()


def test_publish_workflow_keeps_credentials_ephemeral_and_requires_signed_history():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert workflow.count("persist-credentials: false") == 2
    assert workflow.count("fetch-depth: 0") == 2
    assert "ref: ${{ github.sha }}" in workflow
    assert workflow.count("${{ secrets.PUBLIC_PROOF_TOKEN }}") == 1
    assert "git -C public-proof log --all" in workflow
    assert "manifest.json.sig" in workflow
    assert "ssh-keygen -Y verify" in workflow
    assert "GIT_ASKPASS" in workflow
    assert "git -c credential.helper= push" in workflow
