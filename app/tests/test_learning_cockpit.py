from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import learn, learning_publish

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _write_raw_receipt(
    root: Path, day_id: str = "J001", digest: str = "a" * 64
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": 1,
        "id": f"{day_id.lower()}-{'1' * 32}",
        "sha256": digest,
        "copies": 2,
        "retention": learn.RAW_EVIDENCE_RETENTION,
        "verified_at": "2026-08-20T10:00:00+02:00",
    }
    learn.atomic_json(learn.raw_evidence_receipt_path(root, day_id), receipt)
    return receipt


def test_historical_guide_is_an_exact_immutable_copy() -> None:
    manifest = json.loads(
        (REPOSITORY_ROOT / "curriculum" / "active.json").read_text(encoding="utf-8")
    )
    source = REPOSITORY_ROOT / manifest["source"]["imported_path"]

    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    assert digest == "f38dbd6b9d97ed6ccab21f15619789559792565bed8b5d733155299b1d36b77d"
    assert manifest["source"]["immutable"] is True


def test_active_guide_integrity_and_phase_zero_activation() -> None:
    manifest, guide = learn.active_manifest(REPOSITORY_ROOT)

    assert manifest["active_version"] == "2.1.0"
    assert manifest["audited_phases"] == [0]
    assert guide.is_file()


def test_parse_day_returns_only_guide_content() -> None:
    _, guide = learn.active_manifest(REPOSITORY_ROOT)

    day = learn.parse_day(guide, "J001")

    assert (
        day.title
        == "Définir le périmètre, les règles de sécurité et le journal de bord"
    )
    assert day.commands == ("git status --short", "uname -a")
    assert day.reference.startswith("JOUR 001")
    assert "Ne modifie aucun service" in day.guardrail


def test_consolidation_card_is_bounded_to_the_guide_contract() -> None:
    _, guide = learn.active_manifest(REPOSITORY_ROOT)

    day = learn.parse_day(guide, "J371")

    assert day.title == "Rejouer la reconstruction d'une VM"
    assert day.commands == ()
    assert "Appendice A" in day.reference
    assert "Écart fermé" in day.details


def test_blocked_consolidation_reuses_only_the_triggered_guide_day() -> None:
    _, guide = learn.active_manifest(REPOSITORY_ROOT)
    source = learn.parse_day(guide, "J001")

    day = learn.activated_day_card(
        guide,
        "J371",
        {"kind": "blocked-day", "triggered_by": "J001"},
    )

    assert day.title.startswith("Consolidation de J001")
    assert day.objective == source.objective
    assert day.guardrail == source.guardrail
    assert day.commands == source.commands
    assert learn.guide_references(day) == [
        "Appendice A, journée 371",
        source.reference,
    ]
    assert "reconstruction d'une VM" not in (day.title + day.details).lower()
    assert "Écart fermé" not in day.details
    assert "reprise planifiée" not in day.details


def test_pathway_consolidation_keeps_its_appendix_topic() -> None:
    _, guide = learn.active_manifest(REPOSITORY_ROOT)

    day = learn.activated_day_card(
        guide,
        "J371",
        {"kind": "pathway-completion", "triggered_by": "J370"},
    )

    assert day.title == "Rejouer la reconstruction d'une VM"
    assert learn.guide_references(day) == ["Appendice A, journée 371"]


def test_every_guide_command_keeps_observations_as_the_active_step() -> None:
    manifest, guide = learn.active_manifest(REPOSITORY_ROOT)
    day = learn.parse_day(guide, "J002")
    markdown = learn.render_template(REPOSITORY_ROOT, manifest, day).replace(
        "_Avant la première action, j'écris ce que je pense observer et pourquoi._",
        "Je prévois quatre lectures système sans mutation.",
    )

    assert len(day.commands) == 4
    for index in range(len(day.commands)):
        assert (
            learn.next_learning_step(markdown, day, {"command_index": index})
            == "Mes observations"
        )

    markdown = markdown.replace(
        "_Je conserve uniquement la sortie utile, le code retour et l'horodatage\n"
        "technique. Ce dépôt est public : je retire secrets, données personnelles,\n"
        "adresses réelles, noms DNS réels et chemins propres à mes machines._",
        "J'ai interprété séparément les quatre résultats et leurs codes retour.",
    )
    assert (
        learn.next_learning_step(markdown, day, {"command_index": len(day.commands)})
        == "Mon explication"
    )


def test_template_starts_incomplete_and_is_owned_by_learner() -> None:
    manifest, guide = learn.active_manifest(REPOSITORY_ROOT)
    day = learn.parse_day(guide, "J001")

    markdown = learn.render_template(REPOSITORY_ROOT, manifest, day)

    assert learn.next_incomplete(markdown) == "Ma prévision"
    assert learn.learner_status(markdown) == "En cours"
    assert "Le cockpit" in markdown
    assert manifest["sha256"] in markdown


@pytest.mark.parametrize(
    ("editor", "expected"),
    [
        ("code", ["code", "--goto", "/tmp/learner.md:12"]),
        ("vim -f", ["vim", "-f", "+12", "/tmp/learner.md"]),
        ("custom --line {line} {file}", ["custom", "--line", "12", "/tmp/learner.md"]),
    ],
)
def test_editor_adapters(editor: str, expected: list[str]) -> None:
    assert learn.editor_arguments(editor, Path("/tmp/learner.md"), 12) == expected


def test_paths_cannot_escape_repository(tmp_path: Path) -> None:
    with pytest.raises(learn.LearningError, match="hors dépôt"):
        learn.ensure_inside(tmp_path, tmp_path / ".." / "escape")


def test_training_only_is_never_conformant(tmp_path: Path) -> None:
    root = _minimal_repository(tmp_path)
    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    day, journal = learn.ensure_day(root, manifest, guide, state)
    text = journal.read_text(encoding="utf-8")
    for title in learn.LEARNER_SECTIONS:
        text = text.replace(
            f"## {title}\n", f"## {title}\n\nRéponse personnelle suffisante.\n", 1
        )
    text = text.replace("Statut: En cours", "Statut: Validé")
    journal.write_text(text, encoding="utf-8")
    state["days"]["J001"]["source_mode"] = "training-only"
    proof_dir = journal.parent / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "ci.json").write_text('{"conclusion":"conforme"}\n', encoding="utf-8")
    (proof_dir / "review.json").write_text(
        '{"status":"ready","criteria":[]}\n', encoding="utf-8"
    )

    proof = learn.update_proof(root, manifest, state, day)

    assert proof["source_mode"] == "training-only"
    assert proof["conformity"] == "non_conforme"


def test_training_taint_and_ignored_artifacts_survive_cache_loss(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\ntraining-cache/\n", encoding="utf-8")

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    baseline = git("rev-parse", "HEAD")
    git("switch", "-c", "learn/j001")
    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    learn.ensure_day(root, manifest, guide, state)
    learn.mark_training_only(root, state, "J001")
    aided = root / "training-cache/aided-output.txt"
    aided.parent.mkdir(parents=True)
    aided.write_text("sortie issue d'une aide extérieure\n", encoding="utf-8")
    learn.state_path(root).unlink()

    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    day_state = rebuilt["days"]["J001"]
    assert day_state["source_mode"] == "training-only"
    assert day_state["ignored_artifact_baseline"] == {}
    assert "training-cache/aided-output.txt" in learn.training_attempt_paths(
        root,
        baseline,
        day_state["ignored_artifact_baseline"],
    )
    git("add", "learning/days/J001")
    git("commit", "-m", "record durable training taint")
    learn.source_mode_receipt_path(root, "J001").unlink()
    git("add", "-u", "learning/days/J001")
    git("commit", "-m", "attempt to hide training taint")

    assert learn.has_reachable_training_taint(root, "J001")


def test_training_attempt_restart_archives_then_creates_a_clean_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(
        ".learning/\ncache/\ntraining-cache/\n", encoding="utf-8"
    )

    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Clean baseline")
    baseline = git("rev-parse", "HEAD").stdout.strip()
    git("switch", "-c", "learn/j001")
    modified_ignored = root / "cache/state.txt"
    modified_ignored.parent.mkdir(parents=True)
    modified_ignored.write_text("baseline locale\n", encoding="utf-8")

    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    day, journal = learn.ensure_day(root, manifest, guide, state)
    state["days"]["J001"]["source_mode"] = "training-only"
    learn.save_state(root, state)
    proof_dir = journal.parent / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "old-review.json").write_text("{}\n", encoding="utf-8")
    marker = root / "training-solution-marker.txt"
    marker.write_text("solution extérieure non créditable\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Training-only solution")
    training_commit = git("rev-parse", "HEAD").stdout.strip()
    aided_deliverable = root / "docs/cadrage/baseline.md"
    aided_deliverable.parent.mkdir(parents=True)
    aided_deliverable.write_text("livrable produit avec aide\n", encoding="utf-8")
    ignored_artifact = root / "training-cache/solution.txt"
    ignored_artifact.parent.mkdir(parents=True)
    ignored_artifact.write_text("artefact ignoré produit avec aide\n", encoding="utf-8")
    modified_ignored.write_text("solution extérieure persistante\n", encoding="utf-8")

    monkeypatch.setattr(learn, "confirm", lambda _message: True)
    archived_sources: list[Path] = []

    def fake_archive(archive_root: Path, day_id: str, sources: list[Path]) -> int:
        archived_sources.extend(sources)
        archived_state = learn.load_state(archive_root)
        archived_state["days"][day_id]["raw_evidence"] = {
            "id": "training-archive",
            "sha256": "a" * 64,
        }
        learn.save_state(archive_root, archived_state)
        return 0

    monkeypatch.setattr(learn, "archive_raw_evidence", fake_archive)

    assert learn.restart_guide_only_attempt(root, state, manifest, guide, day) == 0

    restarted = learn.load_state(root)["days"]["J001"]
    assert restarted["source_mode"] == "guide-only"
    assert restarted["branch"] == "learn/j001-retry-1"
    assert restarted["base_commit"] == baseline
    assert restarted["checkpoint_commits"] == {}
    assert restarted["training_attempts"][0]["archive"] == {
        "id": "training-archive",
        "sha256": "a" * 64,
    }
    assert learn.learner_status(journal.read_text(encoding="utf-8")) == "En cours"
    assert not (proof_dir / "old-review.json").exists()
    history = json.loads(
        (proof_dir / "training-attempts.json").read_text(encoding="utf-8")
    )
    assert history["attempts"][0]["archive"]["id"] == "training-archive"
    assert not marker.exists()
    assert not aided_deliverable.exists()
    assert not ignored_artifact.exists()
    assert not modified_ignored.exists()
    assert aided_deliverable in archived_sources
    assert ignored_artifact in archived_sources
    assert modified_ignored in archived_sources
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", training_commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        != 0
    )


def test_capture_keeps_a_digest_not_the_answer(tmp_path: Path) -> None:
    root = _minimal_repository(tmp_path)
    secret_answer = "observation personnelle à ne pas recopier"

    learn.append_capture(root, "J001", "section", secret_answer)

    capture = (root / "learning/days/J001/.proof/captures.jsonl").read_text(
        encoding="utf-8"
    )
    assert secret_answer not in capture
    assert learn.sha256_text(secret_answer) in capture


def test_proof_projects_only_public_raw_reference_and_binds_reviewed_sections(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    day, journal = learn.ensure_day(root, manifest, guide, state)
    receipt = _write_raw_receipt(root)
    state["days"]["J001"]["raw_evidence"] = receipt

    proof = learn.update_proof(root, manifest, state, day)
    markdown = journal.read_text(encoding="utf-8")

    assert proof["raw_evidence"] == {
        "id": "j001-" + "1" * 32,
        "sha256": "a" * 64,
    }
    assert set(proof["section_digests"]) == set(learn.PROOF_SECTIONS)
    assert proof["section_digests"]["Erreur utile"] == learn.sha256_text(
        learn.section(markdown, "Erreur utile")
    )
    assert proof["section_digests"]["Statut"] == learn.sha256_text(
        learn.section(markdown, "Statut")
    )


def test_cockpit_proof_is_accepted_by_the_publication_boundary(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)

    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Fixture baseline")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    day, journal = learn.ensure_day(root, manifest, guide, state)
    markdown = journal.read_text(encoding="utf-8")
    answers = {
        "Ma prévision": "Je prévois un contrôle réussi et un résultat explicable.",
        "Mes observations": "Le résultat utile correspond exactement à la prévision.",
        "Mon explication": "Le contrôle compare le résultat réel au résultat attendu.",
        "Test positif": "Le cas autorisé réussit avec le résultat attendu.",
        "Refus attendu": "Le cas interdit est refusé sans élargir les droits.",
        "Rollback": "La cible isolée revient à sa baseline vérifiée.",
        "Erreur utile": "Significative: non\n\nErreur:\n\nCorrection:",
        "Synthèse personnelle sans notes": (
            "Je sais refaire le contrôle et expliquer sa limite."
        ),
        "Résumé public FR": "J’ai reproduit et expliqué un contrôle borné.",
        "Résumé public EN approuvé": ("I reproduced and explained a bounded check."),
        "Assertions publiques": "Le test et le retour arrière ont été vérifiés.",
        "Statut": "Statut: Validé",
    }
    for title, answer in answers.items():
        markdown = re.sub(
            rf"(?ms)(^## {re.escape(title)}[ \t]*\n).*?(?=^## |\Z)",
            rf"\g<1>\n{answer}\n\n",
            markdown,
        )
    journal.write_text(markdown, encoding="utf-8")
    git("add", "learning/days/J001/learner.md")
    git("commit", "-m", "J001: prévision")
    prediction = git("rev-parse", "HEAD").stdout.strip()
    proof_dir = journal.parent / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "ci.json").write_text('{"conclusion":"conforme"}\n', encoding="utf-8")
    learn.record_review(root, "J001", "ready", ["objectif démontré"])
    receipt = _write_raw_receipt(root)
    state["days"]["J001"]["raw_evidence"] = receipt
    git("add", "learning/days/J001/.proof")
    git("commit", "-m", "J001: tentative")
    attempt = git("rev-parse", "HEAD").stdout.strip()
    state["days"]["J001"]["commit_checkpoints"] = ["prediction", "attempt"]
    state["days"]["J001"]["checkpoint_commits"] = {
        "prediction": prediction,
        "attempt": attempt,
    }

    proof = learn.update_proof(root, manifest, state, day)
    learn.prepare_final_seal(root, state, day, manifest)
    git("add", "learning/days/J001/.proof")
    git("commit", "-m", "J001: résultat final")
    proof_bytes = (proof_dir / "proof.json").read_bytes()
    assert learn.validate_day(root, "J001") == []
    assert (proof_dir / "proof.json").read_bytes() == proof_bytes
    git("switch", "master")
    git("merge", "--no-ff", "learn/j001", "-m", "Merge J001")
    git("push", "origin", "master")
    learn.state_path(root).unlink()
    rebuilt = learn.load_state(root)
    assert rebuilt["completed_days"] == ["J001"]
    assert rebuilt["active_day"] == "J002"
    next_guide = root / "curriculum/v2.1.0/guide.md"
    next_guide.parent.mkdir(parents=True)
    next_guide.write_text(
        guide.read_text(encoding="utf-8") + "\nClarification de phase suivante.\n",
        encoding="utf-8",
    )
    evolved_manifest = json.loads(
        (root / "curriculum/active.json").read_text(encoding="utf-8")
    )
    evolved_manifest["active_version"] = "2.1.0"
    evolved_manifest["guide_path"] = "curriculum/v2.1.0/guide.md"
    evolved_manifest["sha256"] = learn.sha256_file(next_guide)
    evolved_manifest["versions"]["2.0.0"]["status"] = "superseded-creditable"
    evolved_manifest["versions"]["2.1.0"] = {
        "status": "active",
        "guide_path": "curriculum/v2.1.0/guide.md",
        "sha256": evolved_manifest["sha256"],
        "audited_phases": [0],
        "audit_reports": evolved_manifest["audit_reports"],
    }
    (root / "curriculum/active.json").write_text(
        json.dumps(evolved_manifest), encoding="utf-8"
    )
    git("add", "curriculum")
    git("commit", "-m", "Activate fixture guide 2.1.0")
    pinned_manifest, pinned_guide = learn.curriculum_for_day(
        root, evolved_manifest, next_guide, state, "J001"
    )
    assert pinned_manifest["active_version"] == "2.0.0"
    assert pinned_guide == guide
    assert learn.validate_day(root, "J001") == []
    output = tmp_path / "public"
    learning_publish.publish(
        journal,
        proof_dir / "proof.json",
        proof_dir / "review.json",
        output,
        curriculum_path=root / "curriculum/active.json",
        source_revision=git("rev-parse", "HEAD").stdout.strip(),
    )

    assert proof["conformity"] == "conforme"
    assert (output / "public-proof.json").is_file()


def test_unaudited_phase_cannot_start(tmp_path: Path) -> None:
    root = _minimal_repository(tmp_path)
    manifest, _ = learn.active_manifest(root)
    state = learn.new_state()

    with pytest.raises(learn.LearningError, match="phase 1"):
        learn.assert_day_activation(manifest, state, "J011")


def test_blockage_activates_one_consolidation_and_then_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["days"]["J001"] = {
        "base_commit": "b" * 40,
        "guide_version": "2.0.0",
        "guide_sha256": "1" * 64,
        "branch": "learn/j001",
        "checkpoint_commits": {
            "prediction": "c" * 40,
            "attempt": "d" * 40,
            "final": "e" * 40,
        },
        "raw_evidence": {"id": "blocked", "sha256": "f" * 64},
    }
    monkeypatch.setattr(learn, "current_git_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        learn,
        "_blocked_branch_context",
        lambda *_args: ("learn/j001", "2.0.0", "1" * 64),
    )

    consolidation = learn.schedule_consolidation(root, state, "J001")

    assert consolidation == "J371"
    assert state["active_day"] == "J371"
    assert state["next_day"] == "J001"
    assert state["consolidation_queue"] == ["J371"]
    assert state["days"]["J371"]["branch"] == "learn/j371-blocked-j001"
    assert state["days"]["J371"]["guide_version"] == "2.0.0"
    assert state["days"]["J371"]["guide_sha256"] == "1" * 64

    following = learn.complete_day(root, state, "J371")

    assert following == "J001"
    assert state["active_day"] == "J001"
    assert state["consolidation_queue"] == []
    assert state["days"]["J001"]["resume_from_consolidation"] == "J371"
    assert state["days"]["J001"]["resume_prepared"] is False
    assert state["days"]["J001"]["branch"] == "learn/j001-resume-1"
    assert state["days"]["J001"]["start_commit"] == "a" * 40
    assert state["days"]["J001"]["checkpoint_commits"] == {}
    assert "raw_evidence" not in state["days"]["J001"]
    assert state["days"]["J001"]["blocked_attempts"][0]["branch"] == "learn/j001"


def test_second_consolidation_restores_the_exact_blocked_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["active_day"] = "J372"
    state["suspended_day"] = "J001"
    state["consolidation_queue"] = ["J372"]
    state["days"]["J372"] = {
        "resume_source_branch": "learn/j001-resume-1",
        "guide_version": "2.1.0",
        "guide_sha256": "1" * 64,
    }
    monkeypatch.setattr(learn, "current_git_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        learn,
        "_blocked_branch_context",
        lambda *_args: ("learn/j001-resume-1", "2.1.0", "1" * 64),
    )

    following = learn.complete_day(root, state, "J372")

    assert following == "J001"
    assert state["days"]["J001"]["resume_source_branch"] == ("learn/j001-resume-1")
    assert state["days"]["J001"]["branch"] == "learn/j001-resume-2"


def test_consolidation_activation_recovers_from_its_branch_name(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Clean baseline")
    git("switch", "-c", "learn/j371-blocked-j001")

    assert learn._branch_activation_hint(root) == {
        "kind": "blocked-day",
        "triggered_by": "J001",
    }
    with pytest.raises(learn.LearningError, match="branche source et le guide"):
        learn.load_state(root)


def test_versioned_source_branch_disambiguates_a_second_blockage(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    for branch in ("learn/j001", "learn/j001-resume-1"):
        git("switch", "-c", branch, "master")
        journal = root / "learning/days/J001/learner.md"
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(
            "# J001 — blocage\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
            encoding="utf-8",
        )
        proof = journal.parent / ".proof/proof.json"
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(
            json.dumps(
                {
                    "day_id": "J001",
                    "source_mode": "guide-only",
                    "learner_status": "Bloqué",
                }
            ),
            encoding="utf-8",
        )
        if branch.endswith("resume-1"):
            learn.atomic_json(
                proof.parent / "resume.json",
                {
                    "schema_version": 1,
                    "day_id": "J001",
                    "resume_source_branch": "learn/j001",
                },
            )
        git("add", ".")
        git("commit", "-m", "J001: résultat final")

    assert learn._blocked_source_context(root, "J001") is None
    assert learn._blocked_branch_context(root, "J001", "learn/j001-resume-1") == (
        "learn/j001-resume-1",
        "2.1.0",
        "a" * 64,
    )
    assert learn._pending_branch_context(root, "J001") == (
        "learn/j001-resume-1",
        "2.1.0",
        "a" * 64,
    )
    git("switch", "learn/j001")
    with pytest.raises(learn.LearningError, match="ancienne génération"):
        learn.reconstruct_state(root)
    git("switch", "master")
    stale_state = learn.new_state()
    stale_state["days"]["J001"] = {
        "branch": "learn/j001",
        "guide_version": "2.1.0",
        "guide_sha256": "a" * 64,
    }
    learn.save_state(root, stale_state)
    with pytest.raises(learn.LearningError, match="cache local.*ancienne génération"):
        learn.load_state(root)


def test_blocked_branch_rejects_a_deleted_training_taint_in_ancestry(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    branch = "learn/j001"
    git("switch", "-c", branch)
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J001 — blocage\n\n> Guide actif : 2.1.0 (`"
        + "a" * 64
        + "`)\n\n## Statut\n\nStatut: Bloqué\n",
        encoding="utf-8",
    )
    proof_dir = journal.parent / ".proof"
    learn.atomic_json(
        proof_dir / "proof.json",
        {
            "day_id": "J001",
            "source_mode": "guide-only",
            "learner_status": "Bloqué",
        },
    )
    learn.atomic_json(
        proof_dir / "source-mode.json",
        {
            "schema_version": 1,
            "day_id": "J001",
            "source_mode": "training-only",
        },
    )
    git("add", ".")
    git("commit", "-m", "blocked training attempt")
    (proof_dir / "source-mode.json").unlink()
    git("add", "-u")
    git("commit", "-m", "hide training receipt")

    assert learn.has_reachable_training_taint(root, "J001", branch)
    assert learn._blocked_branch_context(root, "J001", branch) is None


def test_pending_retry_can_authorize_a_baseline_branch_without_a_journal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("branch", "learn/j001")
    git("switch", "-c", "learn/j001-retry-1")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J001 — reprise\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
        encoding="utf-8",
    )
    learn.atomic_json(
        journal.parent / ".proof/training-attempts.json",
        {
            "schema_version": 1,
            "day_id": "J001",
            "attempts": [{"branch": "learn/j001"}],
        },
    )
    git("add", ".")
    git("commit", "-m", "reprise guide-only")

    assert learn._pending_branch_context(root, "J001") == (
        "learn/j001-retry-1",
        "2.1.0",
        "a" * 64,
    )


@pytest.mark.parametrize(
    "transitions",
    [
        {"learn/j001-retry-1": "learn/j001-retry-1"},
        {
            "learn/j001-retry-1": "learn/j001-retry-2",
            "learn/j001-retry-2": "learn/j001-retry-1",
        },
    ],
)
def test_pending_branch_rejects_cyclic_transition_receipts(
    tmp_path: Path, transitions: dict[str, str]
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    for branch, source in transitions.items():
        git("switch", "-c", branch, "master")
        journal = root / "learning/days/J001/learner.md"
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(
            "# J001 — reprise\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
            encoding="utf-8",
        )
        learn.atomic_json(
            journal.parent / ".proof/training-attempts.json",
            {
                "schema_version": 1,
                "day_id": "J001",
                "attempts": [{"branch": source}],
            },
        )
        git("add", ".")
        git("commit", "-m", "reprise guide-only")

    with pytest.raises(learn.LearningError, match="boucle"):
        learn._pending_branch_context(root, "J001")


def test_pending_branch_rejects_conflicting_transition_receipt_types(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("branch", "learn/j001")
    git("switch", "-c", "learn/j001-retry-1")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J001 — reprise\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
        encoding="utf-8",
    )
    proof_dir = journal.parent / ".proof"
    learn.atomic_json(
        proof_dir / "resume.json",
        {
            "schema_version": 1,
            "day_id": "J001",
            "resume_source_branch": "learn/j001",
        },
    )
    learn.atomic_json(
        proof_dir / "training-attempts.json",
        {
            "schema_version": 1,
            "day_id": "J001",
            "attempts": [{"branch": "learn/j001-retry-1"}],
        },
    )
    git("add", ".")
    git("commit", "-m", "conflicting transition receipts")

    with pytest.raises(learn.LearningError, match="plusieurs reçus"):
        learn._pending_branch_context(root, "J001")


def test_pending_branch_accepts_local_ahead_but_rejects_divergent_tips(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    remote = tmp_path / "remote.git"

    def git(*arguments: str, cwd: Path = root) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "--bare", str(remote), cwd=tmp_path)
    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("remote", "add", "origin", str(remote))
    git("push", "origin", "master")
    git("switch", "-c", "learn/j001")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J001 — journal\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
        encoding="utf-8",
    )
    git("add", ".")
    git("commit", "-m", "journal initial")
    git("push", "--set-upstream", "origin", "learn/j001")
    (root / "local-only.txt").write_text("divergence\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "avance locale")

    assert learn._pending_branch_context(root, "J001") == (
        "learn/j001",
        "2.1.0",
        "a" * 64,
    )

    git("switch", "-c", "remote-work", "origin/learn/j001")
    (root / "remote-only.txt").write_text("divergence distante\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "avance distante concurrente")
    git("push", "origin", "HEAD:learn/j001")
    git("switch", "learn/j001")

    with pytest.raises(learn.LearningError, match="diverge"):
        learn._pending_branch_context(root, "J001")


def test_pending_consolidation_retry_follows_its_versioned_predecessor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    original = "learn/j371-blocked-j001"
    retry = original + "-retry-1"
    git("switch", "-c", original)
    journal = root / "learning/days/J371/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J371 — consolidation\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
        encoding="utf-8",
    )
    git("add", ".")
    git("commit", "-m", "consolidation initiale")
    git("switch", "-c", retry)
    learn.atomic_json(
        journal.parent / ".proof/training-attempts.json",
        {
            "schema_version": 1,
            "day_id": "J371",
            "attempts": [{"branch": original}],
        },
    )
    git("add", ".")
    git("commit", "-m", "reprise de consolidation")

    assert learn._pending_branch_context(root, "J371") == (
        retry,
        "2.1.0",
        "a" * 64,
    )


def test_cached_consolidation_rejects_a_stale_source_branch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    branch = "learn/j372-blocked-j001"
    git("switch", "-c", branch)
    journal = root / "learning/days/J372/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# J372 — consolidation\n\n> Guide actif : 2.1.0 (`" + "a" * 64 + "`)\n",
        encoding="utf-8",
    )
    activation = {"kind": "blocked-day", "triggered_by": "J001"}
    learn.atomic_json(
        journal.parent / ".proof/activation.json",
        {
            "schema_version": 1,
            "day_id": "J372",
            "activation": activation,
            "resume_source_branch": "learn/j001-resume-1",
        },
    )
    git("add", ".")
    git("commit", "-m", "versioned consolidation context")

    state = learn.new_state()
    state["active_day"] = "J372"
    state["days"]["J372"] = {
        "branch": branch,
        "guide_version": "2.1.0",
        "guide_sha256": "a" * 64,
        "activation": activation,
        "resume_source_branch": "learn/j001",
    }
    learn.save_state(root, state)

    with pytest.raises(learn.LearningError, match="branche source versionnée"):
        learn.load_state(root)


def test_consolidation_and_resumption_branches_exclude_the_blocked_history(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Clean baseline")
    baseline = git("rev-parse", "HEAD").stdout.strip()
    git("switch", "-c", "learn/j001")
    blocked_marker = root / "blocked-change.txt"
    blocked_marker.write_text("changement non validé\n", encoding="utf-8")
    blocked_journal = root / "learning/days/J001/learner.md"
    blocked_journal.parent.mkdir(parents=True)
    blocked_journal.write_text(
        "# J001 — tentative bloquée\n\n"
        "> Guide actif : 2.0.0 (`" + "1" * 64 + "`)\n\n## Statut\n\nStatut: Bloqué\n",
        encoding="utf-8",
    )
    learn.atomic_json(
        blocked_journal.parent / ".proof/proof.json",
        {
            "day_id": "J001",
            "source_mode": "guide-only",
            "learner_status": "Bloqué",
        },
    )
    git("add", ".")
    git("commit", "-m", "Blocked attempt")
    blocked_commit = git("rev-parse", "HEAD").stdout.strip()
    state = learn.new_state()
    state["days"]["J001"] = {
        "base_commit": baseline,
        "guide_version": "2.0.0",
        "guide_sha256": "1" * 64,
        "branch": "learn/j001",
    }

    consolidation = learn.schedule_consolidation(root, state, "J001")
    start = state["days"][consolidation]["start_commit"]
    learn.switch_day_branch(
        root, state["days"][consolidation]["branch"], start_commit=start
    )

    assert not blocked_marker.exists()
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", blocked_commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        != 0
    )
    correction = root / "consolidation-correction.txt"
    correction.write_text("correction validée\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Consolidation correction")
    correction_commit = git("rev-parse", "HEAD").stdout.strip()

    learn.plan_resumed_attempt(root, state, "J001", "J371")
    resumed = state["days"]["J001"]
    learn.switch_day_branch(
        root, resumed["branch"], start_commit=resumed["start_commit"]
    )

    assert correction.exists()
    assert not blocked_marker.exists()
    assert not blocked_journal.exists()
    assert "Statut: Bloqué" in (
        learn.restored_resumption_journal(root, "J001", resumed) or ""
    )
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", correction_commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def test_consolidation_retry_preserves_activation_after_cache_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    baseline = git("rev-parse", "HEAD")
    git("switch", "-c", "learn/j371-blocked-j001")
    manifest, guide = learn.active_manifest(root)
    activation = {"kind": "blocked-day", "triggered_by": "J001"}
    day = learn.DayCard(
        "J371",
        "Consolidation de test",
        "Reprendre la compétence bloquée.",
        "Rester dans le lab.",
        "Appendice A + JOUR 001",
        (),
        "Écart fermé.",
    )
    journal = root / "learning/days/J371/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(learn.render_template(root, manifest, day), encoding="utf-8")
    state = learn.new_state()
    state["active_day"] = "J371"
    state["consolidation_queue"] = ["J371"]
    state["suspended_day"] = "J001"
    state["days"]["J371"] = {
        "base_commit": baseline,
        "source_mode": "training-only",
        "activation": activation,
        "resume_source_branch": "learn/j001",
        "ignored_artifact_baseline": {},
    }
    learn.save_state(root, state)
    monkeypatch.setattr(learn, "confirm", lambda _message: True)

    def fake_archive(archive_root: Path, day_id: str, _sources: list[Path]) -> int:
        archived_state = learn.load_state(archive_root)
        archived_state["days"][day_id]["raw_evidence"] = {
            "id": "training-archive",
            "sha256": "a" * 64,
        }
        learn.save_state(archive_root, archived_state)
        return 0

    monkeypatch.setattr(learn, "archive_raw_evidence", fake_archive)

    assert learn.restart_guide_only_attempt(root, state, manifest, guide, day) == 0

    restarted = learn.load_state(root)["days"]["J371"]
    assert restarted["branch"] == "learn/j371-blocked-j001-retry-1"
    assert restarted["activation"] == activation
    activation_record = json.loads(
        (journal.parent / ".proof/activation.json").read_text(encoding="utf-8")
    )
    assert activation_record["activation"] == activation
    (root / ".learning/state.json").unlink()

    rebuilt = learn.reconstruct_state(root)

    assert rebuilt["active_day"] == "J371"
    assert rebuilt["suspended_day"] == "J001"
    assert rebuilt["days"]["J371"]["activation"] == activation
    assert rebuilt["days"]["J371"]["branch"] == ("learn/j371-blocked-j001-retry-1")
    assert rebuilt["days"]["J371"]["retry_count"] == 1


def test_end_of_main_path_enqueues_all_remaining_consolidations(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["active_day"] = "J370"

    following = learn.complete_day(root, state, "J370", merged_baseline="a" * 40)

    assert following == "J371"
    assert state["consolidation_queue"][0] == "J371"
    assert state["consolidation_queue"][-1] == "J390"
    assert state["pending_phase_tag"] == "phase-13"
    assert state["pending_phase_commit"] == "a" * 40


def test_phase_tag_instruction_targets_the_merged_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = learn.new_state()
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = "a" * 40
    monkeypatch.setattr(learn, "_remote_phase_tag_identity", lambda *_args: None)

    assert not learn.reconcile_phase_tag(tmp_path, state)

    output = capsys.readouterr().out
    assert "git tag -s -m 'Jalon phase-00' phase-00 " + "a" * 40 in output


def test_phase_tag_requires_a_real_cryptographic_signature(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str, input_text: str | None = None) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            input=input_text,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    commit = git("rev-parse", "HEAD")
    fake_tag = (
        f"object {commit}\n"
        "type commit\n"
        "tag phase-00\n"
        "tagger Fake <fake@example.invalid> 1787252400 +0000\n\n"
        "fake signed tag\n"
        "-----BEGIN PGP SIGNATURE-----\n"
        "fake\n"
        "-----END PGP SIGNATURE-----\n"
    )
    tag_object = git("hash-object", "-t", "tag", "-w", "--stdin", input_text=fake_tag)
    git("update-ref", "refs/tags/phase-00", tag_object)
    state = learn.new_state()
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = commit

    with pytest.raises(learn.LearningError, match="cryptographique"):
        learn.reconcile_phase_tag(root, state)

    assert state["pending_phase_tag"] == "phase-00"
    assert state["pending_phase_commit"] == commit


def test_phase_tag_pending_state_is_recoverable_after_local_cache_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = learn.new_state()
    merged = "a" * 40
    monkeypatch.setattr(
        learn,
        "_merged_baseline_for_day",
        lambda _root, day: merged if day == "J010" else None,
    )
    monkeypatch.setattr(learn, "_phase_tag_is_valid", lambda *_args, **_kwargs: False)

    learn.recover_pending_phase_tag(tmp_path, state, {"J010"})

    assert state["pending_phase_tag"] == "phase-00"
    assert state["pending_phase_commit"] == merged


def test_phase_tag_recovery_reopens_a_deleted_remote_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = learn.new_state()
    merged = "a" * 40
    tag_object = "b" * 40
    monkeypatch.setattr(learn, "_merged_baseline_for_day", lambda *_args: merged)
    monkeypatch.setattr(learn, "_phase_tag_is_valid", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        learn,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], 0, tag_object + "\n", ""
        ),
    )
    monkeypatch.setattr(learn, "_remote_phase_tag_identities", lambda *_args: {})

    learn.recover_pending_phase_tag(tmp_path, state, {"J010"})

    assert state["pending_phase_tag"] == "phase-00"
    assert state["pending_phase_commit"] == merged


def test_phase_tag_recovery_ignores_a_newer_homonymous_unrelated_merge(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    remote = tmp_path / "remote.git"

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("remote", "add", "origin", str(remote))

    git("switch", "-c", "learn/j010")
    journal = root / "learning/days/J010/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text("Statut: Validé\n")
    proof = journal.parent / ".proof/proof.json"
    proof.parent.mkdir()
    proof.write_text(
        json.dumps(
            {
                "day_id": "J010",
                "source_mode": "guide-only",
                "learner_status": "Validé",
                "conformity": "conforme",
            }
        )
        + "\n"
    )
    git("add", ".")
    git("commit", "-m", "J010: résultat final")
    git("switch", "master")
    git("merge", "--no-ff", "learn/j010", "-m", "Merge J010")
    legitimate_merge = git("rev-parse", "HEAD")

    git("switch", "-c", "unrelated")
    (root / "unrelated.txt").write_text("unrelated\n")
    git("add", ".")
    git("commit", "-m", "J010: résultat final")
    git("switch", "master")
    git("merge", "--no-ff", "unrelated", "-m", "Unrelated homonym")
    git("push", "origin", "master")

    assert learn._merged_baseline_for_day(root, "J010") == legitimate_merge


def test_state_reconstruction_advances_from_a_feature_branch_already_merged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    remote = tmp_path / "remote.git"

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / ".gitignore").write_text(".learning/\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("remote", "add", "origin", str(remote))
    git("push", "origin", "master")
    git("switch", "-c", "learn/j001")
    proof_path = root / "learning/days/J001/.proof/proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text(
        json.dumps(
            {
                "day_id": "J001",
                "source_mode": "guide-only",
                "learner_status": "Validé",
                "conformity": "conforme",
                "commits": ["a" * 40, "b" * 40],
                "guide": {"version": "2.0.0", "sha256": "c" * 64},
            }
        )
        + "\n"
    )
    git("add", ".")
    git("commit", "-m", "J001: résultat final")
    git("branch", "-m", "work")
    monkeypatch.setattr(learn, "validate_day", lambda *_args: [])

    unmerged = learn.reconstruct_state(root)

    assert unmerged["completed_days"] == []
    assert unmerged["active_day"] == "J001"
    git("switch", "master")
    git("merge", "--no-ff", "work", "-m", "Merge J001")
    merged = git("rev-parse", "HEAD")
    git("push", "origin", "master")
    git("switch", "work")

    rebuilt = learn.reconstruct_state(root)

    assert rebuilt["completed_days"] == ["J001"]
    assert rebuilt["active_day"] == "J002"
    assert rebuilt["days"]["J002"]["start_commit"] == merged
    assert rebuilt["days"]["J002"]["base_commit"] == merged


def test_state_reconstruction_keeps_the_guide_pin_before_any_proof(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    git("switch", "-c", "learn/j001")
    manifest, guide = learn.active_manifest(root)
    day = learn.parse_day(guide, "J001")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        learn.render_template(root, manifest, day),
        encoding="utf-8",
    )

    rebuilt = learn.reconstruct_state(root)

    assert rebuilt["active_day"] == "J001"
    assert rebuilt["days"]["J001"]["guide_version"] == "2.0.0"
    assert rebuilt["days"]["J001"]["guide_sha256"] == manifest["sha256"]


def test_master_checkout_recovers_the_pin_from_an_unmerged_daily_branch(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "guide 2.0.0")
    git("switch", "-c", "learn/j001")
    old_manifest, old_guide = learn.active_manifest(root)
    state = learn.new_state()
    learn.ensure_day(root, old_manifest, old_guide, state)
    git("add", "learning/days/J001/learner.md")
    git("commit", "-m", "J001: prévision")
    git("switch", "master")
    new_guide = root / "curriculum/v2.1.0/guide.md"
    new_guide.parent.mkdir(parents=True)
    new_guide.write_text(
        old_guide.read_text(encoding="utf-8") + "\nClarification compatible.\n",
        encoding="utf-8",
    )
    manifest_path = root / "curriculum/active.json"
    evolved = json.loads(manifest_path.read_text(encoding="utf-8"))
    evolved["versions"]["2.0.0"]["status"] = "superseded-creditable"
    evolved["active_version"] = "2.1.0"
    evolved["guide_path"] = "curriculum/v2.1.0/guide.md"
    evolved["sha256"] = learn.sha256_file(new_guide)
    evolved["versions"]["2.1.0"] = {
        "status": "active",
        "guide_path": evolved["guide_path"],
        "sha256": evolved["sha256"],
        "audited_phases": [0],
        "audit_reports": evolved["audit_reports"],
    }
    manifest_path.write_text(json.dumps(evolved), encoding="utf-8")
    git("add", "curriculum")
    git("commit", "-m", "guide 2.1.0")
    learn.state_path(root).unlink()

    rebuilt = learn.reconstruct_state(root)

    assert rebuilt["active_day"] == "J001"
    assert rebuilt["days"]["J001"]["branch"] == "learn/j001"
    assert rebuilt["days"]["J001"]["guide_version"] == "2.0.0"
    assert rebuilt["days"]["J001"]["guide_sha256"] == old_manifest["sha256"]


def test_phase_tag_recovery_without_completed_boundary_is_a_noop(
    tmp_path: Path,
) -> None:
    state = learn.new_state()

    learn.recover_pending_phase_tag(tmp_path, state, set())

    assert "pending_phase_tag" not in state
    assert "pending_phase_commit" not in state


def test_phase_tag_validation_requires_target_annotation_and_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "a" * 40
    calls: list[tuple[str, ...]] = []

    def successful_run(
        arguments: list[str], *, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        del cwd
        calls.append(tuple(arguments))
        if arguments[1] == "rev-parse":
            return subprocess.CompletedProcess(arguments, 0, expected + "\n", "")
        if arguments[1] == "cat-file":
            return subprocess.CompletedProcess(arguments, 0, "tag\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(learn, "run", successful_run)
    monkeypatch.setattr(
        learn,
        "_ssh_signing_fingerprint",
        lambda *_args, **_kwargs: "SHA256:personal",
    )

    def verified_run(
        arguments: list[str], *, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        result = successful_run(arguments, cwd=cwd)
        if arguments[1] == "verify-tag":
            return subprocess.CompletedProcess(
                arguments,
                0,
                "",
                (
                    'Good "git" signature for aegis-learning with ED25519 key '
                    "SHA256:personal\n"
                ),
            )
        return result

    monkeypatch.setattr(learn, "run", verified_run)

    assert learn._phase_tag_is_valid(tmp_path, "phase-00", expected)
    assert ("git", "verify-tag", "phase-00") in calls


def test_phase_tag_does_not_confuse_a_principal_with_the_signing_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "a" * 40

    def forged_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments[1] == "cat-file":
            output = "tag\n"
        elif arguments[1] == "verify-tag":
            output = (
                'Good "git" signature for SHA256:personal with ED25519 key '
                "SHA256:other\n"
            )
        else:
            output = expected + "\n"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    monkeypatch.setattr(learn, "run", forged_run)
    monkeypatch.setattr(
        learn,
        "_ssh_signing_fingerprint",
        lambda *_args, **_kwargs: "SHA256:personal",
    )

    assert not learn._phase_tag_is_valid(tmp_path, "phase-00", expected)


def test_historical_phase_tag_survives_a_personal_key_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "a" * 40

    def historical_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if arguments[1] == "cat-file":
            output = "tag\n"
        elif arguments[1] == "verify-tag":
            output = (
                'Good "git" signature for aegis-learning with ED25519 key SHA256:old\n'
            )
        else:
            output = expected + "\n"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    monkeypatch.setattr(learn, "run", historical_run)
    monkeypatch.setattr(
        learn,
        "_ssh_signing_fingerprint",
        lambda *_args, **_kwargs: "SHA256:new",
    )
    monkeypatch.setattr(
        learn,
        "_allowed_signing_fingerprints",
        lambda _root: {"SHA256:old", "SHA256:new"},
    )

    assert learn._phase_tag_is_valid(
        tmp_path,
        "phase-00",
        expected,
        require_current_key=False,
    )
    assert not learn._phase_tag_is_valid(tmp_path, "phase-00", expected)


def test_signed_phase_tag_must_be_pushed_before_pending_is_cleared(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "a" * 40
    state = learn.new_state()
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = expected
    monkeypatch.setattr(
        learn,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, expected + "\n", ""
        ),
    )
    monkeypatch.setattr(learn, "_phase_tag_is_valid", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(learn, "_remote_phase_tag_identity", lambda *_args: None)

    assert not learn.reconcile_phase_tag(tmp_path, state)

    assert state["pending_phase_tag"] == "phase-00"
    assert "git push origin refs/tags/phase-00" in capsys.readouterr().out


def test_remote_phase_tag_must_be_the_same_signed_git_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "a" * 40
    local_tag_object = "b" * 40
    state = learn.new_state()
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = expected

    def tag_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        output = local_tag_object if arguments[-1] == "refs/tags/phase-00" else expected
        return subprocess.CompletedProcess(arguments, 0, output + "\n", "")

    monkeypatch.setattr(learn, "run", tag_run)
    monkeypatch.setattr(learn, "_phase_tag_is_valid", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        learn,
        "_remote_phase_tag_identity",
        lambda *_args: ("c" * 40, expected),
    )

    with pytest.raises(learn.LearningError, match="diffère du tag signé localement"):
        learn.reconcile_phase_tag(tmp_path, state)

    assert state["pending_phase_tag"] == "phase-00"


def test_published_historical_phase_tag_is_accepted_after_key_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "a" * 40
    local_tag_object = "b" * 40
    state = learn.new_state()
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = expected
    current_key_requirements: list[bool] = []

    def tag_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        output = local_tag_object if arguments[-1] == "refs/tags/phase-00" else expected
        return subprocess.CompletedProcess(arguments, 0, output + "\n", "")

    def valid_tag(
        _root: Path,
        _tag: str,
        _expected: str,
        *,
        require_current_key: bool = True,
    ) -> bool:
        current_key_requirements.append(require_current_key)
        return not require_current_key

    monkeypatch.setattr(learn, "run", tag_run)
    monkeypatch.setattr(learn, "_phase_tag_is_valid", valid_tag)
    monkeypatch.setattr(
        learn,
        "_remote_phase_tag_identity",
        lambda *_args: (local_tag_object, expected),
    )
    monkeypatch.setattr(learn, "save_state", lambda *_args: None)

    assert learn.reconcile_phase_tag(tmp_path, state)

    assert current_key_requirements == [True, False]
    assert "pending_phase_tag" not in state
    assert "pending_phase_commit" not in state


def test_published_phase_tag_clears_pending_and_recovers_next_missing_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = "a" * 40
    second = "b" * 40
    state = learn.new_state()
    state["completed_days"] = ["J010", "J040"]
    state["pending_phase_tag"] = "phase-00"
    state["pending_phase_commit"] = first

    def phase_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if any("phase-01" in argument for argument in arguments):
            return subprocess.CompletedProcess(arguments, 128, "", "missing")
        return subprocess.CompletedProcess(arguments, 0, first + "\n", "")

    monkeypatch.setattr(learn, "run", phase_run)
    monkeypatch.setattr(
        learn,
        "_merged_baseline_for_day",
        lambda _root, day: {"J010": first, "J040": second}.get(day),
    )
    monkeypatch.setattr(
        learn,
        "_phase_tag_is_valid",
        lambda _root, tag, _expected, **_kwargs: tag == "phase-00",
    )
    monkeypatch.setattr(
        learn,
        "_remote_phase_tag_identity",
        lambda _root, tag: (first, first) if tag == "phase-00" else None,
    )
    monkeypatch.setattr(
        learn,
        "_remote_phase_tag_identities",
        lambda _root, _tags: {"phase-00": (first, first)},
    )
    monkeypatch.setattr(learn, "save_state", lambda *_args: None)

    assert not learn.reconcile_phase_tag(tmp_path, state)

    assert state["pending_phase_tag"] == "phase-01"
    assert state["pending_phase_commit"] == second


def test_completed_day_pins_the_next_branch_to_the_merged_master(
    tmp_path: Path,
) -> None:
    state = learn.new_state()
    merged = "a" * 40

    following = learn.complete_day(tmp_path, state, "J001", merged_baseline=merged)

    assert following == "J002"
    assert state["days"]["J001"]["baseline_commit"] == merged
    assert state["days"]["J002"]["start_commit"] == merged
    assert state["days"]["J002"]["base_commit"] == merged


def test_phase_tag_keeps_exact_merge_while_next_day_uses_latest_master(
    tmp_path: Path,
) -> None:
    state = learn.new_state()
    merge_commit = "a" * 40
    latest_master = "b" * 40

    following = learn.complete_day(
        tmp_path,
        state,
        "J010",
        merged_baseline=merge_commit,
        next_start_commit=latest_master,
    )

    assert following == "J011"
    assert state["days"]["J010"]["baseline_commit"] == merge_commit
    assert state["pending_phase_commit"] == merge_commit
    assert state["days"]["J011"]["start_commit"] == latest_master
    assert state["days"]["J011"]["base_commit"] == latest_master


def test_only_three_learner_commit_checkpoints_are_exposed() -> None:
    markdown = "## Ma prévision\n\nMa prévision personnelle complète.\n"
    day_state: dict[str, object] = {}

    assert learn.next_commit_checkpoint(markdown, day_state) == "prediction"

    day_state["commit_checkpoints"] = ["prediction"]
    markdown += (
        "\n## Mes observations\n\nMes observations personnelles complètes.\n"
        "\n## Mon explication\n\nMon explication personnelle.\n"
        "\n## Test positif\n\nLe cas positif fonctionne comme prévu.\n"
        "\n## Refus attendu\n\nLe refus arrive au point prévu.\n"
        "\n## Rollback\n\nLe retour à la baseline est vérifié.\n"
        "\n## Synthèse personnelle sans notes\n\nJe sais refaire le contrôle seule.\n"
        "\n## Résumé public FR\n\nLe contrôle borné est reproduit.\n"
        "\n## Résumé public EN approuvé\n\nThe bounded check was reproduced.\n"
        "\n## Assertions publiques\n\nLe résultat attendu est vérifié.\n"
        "\n## Statut\n\nStatut: En cours\n"
    )
    assert learn.next_commit_checkpoint(markdown, day_state) == "attempt"

    day_state["commit_checkpoints"] = ["prediction", "attempt"]
    markdown = markdown.replace("Statut: En cours", "Statut: Validé")
    assert learn.next_commit_checkpoint(markdown, day_state) is None
    assert (
        learn.next_commit_checkpoint(markdown, day_state, allow_validated_final=True)
        == "final"
    )


def test_attempt_checkpoint_waits_for_the_complete_reviewable_journal() -> None:
    markdown = (
        "## Ma prévision\n\nMa prévision personnelle complète.\n"
        "\n## Mon explication\n\nMon explication personnelle.\n"
        "\n## Test positif\n\nLe cas positif fonctionne comme prévu.\n"
        "\n## Refus attendu\n\nLe refus arrive au point prévu.\n"
        "\n## Rollback\n\nLe retour à la baseline est vérifié.\n"
        "\n## Statut\n\nStatut: En cours\n"
    )

    assert (
        learn.next_commit_checkpoint(markdown, {"commit_checkpoints": ["prediction"]})
        is None
    )


def test_blocked_status_reopens_after_consolidation_instead_of_rescheduling() -> None:
    markdown = "\n\n".join(
        f"## {title}\n\nRéponse personnelle complète pour {title}."
        for title in learn.LEARNER_SECTIONS
    )
    markdown += "\n\n## Statut\n\nStatut: Bloqué\n"
    day = learn.DayCard(
        "J001", "Test", "Objectif", "Garde-fou", "JOUR 001", (), "Détails"
    )

    assert learn.next_incomplete(markdown) is None
    assert (
        learn.next_learning_step(
            markdown,
            day,
            {"resume_from_consolidation": "J371", "command_index": 0},
        )
        == "Statut"
    )
    assert (
        learn.next_commit_checkpoint(
            markdown,
            {"resume_from_consolidation": "J371", "commit_checkpoints": []},
            day,
        )
        == "prediction"
    )
    assert (
        learn.next_commit_checkpoint(
            markdown,
            {
                "resume_from_consolidation": "J371",
                "commit_checkpoints": ["prediction"],
            },
            day,
        )
        is None
    )


def test_checkpoint_is_recorded_only_after_its_commit_is_pushed(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Initial fixture")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))

    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    _day, journal = learn.ensure_day(root, manifest, guide, state)
    markdown = journal.read_text(encoding="utf-8").replace(
        "_Avant la première action, j'écris ce que je pense observer et pourquoi._",
        "Je prévois un résultat observable avant toute action.",
    )
    journal.write_text(markdown, encoding="utf-8")
    learn.begin_checkpoint(root, state, "J001", "prediction")

    assert learn.guide_pending_checkpoint(root, state, "J001") is True
    assert "prediction" not in state["days"]["J001"].get("checkpoint_commits", {})
    git(
        "add",
        "--",
        *state["days"]["J001"]["pending_checkpoint"]["paths"],
    )
    assert learn.guide_pending_checkpoint(root, state, "J001") is True
    git("commit", "-m", "J001: prévision")
    assert learn.guide_pending_checkpoint(root, state, "J001") is True
    assert "prediction" not in state["days"]["J001"].get("checkpoint_commits", {})
    git("push", "--set-upstream", "origin", "HEAD")

    assert learn.guide_pending_checkpoint(root, state, "J001") is False
    assert (
        state["days"]["J001"]["checkpoint_commits"]["prediction"]
        == git("rev-parse", "HEAD").stdout.strip()
    )


def test_checkpoint_commit_command_is_limited_to_the_frozen_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Initial fixture")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text("prévision personnelle\n", encoding="utf-8")
    state = learn.new_state()
    state["days"]["J001"] = {"base_commit": learn.current_git_head(root)}
    learn.begin_checkpoint(root, state, "J001", "prediction")
    git("add", "--", *state["days"]["J001"]["pending_checkpoint"]["paths"])
    late = root / "late-staged.txt"
    late.write_text("ne doit pas entrer dans le jalon\n", encoding="utf-8")
    git("add", "late-staged.txt")

    assert learn.guide_pending_checkpoint(root, state, "J001") is True

    output = capsys.readouterr().out
    assert "git commit --only" in output
    assert "learning/days/J001/learner.md" in output
    assert "late-staged.txt" not in output


@pytest.mark.parametrize("checkpoint", ["prediction", "final"])
def test_boundary_checkpoint_rejects_an_intermediate_lab_commit(
    tmp_path: Path, checkpoint: str
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    (root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    authorized_parent = git("rev-parse", "HEAD")
    (root / "lab-before-boundary.txt").write_text(
        "modification prématurée\n", encoding="utf-8"
    )
    git("add", ".")
    git("commit", "-m", "unplanned lab change")
    day_root = root / "learning/days/J001"
    if checkpoint == "prediction":
        anchor = day_root / "learner.md"
        day_state = {"base_commit": authorized_parent}
    else:
        anchor = day_root / ".proof/final-seal.json"
        day_state = {"checkpoint_commits": {"attempt": authorized_parent}}
    anchor.parent.mkdir(parents=True)
    anchor.write_text("preuve de frontière\n", encoding="utf-8")
    state = learn.new_state()
    state["days"]["J001"] = day_state

    with pytest.raises(learn.LearningError, match="aucun commit intermédiaire"):
        learn.begin_checkpoint(root, state, "J001", checkpoint)


def test_final_checkpoint_rejects_a_file_added_after_the_plan_was_frozen(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    seal = root / "learning/days/J001/.proof/final-seal.json"
    seal.parent.mkdir(parents=True)
    solution = root / "solution.txt"
    solution.write_text("version revue\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    seal.write_text('{"sealed": true}\n', encoding="utf-8")
    state = learn.new_state()
    state["days"]["J001"] = {
        "checkpoint_commits": {"attempt": learn.current_git_head(root)}
    }
    learn.begin_checkpoint(root, state, "J001", "final")
    solution.write_text("version modifiée après revue\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "J001: résultat final")

    with pytest.raises(learn.LearningError, match="diffère du plan gelé"):
        learn.guide_pending_checkpoint(root, state, "J001")


def test_all_skipped_ci_checks_remain_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["days"]["J001"] = {"pr_url": "https://example.invalid/pr/1"}

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps(
                [{"name": "optional", "state": "SKIPPED", "bucket": "skipping"}]
            ),
            stderr="",
        )

    monkeypatch.setattr(learn, "run", fake_run)

    assert learn.refresh_ci(root, state, "J001") == "pending"
    assert not (root / "learning/days/J001/.proof/ci.json").exists()


def test_one_trivial_pass_cannot_hide_skipped_required_ci_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["days"]["J001"] = {"pr_url": "https://example.invalid/pr/1"}
    checks = [
        {"name": "trivial", "state": "SUCCESS", "bucket": "pass"},
        *[
            {"name": name, "state": "SKIPPED", "bucket": "skipping"}
            for name in sorted(learn.REQUIRED_CI_CHECK_NAMES)
        ],
    ]
    monkeypatch.setattr(
        learn,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, json.dumps(checks), ""
        ),
    )

    assert learn.refresh_ci(root, state, "J001") == "pending"


def test_every_required_ci_check_must_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    state["days"]["J001"] = {"pr_url": "https://example.invalid/pr/1"}
    checks = [
        {"name": name, "state": "SUCCESS", "bucket": "pass"}
        for name in sorted(learn.REQUIRED_CI_CHECK_NAMES)
    ]
    monkeypatch.setattr(
        learn,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, json.dumps(checks), ""
        ),
    )

    assert learn.refresh_ci(root, state, "J001") == "conforme"


def _pushed_planned_checkpoint_chain(
    tmp_path: Path,
    *,
    through: str = "final",
) -> tuple[
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    learn.DayCard,
    Path,
    dict[str, str],
]:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Initial fixture")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")

    manifest, guide = learn.active_manifest(root)
    state = learn.new_state()
    day, journal = learn.ensure_day(root, manifest, guide, state)
    state["days"]["J001"]["branch"] = "learn/j001"
    commits: dict[str, str] = {}
    additions = {
        "prediction": "prévision personnelle",
        "attempt": "tentative personnelle",
        "final": "résultat final personnel",
    }
    subjects = {
        "prediction": "J001: prévision",
        "attempt": "J001: tentative",
        "final": "J001: résultat final",
    }
    checkpoint_order = ("prediction", "attempt", "final")
    assert through in checkpoint_order
    for checkpoint in checkpoint_order[: checkpoint_order.index(through) + 1]:
        journal.write_text(
            journal.read_text(encoding="utf-8") + f"\n{additions[checkpoint]}\n",
            encoding="utf-8",
        )
        if checkpoint == "final":
            learn.final_seal_path(root, "J001").write_text(
                '{"test": "seal"}\n', encoding="utf-8"
            )
        learn.begin_checkpoint(root, state, "J001", checkpoint)
        pending = state["days"]["J001"]["pending_checkpoint"]
        git("add", "--", *pending["paths"])
        git("commit", "-m", subjects[checkpoint])
        commits[checkpoint] = git("rev-parse", "HEAD")
        if checkpoint == "prediction":
            git("push", "--set-upstream", "origin", "learn/j001")
        else:
            git("push")
        assert learn.guide_pending_checkpoint(root, state, "J001") is False

    return root, manifest, guide, state, day, journal, commits


def test_checkpoint_hydration_recovers_final_and_completed_commands(
    tmp_path: Path,
) -> None:
    root, manifest, guide, _initial, day, _journal, commits = (
        _pushed_planned_checkpoint_chain(tmp_path)
    )
    prediction = commits["prediction"]
    attempt = commits["attempt"]
    final = commits["final"]
    rebuilt = learn.new_state()
    rebuilt["days"]["J001"] = {
        "branch": "learn/j001",
        "checkpoint_commits": {"prediction": prediction, "attempt": attempt},
        "commit_checkpoints": ["prediction", "attempt"],
        "command_index": 0,
    }

    learn.ensure_day(root, manifest, guide, rebuilt)

    recovered = rebuilt["days"]["J001"]
    assert recovered["checkpoint_commits"]["final"] == final
    assert recovered["commit_checkpoints"] == ["prediction", "attempt", "final"]
    assert recovered["command_index"] == len(day.commands)

    learn.atomic_json(
        root / "learning/days/J001/.proof/revisions.json",
        {
            "schema_version": 1,
            "day_id": "J001",
            "revisions": [
                {
                    "reopened_at": learn.now_iso(),
                    "mode": "full-reattempt",
                    "previous_attempt": attempt,
                    "previous_final": final,
                    "head_at_reopen": final,
                }
            ],
        },
    )
    reopened = learn.new_state()
    reopened["days"]["J001"] = {
        "branch": "learn/j001",
        "checkpoint_commits": {"prediction": prediction},
        "commit_checkpoints": ["prediction"],
        "command_index": 0,
    }

    learn.ensure_day(root, manifest, guide, reopened)

    assert reopened["days"]["J001"]["checkpoint_commits"] == {"prediction": prediction}
    assert reopened["days"]["J001"]["commit_checkpoints"] == ["prediction"]


def test_checkpoint_hydration_ignores_a_lateral_prediction_after_final(
    tmp_path: Path,
) -> None:
    root, manifest, guide, _state, _day, journal, commits = (
        _pushed_planned_checkpoint_chain(tmp_path)
    )

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("switch", "master")
    git("switch", "-c", "lateral/j001")
    lateral_state = learn.new_state()
    _lateral_day, lateral_journal = learn.ensure_day(
        root, manifest, guide, lateral_state
    )
    lateral_state["days"]["J001"]["branch"] = "lateral/j001"
    lateral_journal.write_text(
        lateral_journal.read_text(encoding="utf-8")
        + "\nprévision latérale personnelle\n",
        encoding="utf-8",
    )
    learn.begin_checkpoint(root, lateral_state, "J001", "prediction")
    lateral_pending = lateral_state["days"]["J001"]["pending_checkpoint"]
    git("add", "--", *lateral_pending["paths"])
    lateral_commit_environment = dict(os.environ)
    lateral_commit_environment.update(
        {
            "GIT_AUTHOR_DATE": "2035-01-02T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2035-01-02T00:00:00+00:00",
        }
    )
    subprocess.run(
        ["git", "commit", "-m", "J001: prévision"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        env=lateral_commit_environment,
    )
    lateral_prediction = git("rev-parse", "HEAD")
    git("push", "--set-upstream", "origin", "lateral/j001")
    assert learn.guide_pending_checkpoint(root, lateral_state, "J001") is False
    assert (
        learn.checkpoint_plan_for_commit(root, "J001", "prediction", lateral_prediction)
        is not None
    )

    git("switch", "learn/j001")
    main_journal = journal.read_text(encoding="utf-8")
    merge = subprocess.run(
        [
            "git",
            "merge",
            "--no-ff",
            "--no-commit",
            "lateral/j001",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert merge.returncode == 1
    unresolved = set(git("diff", "--name-only", "--diff-filter=U").splitlines())
    journal_relative = str(journal.relative_to(root))
    plan_relative = str(learn.checkpoint_plan_path(root, "J001").relative_to(root))
    assert unresolved == {journal_relative, plan_relative}
    journal.write_text(
        main_journal + "\nRésolution explicite de la fusion latérale.\n",
        encoding="utf-8",
    )
    git("add", "--", journal_relative)
    git("checkout", "--ours", "--", plan_relative)
    git("add", "--", plan_relative)
    git("commit", "-m", "Merge lateral prediction fixture")
    merge_commit = git("rev-parse", "HEAD")
    assert git("rev-parse", f"{merge_commit}^1") == commits["final"]
    assert git("rev-parse", f"{merge_commit}^2") == lateral_prediction
    changed_from_first_parent = git(
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        f"{merge_commit}^1",
        merge_commit,
    ).splitlines()
    assert journal_relative in changed_from_first_parent
    git("push")

    unfiltered_history = git(
        "log",
        "--reverse",
        "--format=%H",
        "HEAD",
        "--",
        journal_relative,
        str(learn.final_seal_path(root, "J001").relative_to(root)),
    ).splitlines()
    assert unfiltered_history.index(lateral_prediction) > unfiltered_history.index(
        commits["final"]
    )

    learn.state_path(root).unlink(missing_ok=True)
    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    checkpoint_commits = rebuilt["days"]["J001"]["checkpoint_commits"]
    assert checkpoint_commits == commits
    assert lateral_prediction not in checkpoint_commits.values()


def test_checkpoint_hydration_rejects_a_forged_monoparent_reseal(
    tmp_path: Path,
) -> None:
    root, manifest, guide, state, _day, _journal, commits = (
        _pushed_planned_checkpoint_chain(tmp_path)
    )

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    rogue_path = root / "rogue-after-final.txt"
    rogue_path.write_text("commit intermédiaire non autorisé\n", encoding="utf-8")
    git("add", rogue_path.name)
    git("commit", "-m", "rogue commit after final")
    rogue = git("rev-parse", "HEAD")
    assert len(git("show", "-s", "--format=%P", rogue).split()) == 1
    git("push")

    revisions_path = root / "learning/days/J001/.proof/revisions.json"
    learn.atomic_json(
        revisions_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "revisions": [
                {
                    "reopened_at": learn.now_iso(),
                    "mode": "reseal-after-base-update",
                    "previous_attempt": commits["attempt"],
                    "previous_final": commits["final"],
                    "head_at_reopen": rogue,
                }
            ],
        },
    )
    seal = learn.final_seal_path(root, "J001")
    seal.write_text('{"test": "forged reseal"}\n', encoding="utf-8")

    with pytest.raises(learn.LearningError, match="aucun commit intermédiaire"):
        learn.begin_checkpoint(root, state, "J001", "final")

    plan_path = learn.checkpoint_plan_path(root, "J001")
    forged_paths = sorted(
        str(path.relative_to(root)) for path in (plan_path, revisions_path, seal)
    )
    learn.atomic_json(
        plan_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "checkpoint": "final",
            "base_head": rogue,
            "paths": forged_paths,
        },
    )
    git("add", "--", *forged_paths)
    git("commit", "-m", "J001: résultat final")
    forged_final = git("rev-parse", "HEAD")
    assert (
        learn.checkpoint_plan_for_commit(root, "J001", "final", forged_final)
        is not None
    )
    git("push")

    learn.state_path(root).unlink(missing_ok=True)
    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    checkpoint_commits = rebuilt["days"]["J001"]["checkpoint_commits"]
    assert checkpoint_commits == commits
    assert forged_final not in checkpoint_commits.values()


def test_reseal_accepts_a_verified_master_merge_as_its_direct_parent(
    tmp_path: Path,
) -> None:
    root, manifest, guide, state, _day, _journal, commits = (
        _pushed_planned_checkpoint_chain(tmp_path)
    )

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    prediction_plan = learn.checkpoint_plan_for_commit(
        root, "J001", "prediction", commits["prediction"]
    )
    assert prediction_plan is not None
    original_base = prediction_plan["base_head"]
    git("switch", "-c", "upstream-update", "master")
    (root / "upstream.txt").write_text("mise à jour master\n", encoding="utf-8")
    git("add", "upstream.txt")
    git("commit", "-m", "upstream update")
    updated_master = git("rev-parse", "HEAD")
    assert updated_master != original_base
    git("push", "origin", "HEAD:master")
    git("switch", "learn/j001")
    git("merge", "--no-ff", "upstream-update", "-m", "Update branch")
    merge_commit = git("rev-parse", "HEAD")
    assert git("rev-parse", f"{merge_commit}^1") == commits["final"]

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0
    learn.final_seal_path(root, "J001").write_text(
        '{"test": "resealed"}\n', encoding="utf-8"
    )

    learn.begin_checkpoint(root, state, "J001", "final")

    pending = state["days"]["J001"]["pending_checkpoint"]
    assert pending["base_head"] == merge_commit
    git("add", "--", *pending["paths"])
    git("commit", "-m", "J001: résultat final")
    resealed_final = git("rev-parse", "HEAD")
    git("push")
    assert learn.guide_pending_checkpoint(root, state, "J001") is False

    learn.state_path(root).unlink(missing_ok=True)
    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    rebuilt_day = rebuilt["days"]["J001"]
    assert rebuilt_day["checkpoint_commits"] == {
        "prediction": commits["prediction"],
        "attempt": commits["attempt"],
        "final": resealed_final,
    }
    assert rebuilt_day["base_commit"] == original_base
    assert rebuilt_day["base_commit"] != updated_master


def test_checkpoint_hydration_replays_two_successive_full_reattempts(
    tmp_path: Path,
) -> None:
    root, manifest, guide, state, _day, journal, initial_commits = (
        _pushed_planned_checkpoint_chain(tmp_path)
    )

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit_checkpoint(checkpoint: str, cycle: int) -> str:
        journal.write_text(
            journal.read_text(encoding="utf-8")
            + f"\n{checkpoint} personnel du cycle {cycle}\n",
            encoding="utf-8",
        )
        if checkpoint == "final":
            learn.final_seal_path(root, "J001").write_text(
                json.dumps({"test": f"seal-{cycle}"}) + "\n",
                encoding="utf-8",
            )
        learn.begin_checkpoint(root, state, "J001", checkpoint)
        pending = state["days"]["J001"]["pending_checkpoint"]
        git("add", "--", *pending["paths"])
        subject = {
            "attempt": "J001: tentative",
            "final": "J001: résultat final",
        }[checkpoint]
        git("commit", "-m", subject)
        commit = git("rev-parse", "HEAD")
        git("push")
        assert learn.guide_pending_checkpoint(root, state, "J001") is False
        return commit

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0
    attempt_2 = commit_checkpoint("attempt", 2)
    final_2 = commit_checkpoint("final", 2)
    first_revision_history = json.loads(
        git(
            "show",
            f"{attempt_2}:learning/days/J001/.proof/revisions.json",
        )
    )
    assert first_revision_history["revisions"] == [
        {
            "reopened_at": first_revision_history["revisions"][0]["reopened_at"],
            "mode": "full-reattempt",
            "previous_attempt": initial_commits["attempt"],
            "previous_final": initial_commits["final"],
            "head_at_reopen": initial_commits["final"],
        }
    ]

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0
    attempt_3 = commit_checkpoint("attempt", 3)
    final_3 = commit_checkpoint("final", 3)
    second_revision_history = json.loads(
        git(
            "show",
            f"{attempt_3}:learning/days/J001/.proof/revisions.json",
        )
    )
    assert len(second_revision_history["revisions"]) == 2
    assert (
        second_revision_history["revisions"][0]
        == first_revision_history["revisions"][0]
    )
    assert second_revision_history["revisions"][1] == {
        "reopened_at": second_revision_history["revisions"][1]["reopened_at"],
        "mode": "full-reattempt",
        "previous_attempt": attempt_2,
        "previous_final": final_2,
        "head_at_reopen": final_2,
    }

    learn.state_path(root).unlink(missing_ok=True)
    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    assert rebuilt["days"]["J001"]["checkpoint_commits"] == {
        "prediction": initial_commits["prediction"],
        "attempt": attempt_3,
        "final": final_3,
    }


def test_checkpoint_hydration_rejects_replacements_rooted_in_an_invalid_final(
    tmp_path: Path,
) -> None:
    root, manifest, guide, state, _day, journal, commits = (
        _pushed_planned_checkpoint_chain(tmp_path, through="attempt")
    )

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    rogue_path = root / "rogue-between-attempt-and-final.txt"
    rogue_path.write_text("commit intermédiaire non autorisé\n", encoding="utf-8")
    git("add", rogue_path.name)
    git("commit", "-m", "rogue commit before final")
    rogue = git("rev-parse", "HEAD")
    git("push")

    plan_path = learn.checkpoint_plan_path(root, "J001")
    seal = learn.final_seal_path(root, "J001")
    seal.write_text('{"test": "invalid final"}\n', encoding="utf-8")
    invalid_final_paths = sorted(
        str(path.relative_to(root)) for path in (plan_path, seal)
    )
    learn.atomic_json(
        plan_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "checkpoint": "final",
            "base_head": rogue,
            "paths": invalid_final_paths,
        },
    )
    git("add", "--", *invalid_final_paths)
    git("commit", "-m", "J001: résultat final")
    invalid_final = git("rev-parse", "HEAD")
    assert (
        learn.checkpoint_plan_for_commit(root, "J001", "final", invalid_final)
        is not None
    )
    git("push")

    revisions_path = root / "learning/days/J001/.proof/revisions.json"
    forged_revision = {
        "reopened_at": learn.now_iso(),
        "mode": "full-reattempt",
        "previous_attempt": commits["attempt"],
        "previous_final": invalid_final,
        "head_at_reopen": invalid_final,
    }
    learn.atomic_json(
        revisions_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "revisions": [forged_revision],
        },
    )
    journal.write_text(
        journal.read_text(encoding="utf-8") + "\ntentative de remplacement\n",
        encoding="utf-8",
    )
    seal.unlink()
    with pytest.raises(learn.LearningError, match="aucun commit intermédiaire"):
        learn.begin_checkpoint(root, state, "J001", "attempt")
    attempt_2_paths = sorted(
        str(path.relative_to(root))
        for path in (journal, plan_path, revisions_path, seal)
    )
    learn.atomic_json(
        plan_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "checkpoint": "attempt",
            "base_head": invalid_final,
            "paths": attempt_2_paths,
        },
    )
    git("add", "--", *attempt_2_paths)
    git("commit", "-m", "J001: tentative")
    attempt_2 = git("rev-parse", "HEAD")
    git("push")
    assert (
        learn.checkpoint_plan_for_commit(root, "J001", "attempt", attempt_2) is not None
    )
    committed_revision = json.loads(
        git(
            "show",
            f"{attempt_2}:learning/days/J001/.proof/revisions.json",
        )
    )
    assert committed_revision["revisions"] == [forged_revision]

    journal.write_text(
        journal.read_text(encoding="utf-8") + "\nfinal de remplacement\n",
        encoding="utf-8",
    )
    seal.write_text('{"test": "replacement final"}\n', encoding="utf-8")
    final_2_paths = sorted(
        str(path.relative_to(root)) for path in (journal, plan_path, seal)
    )
    learn.atomic_json(
        plan_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "checkpoint": "final",
            "base_head": attempt_2,
            "paths": final_2_paths,
        },
    )
    git("add", "--", *final_2_paths)
    git("commit", "-m", "J001: résultat final")
    final_2 = git("rev-parse", "HEAD")
    git("push")
    assert learn.checkpoint_plan_for_commit(root, "J001", "final", final_2) is not None

    learn.state_path(root).unlink(missing_ok=True)
    rebuilt = learn.reconstruct_state(root)
    learn.ensure_day(root, manifest, guide, rebuilt)

    checkpoint_commits = rebuilt["days"]["J001"]["checkpoint_commits"]
    assert checkpoint_commits == {
        "prediction": commits["prediction"],
        "attempt": commits["attempt"],
    }
    assert checkpoint_commits != {
        "prediction": commits["prediction"],
        "attempt": attempt_2,
        "final": final_2,
    }
    assert invalid_final not in checkpoint_commits.values()
    assert attempt_2 not in checkpoint_commits.values()
    assert final_2 not in checkpoint_commits.values()


def test_checkpoint_hydration_keeps_an_unpushed_commit_pending(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    manifest, guide = learn.active_manifest(root)
    initial = learn.new_state()
    _day, journal = learn.ensure_day(root, manifest, guide, initial)
    initial["days"]["J001"]["branch"] = "learn/j001"
    journal.write_text(journal.read_text(encoding="utf-8") + "\nprévision\n")
    learn.begin_checkpoint(root, initial, "J001", "prediction")
    git("add", "--", *initial["days"]["J001"]["pending_checkpoint"]["paths"])
    git("commit", "-m", "J001: prévision")
    prediction = git("rev-parse", "HEAD")
    rebuilt = learn.new_state()
    rebuilt["days"]["J001"] = {"branch": "learn/j001"}

    learn.ensure_day(root, manifest, guide, rebuilt)

    day_state = rebuilt["days"]["J001"]
    assert day_state["checkpoint_commits"] == {}
    assert day_state["commit_checkpoints"] == []
    assert day_state["pending_checkpoint"]["name"] == "prediction"
    assert day_state["pending_checkpoint"]["commit"] == prediction
    assert learn.guide_pending_checkpoint(root, rebuilt, "J001") is True
    assert "git push --set-upstream origin HEAD" in capsys.readouterr().out


def test_checkpoint_hydration_rejects_a_pushed_prediction_outside_the_day(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    manifest, guide = learn.active_manifest(root)
    initial = learn.new_state()
    _day, journal = learn.ensure_day(root, manifest, guide, initial)
    initial["days"]["J001"]["branch"] = "learn/j001"
    journal.write_text(journal.read_text(encoding="utf-8") + "\nprévision\n")
    learn.begin_checkpoint(root, initial, "J001", "prediction")
    rogue = root / "lab-before-prediction.txt"
    rogue.write_text("action prématurée\n", encoding="utf-8")
    plan_path = learn.checkpoint_plan_path(root, "J001")
    forged_plan = learn.read_json(plan_path)
    forged_plan["paths"] = sorted([*forged_plan["paths"], rogue.name])
    learn.atomic_json(plan_path, forged_plan)
    git("add", ".")
    git("commit", "-m", "J001: prévision")
    git("push", "--set-upstream", "origin", "learn/j001")
    rebuilt = learn.new_state()
    rebuilt["days"]["J001"] = {"branch": "learn/j001"}

    learn.ensure_day(root, manifest, guide, rebuilt)

    day_state = rebuilt["days"]["J001"]
    assert day_state["checkpoint_commits"] == {}
    assert day_state["commit_checkpoints"] == []
    assert "pending_checkpoint" not in day_state


def test_checkpoint_hydration_rejects_a_prediction_after_an_intermediate_commit(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    baseline = git("rev-parse", "HEAD")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    rogue = root / "lab-before-prediction.txt"
    rogue.write_text("action prématurée\n", encoding="utf-8")
    git("add", rogue.name)
    git("commit", "-m", "premature lab commit")
    rogue_commit = git("rev-parse", "HEAD")

    manifest, guide = learn.active_manifest(root)
    card = learn.parse_day(guide, "J001")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(learn.render_template(root, manifest, card), encoding="utf-8")
    plan_path = learn.checkpoint_plan_path(root, "J001")
    plan_paths = sorted(
        [str(journal.relative_to(root)), str(plan_path.relative_to(root))]
    )
    learn.atomic_json(
        plan_path,
        {
            "schema_version": 1,
            "day_id": "J001",
            "checkpoint": "prediction",
            "base_head": rogue_commit,
            "paths": plan_paths,
        },
    )
    git("add", "learning/days/J001")
    git("commit", "-m", "J001: prévision")
    git("push", "--set-upstream", "origin", "learn/j001")

    rebuilt = learn.new_state()
    rebuilt["days"]["J001"] = {"branch": "learn/j001"}
    learn.ensure_day(root, manifest, guide, rebuilt)

    day_state = rebuilt["days"]["J001"]
    assert day_state["base_commit"] == baseline
    assert day_state["checkpoint_commits"] == {}
    assert day_state["commit_checkpoints"] == []
    assert "pending_checkpoint" not in day_state


def _finalised_day_fixture(tmp_path: Path) -> tuple[Path, dict[str, object], str, str]:
    root = tmp_path / "repo"
    proof = root / "learning/days/J001/.proof"
    proof.mkdir(parents=True)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")
    (proof / "ci.json").write_text('{"conclusion":"conforme"}\n')
    (proof / "review.json").write_text('{"status":"ready"}\n')
    (proof / "review.md").write_text("review\n")
    receipt = _write_raw_receipt(root)

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    (root / "attempt.txt").write_text("attempt\n")
    git("add", ".")
    git("commit", "-m", "J001: tentative")
    attempt = git("rev-parse", "HEAD")
    (root / "final.txt").write_text("final\n")
    git("add", ".")
    git("commit", "-m", "J001: résultat final")
    final = git("rev-parse", "HEAD")
    state: dict[str, object] = learn.new_state()
    state["days"] = {
        "J001": {
            "checkpoint_commits": {
                "prediction": git("rev-parse", "master"),
                "attempt": attempt,
                "final": final,
            },
            "commit_checkpoints": ["prediction", "attempt", "final"],
            "raw_evidence": receipt,
            "command_index": 1,
        }
    }
    return root, state, attempt, final


def test_reopen_final_after_regular_correction_requires_a_full_reattempt(
    tmp_path: Path,
) -> None:
    root, state, _attempt, _final = _finalised_day_fixture(tmp_path)

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0

    day_state = state["days"]["J001"]
    assert day_state["checkpoint_commits"] == {
        "prediction": subprocess.run(
            ["git", "rev-parse", "master"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    }
    assert day_state["commit_checkpoints"] == ["prediction"]
    assert day_state["command_index"] == 0
    assert "raw_evidence" not in day_state
    assert not (root / "learning/days/J001/.proof/raw-evidence.json").exists()
    history = json.loads(
        (root / "learning/days/J001/.proof/revisions.json").read_text()
    )
    assert history["revisions"][0]["mode"] == "full-reattempt"


def test_reopen_final_after_merge_update_keeps_review_and_attempt(
    tmp_path: Path,
) -> None:
    root, state, attempt, final = _finalised_day_fixture(tmp_path)

    subprocess.run(
        ["git", "switch", "-c", "upstream-update", "master"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (root / "upstream.txt").write_text("upstream\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "upstream update"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "HEAD:master"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "switch", "learn/j001"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "merge", "--no-ff", "upstream-update", "-m", "Update branch"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0

    day_state = state["days"]["J001"]
    assert day_state["checkpoint_commits"]["attempt"] == attempt
    assert "final" not in day_state["checkpoint_commits"]
    assert day_state["commit_checkpoints"] == ["prediction", "attempt"]
    assert (root / "learning/days/J001/.proof/raw-evidence.json").exists()
    assert (root / "learning/days/J001/.proof/review.json").exists()
    history = json.loads(
        (root / "learning/days/J001/.proof/revisions.json").read_text()
    )
    assert history["revisions"][0]["mode"] == "reseal-after-base-update"
    assert history["revisions"][0]["previous_final"] == final


def test_reopen_final_treats_an_untrusted_merge_as_a_full_reattempt(
    tmp_path: Path,
) -> None:
    root, state, _attempt, _final = _finalised_day_fixture(tmp_path)

    subprocess.run(
        ["git", "switch", "-c", "untrusted-solution", "master"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (root / "solution.txt").write_text("solution externe\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "untrusted solution"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "switch", "learn/j001"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "merge", "--no-ff", "untrusted-solution", "-m", "Merge solution"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0

    assert state["days"]["J001"]["commit_checkpoints"] == ["prediction"]
    history = json.loads(
        (root / "learning/days/J001/.proof/revisions.json").read_text()
    )
    assert history["revisions"][0]["mode"] == "full-reattempt"


def test_reopen_final_rejects_a_forged_tree_with_trusted_merge_parents(
    tmp_path: Path,
) -> None:
    root, state, _attempt, final = _finalised_day_fixture(tmp_path)

    rogue = root / "rogue.txt"
    rogue.write_text("contenu absent de la fusion déterministe\n")
    subprocess.run(
        ["git", "add", "rogue.txt"], cwd=root, check=True, capture_output=True
    )
    tree = subprocess.run(
        ["git", "write-tree"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    baseline = subprocess.run(
        ["git", "rev-parse", "master"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    forged = subprocess.run(
        ["git", "commit-tree", tree, "-p", final, "-p", baseline, "-m", "forged"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "reset", "--hard", forged],
        cwd=root,
        check=True,
        capture_output=True,
    )

    assert learn.reopen_final_checkpoint(root, state, "J001", confirmed=True) == 0

    assert state["days"]["J001"]["commit_checkpoints"] == ["prediction"]
    history = json.loads(
        (root / "learning/days/J001/.proof/revisions.json").read_text()
    )
    assert history["revisions"][0]["mode"] == "full-reattempt"


def test_attempt_checkpoint_includes_lab_deliverables_outside_the_journal(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "Initial fixture")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text("journal complet modifié\n", encoding="utf-8")
    baseline = root / "docs/cadrage/baseline.md"
    inventory = root / "inventory/baseline.json"
    baseline.parent.mkdir(parents=True)
    inventory.parent.mkdir(parents=True)
    baseline.write_text("baseline apprenant\n", encoding="utf-8")
    inventory.write_text('{"scope":"lab"}\n', encoding="utf-8")
    state = learn.new_state()
    state["days"]["J001"] = {
        "checkpoint_commits": {"prediction": learn.current_git_head(root)}
    }

    learn.begin_checkpoint(root, state, "J001", "attempt")

    assert set(state["days"]["J001"]["pending_checkpoint"]["paths"]) == {
        "docs/cadrage/baseline.md",
        "inventory/baseline.json",
        "learning/days/J001/.proof/checkpoint-plan.json",
        "learning/days/J001/learner.md",
    }


def test_attempt_checkpoint_accepts_a_rename_from_its_frozen_plan(
    tmp_path: Path,
) -> None:
    root = _minimal_repository(tmp_path)
    (root / ".gitignore").write_text(".learning/\n", encoding="utf-8")
    old = root / "old.txt"
    old.write_text("livrable\n", encoding="utf-8")

    def git(*arguments: str, cwd: Path = root) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "master")
    git("config", "user.name", "Learning Test")
    git("config", "user.email", "learning-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "baseline")
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    git("remote", "add", "origin", str(remote))
    git("push", "--set-upstream", "origin", "master")
    git("switch", "-c", "learn/j001")
    git("mv", "old.txt", "new.txt")
    journal = root / "learning/days/J001/learner.md"
    journal.parent.mkdir(parents=True)
    journal.write_text("journal de tentative\n", encoding="utf-8")
    state = learn.new_state()
    state["days"]["J001"] = {
        "branch": "learn/j001",
        "checkpoint_commits": {"prediction": learn.current_git_head(root)},
    }
    learn.begin_checkpoint(root, state, "J001", "attempt")
    paths = state["days"]["J001"]["pending_checkpoint"]["paths"]
    git("add", "--", *learn.checkpoint_unstaged_paths(root, paths))
    git("commit", "-m", "J001: tentative")
    git("push", "--set-upstream", "origin", "learn/j001")

    assert learn.guide_pending_checkpoint(root, state, "J001") is False


def test_unchanged_state_is_not_rewritten(tmp_path: Path) -> None:
    root = _minimal_repository(tmp_path)
    state = learn.new_state()
    learn.save_state(root, state)
    before = learn.state_path(root).read_bytes()

    learn.save_state(root, state)

    assert learn.state_path(root).read_bytes() == before


def test_professor_launch_explicitly_invokes_the_repo_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    journal = root / "learning/days/J001/learner.md"
    calls: list[list[str]] = []
    monkeypatch.setattr(learn, "_command_available", lambda command: command == "codex")

    def fake_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(learn.subprocess, "run", fake_run)
    day = learn.DayCard(
        "J001",
        "Objectif",
        "Objectif observable",
        "Garde-fou",
        "JOUR 001",
        (),
        "Détails",
    )

    assert learn.launch_professor(root, day, journal, "Ma prévision") == 0
    assert calls[0][0] == "codex"
    assert "$aegis-professor" in calls[0][-1]
    assert "Ne rédige pas le contenu apprenant" in calls[0][-1]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"visibility": "PUBLIC", "isPrivate": False}, True),
        ({"visibility": "PRIVATE", "isPrivate": True}, False),
        ({"visibility": "INTERNAL", "isPrivate": False}, False),
    ],
)
def test_remote_visibility_requires_an_explicitly_public_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    expected: bool,
) -> None:
    monkeypatch.setattr(learn, "_command_available", lambda command: command == "gh")

    def fake_run(
        arguments: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == [
            "gh",
            "repo",
            "view",
            "--json",
            "visibility,isPrivate,nameWithOwner",
        ]
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(learn, "run", fake_run)

    check = learn.remote_visibility(tmp_path)

    assert check.name == "Dépôt public"
    assert check.ok is expected
    assert check.blocking is True
    assert ("confirme PUBLIC" in check.detail) is expected


def test_noninteractive_cockpit_prepares_exactly_one_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _minimal_repository(tmp_path)
    (tmp_path / "offline-store").mkdir()
    local = root / ".learning/local.json"
    local.parent.mkdir(parents=True)
    local.write_text(
        json.dumps(
            {
                "aliases": {
                    "fedora": "fedora-lab",
                    "ubuntu": "ubuntu-lab",
                    "vps": "vps-lab",
                },
                "age_recipient": "age1" + "q" * 58,
                "raw_store": str(tmp_path / "raw-store"),
                "offline_store": str(tmp_path / "offline-store"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(learn, "_command_available", lambda _command: True)
    monkeypatch.setattr(learn, "selected_editor", lambda: "vim")
    monkeypatch.setattr(
        learn,
        "remote_visibility",
        lambda _root: learn.DoctorCheck("Dépôt public", True, True, "PUBLIC"),
    )
    monkeypatch.setattr(
        learn,
        "personal_signing_check",
        lambda _root: learn.DoctorCheck(
            "Signature Git personnelle", True, True, "configurée"
        ),
    )
    monkeypatch.setattr(
        learn,
        "local_configuration_check",
        lambda _root: learn.DoctorCheck(
            "Configuration locale", True, True, "configurée"
        ),
    )

    assert learn.run_interactive(root, details=False, no_editor=True) == 0
    assert (root / "learning/days/J001/learner.md").is_file()
    assert not (root / "learning/days/J002").exists()


def test_doctor_accepts_an_ssh_signing_key_and_allowed_signers_outside_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "master"], cwd=root, check=True)
    key = tmp_path / "personal-signing-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
    )
    public_key = key.with_suffix(".pub")
    allowed = tmp_path / "allowed_signers"
    allowed.write_text(f"aegis-learning {public_key.read_text().strip()}\n")
    subprocess.run(["git", "config", "gpg.format", "ssh"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.signingkey", str(public_key)],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "gpg.ssh.allowedSignersFile", str(allowed)],
        cwd=root,
        check=True,
    )
    identity = learn._parse_ssh_public_key(public_key.read_text())
    assert identity is not None
    monkeypatch.setattr(
        learn, "_ssh_agent_public_keys", lambda _root: {(identity[0], identity[1])}
    )

    check = learn.personal_signing_check(root)

    assert check.ok
    assert check.blocking


def test_doctor_rejects_ssh_signing_without_allowed_signers(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "master"], cwd=root, check=True)
    key = tmp_path / "personal-signing-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
    )
    subprocess.run(["git", "config", "gpg.format", "ssh"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.signingkey", str(key.with_suffix(".pub"))],
        cwd=root,
        check=True,
    )

    check = learn.personal_signing_check(root)

    assert not check.ok
    assert "allowedSignersFile" in check.detail


def test_doctor_rejects_openpgp_without_an_explicit_secret_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(learn, "_git_config", lambda *_args, **_kwargs: "")

    check = learn.personal_signing_check(tmp_path)

    assert not check.ok
    assert check.blocking


def test_doctor_rejects_a_recipient_that_only_matches_the_age_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(learn, "_command_available", lambda _command: True)
    monkeypatch.setattr(
        learn,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "invalid"),
    )

    assert not learn._age_recipient_usable(tmp_path, "age1" + "q" * 58)


def _minimal_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    guide = root / "curriculum/v2.0.0/guide.md"
    guide.parent.mkdir(parents=True)
    guide.write_text(
        "### JOUR 001 | PHASE 0\n"
        "#### Un objectif test\n"
        "**Objectif observable :** Produire une preuve de test.\n"
        "#### À comprendre avant d'agir\n"
        "Une notion issue du guide.\n"
        "**Préparation obligatoire :** Rester dans le dépôt de test.\n"
        "#### Commandes ou contrôles à adapter\n"
        "```text\n"
        "printf test\n"
        "```\n",
        encoding="utf-8",
    )
    digest = learn.sha256_file(guide)
    manifest = {
        "active_version": "2.0.0",
        "guide_path": "curriculum/v2.0.0/guide.md",
        "sha256": digest,
        "total_main_days": 370,
        "total_consolidation_days": 20,
        "audited_phases": [0],
        "global_contract_reviewed": True,
        "versions": {
            "2.0.0": {
                "status": "active",
                "guide_path": "curriculum/v2.0.0/guide.md",
                "sha256": digest,
                "audited_phases": [0],
                "audit_reports": {
                    "phase-0": {
                        "path": "curriculum/audits/phase-00.md",
                        "sha256": learn.sha256_text("# Audit fixture\n"),
                    }
                },
            }
        },
        "audit_reports": {
            "phase-0": {
                "path": "curriculum/audits/phase-00.md",
                "sha256": learn.sha256_text("# Audit fixture\n"),
            }
        },
    }
    (root / "curriculum/active.json").write_text(json.dumps(manifest), encoding="utf-8")
    audit = root / "curriculum/audits/phase-00.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("# Audit fixture\n", encoding="utf-8")
    template_source = REPOSITORY_ROOT / "learning/templates/learner.md"
    template_target = root / "learning/templates/learner.md"
    template_target.parent.mkdir(parents=True)
    template_target.write_text(
        template_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return root
