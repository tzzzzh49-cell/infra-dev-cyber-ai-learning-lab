#!/usr/bin/env python3
"""Cockpit local du parcours : une commande, un journal, une étape à la fois."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOTAL_MAIN_DAYS = 370
TOTAL_CONSOLIDATION_DAYS = 20
TOTAL_DAYS = TOTAL_MAIN_DAYS + TOTAL_CONSOLIDATION_DAYS
DEFAULT_DAY = "J001"
PHASE_BOUNDARIES = (10, 40, 70, 100, 120, 155, 185, 210, 235, 260, 285, 305, 345, 370)
ALLOWED_STATUSES = {"En cours", "À reprendre", "Bloqué", "Validé"}
LEARNER_SECTIONS = (
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
)
PROOF_SECTIONS = (*LEARNER_SECTIONS, "Erreur utile", "Statut")
REVIEW_SECTIONS = tuple(title for title in PROOF_SECTIONS if title != "Statut")
PLACEHOLDER_PREFIXES = (
    "_Avant ",
    "_Je ",
    "_Résultat ",
    "_Refus ",
    "_Cible ",
    "_Résumé ",
    "_Traduction ",
    "_Une ",
    "_Les ",
)
SAFE_ALIAS = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
AGE_RECIPIENT = re.compile(r"^age1[0-9a-z]{58}$")
RAW_EVIDENCE_ID = re.compile(r"^j[0-9]{3}-[0-9a-f]{32}$")
RAW_EVIDENCE_RETENTION = "one-year-after-pathway-completion"
PERSONAL_SIGNING_PRINCIPAL = "aegis-learning"
RAW_EVIDENCE_RECEIPT_FIELDS = {
    "schema_version",
    "id",
    "sha256",
    "copies",
    "retention",
    "verified_at",
}
IGNORED_RUNTIME_ROOTS = {
    ".learning",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "node_modules",
    "venv",
}
IGNORED_SENSITIVE_ROOTS = {".env", ".secrets", ".ssh", "secrets"}
PROTECTED_LEARNING_PATHS = (
    "curriculum/",
    ".codex/skills/aegis-professor/",
    ".github/workflows/ci.yml",
    ".github/workflows/publish-learning.yml",
    "learning/schemas/",
    "learning/templates/",
    "tools/learn.py",
    "tools/learning_public_anchor.py",
    "tools/learning_publish.py",
)
REQUIRED_CI_CHECK_NAMES = {
    "Python 3.12 lint, compose config, tests and Bandit",
    "Python 3.13 lint, compose config, tests and Bandit",
    "Gitleaks secret scan",
    "Hadolint Dockerfile",
    "Trivy image scan",
    "OWASP ZAP API scan",
}


class LearningError(RuntimeError):
    """Erreur attendue et présentable à l'apprenant."""


@dataclass(frozen=True)
class DayCard:
    day_id: str
    title: str
    objective: str
    guardrail: str
    reference: str
    commands: tuple[str, ...]
    details: str
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    blocking: bool
    detail: str


def now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LearningError(f"Fichier requis absent : {path}") from exc
    except json.JSONDecodeError as exc:
        raise LearningError(f"JSON invalide dans {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LearningError(f"Objet JSON attendu dans {path}")
    return payload


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def raw_evidence_receipt_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / ".proof" / "raw-evidence.json"


def raw_evidence_receipt(
    root: Path, day_id: str, *, required: bool = False
) -> dict[str, Any] | None:
    path = raw_evidence_receipt_path(root, day_id)
    if not path.exists():
        if required:
            raise LearningError(f"Reçu de preuve brute absent pour {day_id}.")
        return None
    payload = read_json(path)
    expected_id = re.compile(rf"^{re.escape(day_id.lower())}-[0-9a-f]{{32}}$")
    if (
        set(payload) != RAW_EVIDENCE_RECEIPT_FIELDS
        or payload.get("schema_version") != 1
        or not isinstance(payload.get("id"), str)
        or expected_id.fullmatch(str(payload.get("id"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(payload.get("sha256", ""))) is None
        or payload.get("copies") != 2
        or payload.get("retention") != RAW_EVIDENCE_RETENTION
        or not _valid_timestamp(payload.get("verified_at"))
    ):
        raise LearningError(f"Reçu de preuve brute invalide pour {day_id}.")
    return payload


def run(
    arguments: list[str],
    *,
    cwd: Path,
    check: bool = False,
    timeout: int = 30,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
    )


def ensure_inside(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise LearningError(f"Chemin hors dépôt refusé : {candidate}")
    return resolved


def active_manifest(root: Path) -> tuple[dict[str, Any], Path]:
    manifest = read_json(root / "curriculum" / "active.json")
    required = {
        "active_version",
        "guide_path",
        "sha256",
        "total_main_days",
        "total_consolidation_days",
        "audited_phases",
        "global_contract_reviewed",
        "versions",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise LearningError("Manifeste du guide incomplet : " + ", ".join(missing))
    if manifest["total_main_days"] != TOTAL_MAIN_DAYS:
        raise LearningError("Le manifeste doit déclarer 370 journées principales.")
    if manifest["total_consolidation_days"] != TOTAL_CONSOLIDATION_DAYS:
        raise LearningError("Le manifeste doit déclarer 20 consolidations.")
    if not manifest["global_contract_reviewed"] or 0 not in manifest["audited_phases"]:
        raise LearningError(
            "Le contrat global et l'audit de la phase 0 doivent être validés "
            "avant J001."
        )
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
        or active_record.get("audit_reports") != manifest.get("audit_reports")
    ):
        raise LearningError("Le registre de la version active est incohérent.")
    guide = ensure_inside(root, root / str(manifest["guide_path"]))
    actual = sha256_file(guide)
    if actual != manifest["sha256"]:
        raise LearningError(
            f"Intégrité du guide invalide : attendu {manifest['sha256']}, "
            f"obtenu {actual}."
        )
    reports = manifest.get("audit_reports", {})
    if not isinstance(reports, dict):
        raise LearningError("Le registre des rapports d'audit est invalide.")
    for phase in manifest["audited_phases"]:
        report = reports.get(f"phase-{int(phase)}")
        if not isinstance(report, dict) or set(report) != {"path", "sha256"}:
            raise LearningError(f"Rapport d'audit absent pour la phase {phase}.")
        report_path = ensure_inside(root, root / str(report["path"]))
        if not report_path.is_file():
            raise LearningError(f"Rapport d'audit introuvable pour la phase {phase}.")
        if sha256_file(report_path) != report["sha256"]:
            raise LearningError(f"Empreinte d'audit invalide pour la phase {phase}.")
    return manifest, guide


def registered_guide(
    root: Path,
    manifest: dict[str, Any],
    version: str,
    expected_sha256: str,
    *,
    phase: int | None = None,
) -> Path:
    """Résout une version gelée sans réinterpréter une ancienne preuve."""

    versions = manifest.get("versions", {})
    record: Any = versions.get(version) if isinstance(versions, dict) else None
    if record is None and version == manifest.get("active_version"):
        record = {
            "status": "active",
            "guide_path": manifest.get("guide_path"),
            "sha256": manifest.get("sha256"),
            "audited_phases": manifest.get("audited_phases"),
        }
    if not isinstance(record, dict):
        raise LearningError(f"Version de guide non enregistrée : {version}")
    if record.get("status") not in {"active", "superseded-creditable"}:
        raise LearningError(f"Version de guide non créditable : {version}")
    audited_phases = record.get("audited_phases")
    if (
        not isinstance(audited_phases, list)
        or any(not isinstance(value, int) for value in audited_phases)
        or (phase is not None and phase not in audited_phases)
    ):
        raise LearningError(
            f"La phase {phase} n'est pas auditée pour le guide {version}."
        )
    if phase is not None:
        audit_reports = record.get("audit_reports")
        report = (
            audit_reports.get(f"phase-{phase}")
            if isinstance(audit_reports, dict)
            else None
        )
        if not isinstance(report, dict) or set(report) != {"path", "sha256"}:
            raise LearningError(
                f"Rapport d'audit absent pour la phase {phase} du guide {version}."
            )
        report_path = ensure_inside(root, root / str(report["path"]))
        if not report_path.is_file() or sha256_file(report_path) != report["sha256"]:
            raise LearningError(
                f"Rapport d'audit altéré pour la phase {phase} du guide {version}."
            )
    if record.get("sha256") != expected_sha256:
        raise LearningError(f"Empreinte non enregistrée pour le guide {version}.")
    guide = ensure_inside(root, root / str(record.get("guide_path", "")))
    if not guide.is_file() or sha256_file(guide) != expected_sha256:
        raise LearningError(f"Guide historique {version} absent ou altéré.")
    return guide


def curriculum_for_day(
    root: Path,
    manifest: dict[str, Any],
    active_guide: Path,
    state: dict[str, Any],
    day_id: str,
) -> tuple[dict[str, Any], Path]:
    day_state = state.get("days", {}).get(day_id, {})
    version = day_state.get("guide_version")
    digest = day_state.get("guide_sha256")
    if not version and not digest:
        return manifest, active_guide
    if not isinstance(version, str) or not isinstance(digest, str):
        raise LearningError(f"Épinglage du guide incomplet pour {day_id}.")
    if version == manifest["active_version"] and digest == manifest["sha256"]:
        return manifest, active_guide
    guide = registered_guide(
        root,
        manifest,
        version,
        digest,
        phase=phase_for_day(day_id),
    )
    record = manifest["versions"][version]
    pinned = dict(manifest)
    pinned["active_version"] = version
    pinned["guide_path"] = record["guide_path"]
    pinned["sha256"] = digest
    pinned["audited_phases"] = list(record["audited_phases"])
    pinned["audit_reports"] = dict(record["audit_reports"])
    return pinned, guide


def _first(pattern: str, text: str, default: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return " ".join(match.group(1).split()) if match else default


def parse_day(guide: Path, day_id: str) -> DayCard:
    number = int(day_id.removeprefix("J"))
    text = guide.read_text(encoding="utf-8")
    header = re.compile(rf"^### JOUR {number:03d}\b.*$", re.MULTILINE)
    match = header.search(text)
    if not match:
        if number > TOTAL_MAIN_DAYS and number <= TOTAL_DAYS:
            consolidation = re.search(
                rf"(?m)^\|\s*{number}\s*\|[^|]+\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
                text,
            )
            if consolidation is None:
                raise LearningError(
                    f"Consolidation absente de l'annexe du guide : {day_id}"
                )
            work = " ".join(consolidation.group(1).split())
            validation = " ".join(consolidation.group(2).split())
            return DayCard(
                day_id=day_id,
                title=work,
                objective=work,
                guardrail="Ne pas introduire de nouveau sujet hors du guide actif.",
                reference=f"Appendice A, journée {number}",
                commands=(),
                details=f"Validation issue du guide : {validation}",
            )
        raise LearningError(f"Journée absente du guide actif : {day_id}")
    next_match = re.search(r"^### JOUR \d{3}\b.*$", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    block = text[match.start() : end]
    title = _first(r"^#### ([^\n]+)", block, day_id)
    objective = _first(r"\*\*Objectif observable\s*:\*\*\s*([^\n]+)", block, title)
    guardrail = _first(
        r"\*\*Préparation obligatoire\s*:\*\*\s*([^\n]+)",
        block,
        "Lire le garde-fou de la phase avant toute action.",
    )
    command_match = re.search(
        r"#### Commandes ou contrôles à adapter\s*```(?:text|console|bash)?\s*(.*?)```",
        block,
        flags=re.MULTILINE | re.DOTALL,
    )
    command_area = command_match.group(1).strip() if command_match else ""
    commands = tuple(line.strip() for line in command_area.splitlines() if line.strip())
    details = _first(
        r"#### À comprendre avant d'agir\s*(.*?)\s*\*\*Préparation obligatoire",
        block,
        "Consulter la fiche du guide actif.",
    )
    return DayCard(
        day_id=day_id,
        title=title,
        objective=objective,
        guardrail=guardrail,
        reference=f"{match.group(0).removeprefix('### ').strip()}",
        commands=commands,
        details=details,
    )


def activated_day_card(
    guide: Path,
    day_id: str,
    activation: dict[str, Any] | None = None,
) -> DayCard:
    card = parse_day(guide, day_id)
    if activation is None or activation.get("kind") != "blocked-day":
        return card
    number = int(day_id.removeprefix("J"))
    trigger = activation.get("triggered_by")
    if not TOTAL_MAIN_DAYS < number <= TOTAL_DAYS or not isinstance(trigger, str):
        raise LearningError("Activation de consolidation bloquée invalide.")
    match = re.fullmatch(r"J(\d{3})", trigger)
    if match is None or not 1 <= int(match.group(1)) <= TOTAL_MAIN_DAYS:
        raise LearningError("Journée source de consolidation invalide.")
    source = parse_day(guide, trigger)
    references = (card.reference, source.reference)
    return DayCard(
        day_id=day_id,
        title=f"Consolidation de {trigger} — {source.title}",
        objective=source.objective,
        guardrail=source.guardrail,
        reference=" + ".join(references),
        commands=source.commands,
        details=f"Matière reprise depuis {source.reference}. {source.details}",
        references=references,
    )


def guide_references(day: DayCard) -> list[str]:
    return list(day.references or (day.reference,))


def render_template(root: Path, manifest: dict[str, Any], day: DayCard) -> str:
    template = (root / "learning" / "templates" / "learner.md").read_text(
        encoding="utf-8"
    )
    values = {
        "day_id": day.day_id,
        "title": day.title,
        "guide_version": str(manifest["active_version"]),
        "guide_sha256": str(manifest["sha256"]),
        "guide_reference": day.reference,
        "objective": day.objective,
        "guardrail": day.guardrail,
    }
    for key, value in values.items():
        template = template.replace("{{ " + key + " }}", value)
    if re.search(r"{{\s*[^}]+\s*}}", template):
        raise LearningError("Le gabarit learner.md contient un placeholder inconnu.")
    return template


def learner_guide_identity(markdown: str) -> tuple[str, str] | None:
    match = re.search(
        r"(?m)^> Guide actif : ([0-9]+\.[0-9]+\.[0-9]+) "
        r"\(`([0-9a-f]{64})`\)[ \t]*$",
        markdown,
    )
    return match.groups() if match else None


def section(markdown: str, title: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(title)}[ \t]*\n(.*?)(?=^## |\Z)", markdown)
    return match.group(1).strip() if match else ""


def meaningful(value: str) -> bool:
    value = re.sub(r"(?ms)^_.*?_$", "", value)
    lines = []
    for line in value.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("<!--"):
            continue
        if cleaned.startswith(PLACEHOLDER_PREFIXES) and cleaned.endswith("_"):
            continue
        lines.append(cleaned)
    return len(" ".join(lines)) >= 8


def learner_status(markdown: str) -> str:
    value = section(markdown, "Statut")
    match = re.search(r"^Statut:\s*(.+?)\s*$", value, re.MULTILINE)
    if not match:
        return ""
    return match.group(1)


def next_incomplete(markdown: str) -> str | None:
    for title in LEARNER_SECTIONS:
        if not meaningful(section(markdown, title)):
            return title
    status = learner_status(markdown)
    if status not in ALLOWED_STATUSES or status in {"En cours", "À reprendre"}:
        return "Statut"
    return None


def next_learning_step(
    markdown: str, day: DayCard, day_state: dict[str, Any]
) -> str | None:
    needed = next_incomplete(markdown)
    command_index = int(day_state.get("command_index", 0))
    if meaningful(section(markdown, "Ma prévision")) and command_index < len(
        day.commands
    ):
        return "Mes observations"
    if (
        day_state.get("resume_from_consolidation")
        and learner_status(markdown) == "Bloqué"
    ):
        return "Statut"
    return needed


def heading_line(markdown: str, title: str) -> int:
    for index, line in enumerate(markdown.splitlines(), start=1):
        if line.strip() == f"## {title}":
            return index + 2
    return 1


def editor_arguments(editor: str, path: Path, line: int) -> list[str]:
    arguments = shlex.split(editor)
    if not arguments:
        raise LearningError("Éditeur vide.")
    executable = Path(arguments[0]).name
    if "{file}" in editor or "{line}" in editor:
        return [
            part.replace("{file}", str(path)).replace("{line}", str(line))
            for part in arguments
        ]
    if executable in {"code", "codium"}:
        return [*arguments, "--goto", f"{path}:{line}"]
    if executable in {"vim", "nvim", "vi", "nano"}:
        return [*arguments, f"+{line}", str(path)]
    return [*arguments, str(path)]


def selected_editor() -> str | None:
    for variable in ("LEARN_EDITOR", "VISUAL", "EDITOR"):
        if value := os.environ.get(variable, "").strip():
            return value
    for fallback in ("code", "codium", "nvim", "vim", "nano", "vi"):
        if shutil.which(fallback):
            return fallback
    return None


def open_editor(path: Path, title: str) -> None:
    editor = selected_editor()
    if editor is None:
        raise LearningError(
            f"Aucun éditeur détecté. Ouvre manuellement {path} à la section "
            f"« {title} »."
        )
    markdown = path.read_text(encoding="utf-8")
    subprocess.run(
        editor_arguments(editor, path, heading_line(markdown, title)), check=False
    )


def launch_professor(root: Path, day: DayCard, path: Path, needed: str) -> int:
    if not _command_available("codex"):
        raise LearningError(
            "Codex CLI est absent ; utilise l'éditeur puis reprends ici."
        )
    prompt = (
        f"Utilise $aegis-professor pour reprendre {day.day_id}. "
        f"Référence épinglée : {day.reference}. "
        f"Le cockpit attend la rubrique « {needed} » dans {path.relative_to(root)}. "
        "Ne rédige pas le contenu apprenant et ne relance pas make learn."
    )
    result = subprocess.run(
        [
            "codex",
            "--no-alt-screen",
            "--cd",
            str(root),
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "on-request",
            prompt,
        ],
        check=False,
    )
    return result.returncode


def local_config_path(root: Path) -> Path:
    return root / ".learning" / "local.json"


def initialize_local_config(root: Path, *, interactive: bool) -> dict[str, Any] | None:
    path = local_config_path(root)
    if path.exists():
        return read_json(path)
    if not interactive:
        return None
    print("Premier lancement — configuration locale sans adresse ni secret.")
    aliases: dict[str, str] = {}
    for key, label, default in (
        ("fedora", "poste Fedora", "fedora-lab"),
        ("ubuntu", "VM Ubuntu", "ubuntu-lab"),
        ("vps", "VPS", "vps-lab"),
    ):
        value = (
            input(f"Alias SSH pseudonyme pour {label} [{default}] : ").strip()
            or default
        )
        if not SAFE_ALIAS.fullmatch(value):
            raise LearningError(
                "Alias refusé : utilise seulement lettres, chiffres, point, "
                "tiret ou underscore."
            )
        aliases[key] = value
    recipient = input(
        "Clé publique age dédiée (age1..., jamais la clé privée) : "
    ).strip()
    if not AGE_RECIPIENT.fullmatch(recipient):
        raise LearningError("La clé publique age dédiée est invalide.")
    default_primary = Path.home() / ".local" / "state" / "aegis-learning" / "raw"
    raw_store = input(f"Stockage chiffré principal [{default_primary}] : ").strip()
    offline_store = input("Point de montage du stockage hors ligne : ").strip()
    payload = {
        "schema_version": 1,
        "aliases": aliases,
        "editor": selected_editor(),
        "age_recipient": recipient,
        "raw_store": raw_store or str(default_primary),
        "offline_store": offline_store,
        "created_at": now_iso(),
    }
    atomic_json(path, payload)
    return payload


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _tar_supports_zstd(root: Path) -> bool:
    if not _command_available("tar"):
        return False
    result = run(["tar", "--help"], cwd=root)
    return result.returncode == 0 and "--zstd" in result.stdout


def remote_privacy(root: Path) -> DoctorCheck:
    if not _command_available("gh"):
        return DoctorCheck("GitHub", False, True, "`gh` est absent.")
    result = run(
        ["gh", "repo", "view", "--json", "visibility,isPrivate,nameWithOwner"],
        cwd=root,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().splitlines()
        detail = message[0] if message else "Impossible d'interroger GitHub."
        return DoctorCheck(
            "Dépôt privé",
            False,
            True,
            f"{detail} Relance `gh auth login -h github.com` puis `make learn`.",
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return DoctorCheck("Dépôt privé", False, True, "Réponse GitHub illisible.")
    private = bool(payload.get("isPrivate")) or payload.get("visibility") == "PRIVATE"
    return DoctorCheck(
        "Dépôt privé",
        private,
        True,
        "GitHub confirme PRIVATE." if private else "Le dépôt GitHub est encore public.",
    )


def _age_recipient_usable(root: Path, recipient: str) -> bool:
    if AGE_RECIPIENT.fullmatch(recipient) is None or not _command_available("age"):
        return False
    result = run(
        ["age", "--encrypt", "--armor", "--recipient", recipient],
        cwd=root,
        timeout=5,
        input_text="",
    )
    return result.returncode == 0 and result.stdout.startswith("-----BEGIN AGE")


def local_configuration_check(root: Path) -> DoctorCheck:
    path = local_config_path(root)
    if not path.exists():
        return DoctorCheck(
            "Configuration locale", False, True, "Initialisation requise."
        )
    try:
        config = read_json(path)
        aliases = config.get("aliases", {})
        aliases_ok = isinstance(aliases, dict) and all(
            SAFE_ALIAS.fullmatch(str(aliases.get(key, "")))
            for key in ("fedora", "ubuntu", "vps")
        )
        recipient_ok = _age_recipient_usable(root, str(config.get("age_recipient", "")))
        primary = _outside_repository(
            root, str(config.get("raw_store", "")), "Le stockage principal"
        )
        offline = _outside_repository(
            root, str(config.get("offline_store", "")), "Le stockage hors ligne"
        )
        stores_ok = (
            primary != offline
            and primary.is_dir()
            and offline.is_dir()
            and primary.stat().st_dev != offline.stat().st_dev
        )
    except (LearningError, OSError):
        aliases_ok = recipient_ok = stores_ok = False
    ok = aliases_ok and recipient_ok and stores_ok
    detail = (
        ".learning/local.json — alias pseudonymes et deux stockages configurés."
        if ok
        else (
            "Complète les alias, une clé publique age opérationnelle et deux "
            "répertoires hors dépôt situés sur des systèmes de fichiers distincts."
        )
    )
    return DoctorCheck("Configuration locale", ok, True, detail)


def _git_config(root: Path, key: str, *, path: bool = False) -> str:
    arguments = ["git", "config"]
    if path:
        arguments.append("--path")
    arguments.extend(["--get", key])
    result = run(arguments, cwd=root)
    return result.stdout.strip() if result.returncode == 0 else ""


def _parse_ssh_public_key(value: str) -> tuple[str, str, str] | None:
    fields = value.strip().split()
    if len(fields) < 2:
        return None
    key_type, encoded = fields[:2]
    if not (
        key_type.startswith("ssh-")
        or key_type.startswith("ecdsa-")
        or key_type.startswith("sk-")
    ):
        return None
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not blob:
        return None
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    return key_type, encoded, f"SHA256:{digest}"


def _ssh_agent_public_keys(root: Path) -> set[tuple[str, str]]:
    if not _command_available("ssh-add"):
        return set()
    result = run(["ssh-add", "-L"], cwd=root, timeout=5)
    if result.returncode != 0:
        return set()
    return {
        (identity[0], identity[1])
        for line in result.stdout.splitlines()
        if (identity := _parse_ssh_public_key(line)) is not None
    }


def _allowed_ssh_signers(root: Path) -> dict[tuple[str, str], set[str]]:
    allowed_value = _git_config(root, "gpg.ssh.allowedSignersFile", path=True)
    try:
        allowed_path = _outside_repository(
            root, allowed_value, "Le fichier allowed_signers"
        )
        if not allowed_path.is_file() or allowed_path.stat().st_size > 1_000_000:
            return {}
        allowed_text = allowed_path.read_text(encoding="utf-8")
    except (LearningError, OSError, UnicodeError):
        return {}
    identities: dict[tuple[str, str], set[str]] = {}
    for line in allowed_text.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        principals = set(fields[0].split(","))
        candidate = next(
            (
                parsed
                for index in range(1, len(fields))
                if (parsed := _parse_ssh_public_key(" ".join(fields[index:])))
                is not None
            ),
            None,
        )
        if candidate is not None:
            identities.setdefault((candidate[0], candidate[1]), set()).update(
                principals
            )
    return identities


def _allowed_signing_fingerprints(root: Path) -> set[str]:
    return {
        identity[2]
        for key, principals in _allowed_ssh_signers(root).items()
        if PERSONAL_SIGNING_PRINCIPAL in principals
        and (identity := _parse_ssh_public_key(" ".join(key))) is not None
    }


def _ssh_signing_fingerprint(root: Path, *, require_agent: bool) -> str | None:
    if (_git_config(root, "gpg.format") or "openpgp").lower() != "ssh":
        return None
    signing_value = _git_config(root, "user.signingkey")
    if signing_value.startswith("key::"):
        public_text = signing_value.removeprefix("key::")
    elif signing_value.startswith(("ssh-", "ecdsa-", "sk-")):
        public_text = signing_value
    else:
        configured_path = _git_config(root, "user.signingkey", path=True)
        if not configured_path:
            return None
        try:
            key_path = _outside_repository(root, configured_path, "La clé publique")
            if not key_path.is_file() or key_path.stat().st_size > 16_384:
                return None
            public_text = key_path.read_text(encoding="utf-8")
        except (LearningError, OSError, UnicodeError):
            return None
    identity = _parse_ssh_public_key(public_text)
    if identity is None:
        return None
    key_type, encoded, fingerprint = identity
    allowed_principals = _allowed_ssh_signers(root).get((key_type, encoded), set())
    if PERSONAL_SIGNING_PRINCIPAL not in allowed_principals:
        return None
    if require_agent and (key_type, encoded) not in _ssh_agent_public_keys(root):
        return None
    return fingerprint


def personal_signing_check(root: Path) -> DoctorCheck:
    fingerprint = _ssh_signing_fingerprint(root, require_agent=True)
    ok = _command_available("ssh-keygen") and fingerprint is not None
    return DoctorCheck(
        "Signature Git personnelle",
        ok,
        True,
        (
            f"Clé SSH personnelle {fingerprint} chargée dans ssh-agent et autorisée."
            if ok
            else (
                "Configure `gpg.format=ssh`, une clé publique `user.signingKey` "
                "hors dépôt, charge sa clé privée dans ssh-agent et référence un "
                "`gpg.ssh.allowedSignersFile` contenant exactement cette clé."
            )
        ),
    )


def doctor(root: Path, *, include_remote: bool = True) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    git_available = _command_available("git")
    age_available = _command_available("age")
    tar_available = _tar_supports_zstd(root)
    editor = selected_editor()
    codex_available = _command_available("codex")
    try:
        manifest, guide = active_manifest(root)
        checks.append(
            DoctorCheck(
                "Guide actif",
                True,
                True,
                f"{manifest['active_version']} — {guide.relative_to(root)}",
            )
        )
    except LearningError as exc:
        checks.append(DoctorCheck("Guide actif", False, True, str(exc)))
    checks.extend(
        [
            DoctorCheck(
                "Git",
                git_available,
                True,
                "Disponible." if git_available else "Absent.",
            ),
            DoctorCheck(
                "Chiffrement age",
                age_available,
                True,
                "Disponible."
                if age_available
                else "Installe `age` avant de produire une preuve.",
            ),
            DoctorCheck(
                "Archive tar+zstd",
                tar_available,
                True,
                "Disponible."
                if tar_available
                else "Installe GNU tar avec la prise en charge de `--zstd`.",
            ),
            DoctorCheck(
                "Éditeur",
                editor is not None,
                True,
                editor or "Configure `$VISUAL`, `$EDITOR` ou `LEARN_EDITOR`.",
            ),
            DoctorCheck(
                "Codex CLI",
                codex_available,
                True,
                "Disponible."
                if codex_available
                else "Installe ou rends Codex CLI accessible dans PATH.",
            ),
            local_configuration_check(root),
            personal_signing_check(root),
        ]
    )
    if include_remote:
        checks.append(remote_privacy(root))
    return checks


def print_doctor(checks: list[DoctorCheck], *, details: bool) -> None:
    for item in checks:
        if details or not item.ok:
            symbol = "OK" if item.ok else "BLOQUÉ" if item.blocking else "ATTENTION"
            print(f"[{symbol}] {item.name}: {item.detail}")


def state_path(root: Path) -> Path:
    return root / ".learning" / "state.json"


def source_mode_receipt_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / ".proof" / "source-mode.json"


def resume_receipt_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / ".proof" / "resume.json"


def has_training_taint(root: Path, day_id: str) -> bool:
    path = source_mode_receipt_path(root, day_id)
    # La présence suffit : un reçu corrompu ne doit jamais rendre à nouveau
    # créditable une tentative qui a reçu une aide extérieure.
    return path.exists() or path.is_symlink()


def has_reachable_training_taint(
    root: Path,
    day_id: str,
    revision: str = "HEAD",
    *,
    include_worktree: bool = True,
) -> bool:
    if include_worktree and has_training_taint(root, day_id):
        return True
    relative = source_mode_receipt_path(root, day_id).relative_to(root).as_posix()
    history = run(
        ["git", "log", "--full-history", "--format=%H", revision, "--", relative],
        cwd=root,
    )
    # Une histoire illisible ne doit jamais permettre de recréditer une tentative.
    return history.returncode != 0 or bool(history.stdout.strip())


def new_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "active_day": DEFAULT_DAY,
        "next_day": "J002",
        "completed_days": [],
        "consolidation_queue": [],
        "total_days": TOTAL_DAYS,
        "days": {},
        "updated_at": now_iso(),
    }


def _branch_day_hint(root: Path) -> str | None:
    branch = current_branch(root)
    if not branch:
        return None
    match = re.fullmatch(
        r"learn/(j\d{3})(?:(?:-(?:retry|resume)-\d+)|"
        r"(?:-(?:blocked|pathway)-j\d{3}(?:-retry-\d+)?))?",
        branch,
    )
    return match.group(1).upper() if match else None


def _branch_activation_hint(root: Path) -> dict[str, str] | None:
    branch = current_branch(root) or ""
    match = re.fullmatch(
        r"learn/j(?:37[1-9]|38\d|390)-(blocked|pathway)-(j\d{3})"
        r"(?:-retry-\d+)?",
        branch,
    )
    if match is None:
        return None
    kind, trigger = match.groups()
    return {
        "kind": "blocked-day" if kind == "blocked" else "pathway-completion",
        "triggered_by": trigger.upper(),
    }


def _blocked_source_context(root: Path, day_id: str) -> tuple[str, str, str] | None:
    refs = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)%00%(objectname)",
            "refs/heads",
            "refs/remotes/origin",
        ],
        cwd=root,
    )
    if refs.returncode != 0:
        return None
    branch_pattern = re.compile(
        rf"(?:origin/)?(learn/{day_id.lower()}"
        r"(?:-(?:retry|resume)-\d+)?)"
    )
    branches: set[str] = set()
    for line in refs.stdout.splitlines():
        reference, separator, _commit = line.partition("\0")
        match = branch_pattern.fullmatch(reference)
        if not separator or match is None:
            continue
        branches.add(match.group(1))
    candidates: dict[str, tuple[str, str, str, str]] = {}
    for branch in sorted(branches):
        context = _blocked_branch_context(root, day_id, branch)
        if context is None:
            continue
        resolved = run(
            ["git", "rev-parse", "--verify", f"{branch}^{{commit}}"], cwd=root
        )
        if resolved.returncode != 0:
            resolved = run(
                ["git", "rev-parse", "--verify", f"origin/{branch}^{{commit}}"],
                cwd=root,
            )
        commit = resolved.stdout.strip()
        if resolved.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
            continue
        candidates[branch] = (*context, commit)
    newest = [
        candidate
        for candidate in candidates.values()
        if not any(
            candidate[3] != other[3]
            and run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    candidate[3],
                    other[3],
                ],
                cwd=root,
            ).returncode
            == 0
            for other in candidates.values()
        )
    ]
    return newest[0][:3] if len(newest) == 1 else None


def _blocked_branch_context(
    root: Path, day_id: str, branch: str
) -> tuple[str, str, str] | None:
    if (
        re.fullmatch(rf"learn/{day_id.lower()}(?:-(?:retry|resume)-\d+)?", branch)
        is None
    ):
        return None
    relative = f"learning/days/{day_id}"
    contexts: list[tuple[str, str, str]] = []
    commits: set[str] = set()
    checked_out = current_branch(root)
    for reference in (branch, f"origin/{branch}"):
        resolved = run(
            ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root
        )
        if resolved.returncode != 0:
            continue
        if has_reachable_training_taint(
            root,
            day_id,
            reference,
            include_worktree=reference == checked_out,
        ):
            return None
        proof_result = run(
            ["git", "show", f"{reference}:{relative}/.proof/proof.json"], cwd=root
        )
        journal_result = run(
            ["git", "show", f"{reference}:{relative}/learner.md"], cwd=root
        )
        if proof_result.returncode != 0 or journal_result.returncode != 0:
            return None
        try:
            proof = json.loads(proof_result.stdout)
        except json.JSONDecodeError:
            return None
        identity = learner_guide_identity(journal_result.stdout)
        if (
            proof.get("day_id") != day_id
            or proof.get("source_mode") != "guide-only"
            or proof.get("learner_status") != "Bloqué"
            or identity is None
        ):
            return None
        commits.add(resolved.stdout.strip())
        contexts.append((branch, identity[0], identity[1]))
    if not contexts or len(commits) != 1 or len(set(contexts)) != 1:
        return None
    return contexts[0]


def _transition_source_from_record(day_id: str, record: Any) -> str | None:
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        return None
    if record.get("day_id") != day_id:
        return None
    source = record.get("resume_source_branch")
    if source is None:
        attempts = record.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            return None
        last = attempts[-1]
        source = last.get("branch") if isinstance(last, dict) else None
    if (
        not isinstance(source, str)
        or re.fullmatch(
            rf"learn/{day_id.lower()}(?:(?:-(?:retry|resume)-\d+)|"
            r"(?:-(?:blocked|pathway)-j\d{3}(?:-retry-\d+)?))?",
            source,
        )
        is None
    ):
        return None
    return source


def _worktree_pending_branch_context(
    root: Path, day_id: str, branches: set[str]
) -> tuple[tuple[str, str, str], str] | None:
    branch = current_branch(root)
    if (
        branch not in branches
        or re.search(r"-(?:retry|resume)-\d+$", branch or "") is None
    ):
        return None
    relative = f"learning/days/{day_id}/learner.md"
    if run(["git", "show", f"{branch}:{relative}"], cwd=root).returncode == 0:
        return None
    journal = root / relative
    if journal.is_symlink() or not journal.is_file():
        return None
    try:
        identity = learner_guide_identity(journal.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if identity is None:
        return None

    proof_root = day_directory(root, day_id) / ".proof"
    transition_sources: list[str] = []
    for name in ("resume.json", "training-attempts.json"):
        path = proof_root / name
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            return None
        try:
            source = _transition_source_from_record(day_id, read_json(path))
        except LearningError:
            return None
        if source is None:
            return None
        transition_sources.append(source)
    if len(transition_sources) != 1:
        return None
    source = transition_sources[0]
    if source == branch or source not in branches:
        return None

    if int(day_id.removeprefix("J")) > TOTAL_MAIN_DAYS:
        activation_path = proof_root / "activation.json"
        if activation_path.is_symlink() or not activation_path.is_file():
            return None
        try:
            activation_record = read_json(activation_path)
        except LearningError:
            return None
        expected_activation = _branch_activation_hint(root)
        if (
            activation_record.get("schema_version") != 1
            or activation_record.get("day_id") != day_id
            or activation_record.get("activation") != expected_activation
        ):
            return None

    return (branch, identity[0], identity[1]), source


def _branch_transition_source(root: Path, day_id: str, branch: str) -> str | None:
    proof_root = f"learning/days/{day_id}/.proof"
    records: dict[str, dict[str, Any] | None] = {}
    commits: dict[str, str] = {}
    for reference in (branch, f"origin/{branch}"):
        resolved = run(
            ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root
        )
        if resolved.returncode != 0:
            continue
        commits[reference] = resolved.stdout.strip()
        found: list[dict[str, Any]] = []
        for name in ("resume.json", "training-attempts.json"):
            result = run(["git", "show", f"{reference}:{proof_root}/{name}"], cwd=root)
            if result.returncode != 0:
                continue
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                raise LearningError(
                    f"Le reçu de transition de {branch} est illisible."
                ) from None
            if not isinstance(payload, dict):
                raise LearningError(f"Le reçu de transition de {branch} est invalide.")
            found.append(payload)
        if len(found) > 1:
            raise LearningError(
                f"La branche {branch} contient plusieurs reçus de transition."
            )
        records[reference] = found[0] if found else None
    if not records or all(record is None for record in records.values()):
        return None
    local = records.get(branch)
    remote = records.get(f"origin/{branch}")
    if len(records) == 2 and local != remote:
        local_commit = commits[branch]
        remote_commit = commits[f"origin/{branch}"]
        local_ahead = (
            run(
                ["git", "merge-base", "--is-ancestor", remote_commit, local_commit],
                cwd=root,
            ).returncode
            == 0
        )
        if not (local_ahead and local is not None and remote is None):
            raise LearningError(
                f"Les reçus de transition de {branch} et origin/{branch} diffèrent."
            )
    selected = local if branch in records else remote
    source = _transition_source_from_record(day_id, selected)
    if source is None:
        raise LearningError(f"Le reçu de transition de {branch} est invalide.")
    return source


def _pending_branch_context(root: Path, day_id: str) -> tuple[str, str, str] | None:
    refs = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/heads",
            "refs/remotes/origin",
        ],
        cwd=root,
    )
    if refs.returncode != 0:
        return None
    pattern = re.compile(
        rf"(?:origin/)?(learn/{day_id.lower()}"
        r"(?:(?:-(?:retry|resume)-\d+)|"
        r"(?:-(?:blocked|pathway)-j\d{3}(?:-retry-\d+)?))?)"
    )
    branches = {
        match.group(1)
        for reference in refs.stdout.splitlines()
        if (match := pattern.fullmatch(reference)) is not None
    }
    transitions = {
        branch: source
        for branch in branches
        if (source := _branch_transition_source(root, day_id, branch)) is not None
    }
    worktree_context = _worktree_pending_branch_context(root, day_id, branches)
    if worktree_context is not None:
        context, source = worktree_context
        transitions[context[0]] = source
    for start in transitions:
        branch = start
        visited: set[str] = set()
        while branch in transitions:
            if branch in visited:
                raise LearningError(
                    f"La chaîne de reprise de {day_id} contient une boucle."
                )
            visited.add(branch)
            branch = transitions[branch]
    predecessors = set(transitions.values())
    contexts: dict[str, tuple[str, str, str]] = {}
    empty_leaves: set[str] = set()
    for branch in sorted(branches):
        relative = f"learning/days/{day_id}/learner.md"
        results: list[subprocess.CompletedProcess[str]] = []
        reference_commits: dict[str, str] = {}
        for reference in (branch, f"origin/{branch}"):
            resolved = run(
                ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"],
                cwd=root,
            )
            if resolved.returncode != 0:
                continue
            reference_commits[reference] = resolved.stdout.strip()
            results.append(run(["git", "show", f"{reference}:{relative}"], cwd=root))
        local_commit = reference_commits.get(branch)
        remote_commit = reference_commits.get(f"origin/{branch}")
        if (
            local_commit is not None
            and remote_commit is not None
            and local_commit != remote_commit
        ):
            remote_is_ancestor = (
                run(
                    ["git", "merge-base", "--is-ancestor", remote_commit, local_commit],
                    cwd=root,
                ).returncode
                == 0
            )
            local_is_ancestor = (
                run(
                    ["git", "merge-base", "--is-ancestor", local_commit, remote_commit],
                    cwd=root,
                ).returncode
                == 0
            )
            if local_is_ancestor:
                raise LearningError(
                    f"La branche locale {branch} est en retard sur origin/{branch}; "
                    "synchronise-la par fast-forward avant de reprendre."
                )
            if not remote_is_ancestor:
                raise LearningError(
                    f"La branche quotidienne {branch} diverge de origin/{branch}."
                )
        if worktree_context is not None and branch == worktree_context[0][0]:
            contexts[branch] = worktree_context[0]
            continue
        observed = [
            learner_guide_identity(result.stdout) if result.returncode == 0 else None
            for result in results
        ]
        identities = {identity for identity in observed if identity is not None}
        if results and None not in observed and len(identities) == 1:
            version, digest = identities.pop()
            contexts[branch] = (branch, version, digest)
        elif results and branch not in predecessors:
            if all(result.returncode != 0 for result in results):
                empty_leaves.add(branch)
            else:
                raise LearningError(
                    f"La branche quotidienne {branch} diverge ou porte un "
                    "journal invalide."
                )
    leaves = [branch for branch in contexts if branch not in predecessors]
    if contexts and not leaves:
        raise LearningError(
            f"La chaîne de reprise de {day_id} ne possède aucune branche terminale."
        )
    if len(leaves) > 1 or (empty_leaves and (leaves or len(empty_leaves) > 1)):
        raise LearningError(
            f"Plusieurs branches quotidiennes non réconciliées existent pour {day_id}."
        )
    return contexts[leaves[0]] if leaves else None


def _consolidation_branch_activation(
    root: Path, day_id: str, branch: str
) -> dict[str, Any] | None:
    match = re.fullmatch(
        rf"learn/{day_id.lower()}-(blocked|pathway)-(j\d{{3}})(?:-retry-\d+)?",
        branch,
    )
    if match is None:
        return None
    branch_kind, trigger = match.groups()
    relative = f"learning/days/{day_id}/.proof/activation.json"
    records: list[dict[str, Any]] = []
    for reference in (branch, f"origin/{branch}"):
        resolved = run(
            ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root
        )
        if resolved.returncode != 0:
            continue
        result = run(["git", "show", f"{reference}:{relative}"], cwd=root)
        if result.returncode != 0:
            return None
        try:
            record = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(record, dict):
            return None
        records.append(record)
    if (
        not records
        or len(
            {
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in records
            }
        )
        != 1
    ):
        return None
    activation = records[0].get("activation")
    expected_activation = {
        "kind": "blocked-day" if branch_kind == "blocked" else "pathway-completion",
        "triggered_by": trigger.upper(),
    }
    if (
        records[0].get("schema_version") != 1
        or records[0].get("day_id") != day_id
        or activation != expected_activation
    ):
        return None
    return records[0]


def _pending_consolidation_branch(
    root: Path, completed: set[str]
) -> tuple[tuple[str, str, str], dict[str, Any]] | None:
    candidates: list[tuple[tuple[str, str, str], dict[str, Any]]] = []
    for number in range(TOTAL_MAIN_DAYS + 1, TOTAL_DAYS + 1):
        day_id = f"J{number:03d}"
        if day_id in completed:
            continue
        context = _pending_branch_context(root, day_id)
        if context is None:
            continue
        activation = _consolidation_branch_activation(root, day_id, context[0])
        if activation is not None:
            candidates.append((context, activation))
    if len(candidates) > 1:
        raise LearningError("Plusieurs consolidations non réconciliées sont présentes.")
    return candidates[0] if candidates else None


def _apply_blocked_source_context(
    day_state: dict[str, Any], context: tuple[str, str, str]
) -> None:
    branch, version, digest = context
    day_state["branch"] = branch
    day_state["guide_version"] = version
    day_state["guide_sha256"] = digest
    retry_match = re.search(r"-retry-(\d+)$", branch)
    resume_match = re.search(r"-resume-(\d+)$", branch)
    if retry_match:
        day_state["retry_count"] = int(retry_match.group(1))
    if resume_match:
        day_state["resume_count"] = int(resume_match.group(1))


def _merged_baseline_for_day(root: Path, day_id: str) -> str | None:
    history = run(["git", "log", "--all", "--format=%H%x00%s"], cwd=root)
    if history.returncode != 0:
        return None
    subject = f"{day_id}: résultat final"
    finals = {
        commit
        for line in history.stdout.splitlines()
        for commit, separator, message in (line.partition("\0"),)
        if separator and message == subject
    }
    if not finals:
        return None
    first_parent = run(
        ["git", "rev-list", "--first-parent", "--parents", "origin/master"],
        cwd=root,
    )
    if first_parent.returncode != 0:
        return None
    day_path = f"learning/days/{day_id}"
    for line in first_parent.stdout.splitlines():
        values = line.split()
        if len(values) != 3:
            continue
        merge, base_parent, day_parent = values
        if day_parent not in finals:
            continue
        changed = run(
            ["git", "diff", "--quiet", base_parent, day_parent, "--", day_path],
            cwd=root,
        )
        day_tree = run(
            ["git", "rev-parse", "--verify", f"{day_parent}:{day_path}"], cwd=root
        )
        merge_tree = run(
            ["git", "rev-parse", "--verify", f"{merge}:{day_path}"], cwd=root
        )
        proof_result = run(
            [
                "git",
                "show",
                f"{day_parent}:{day_path}/.proof/proof.json",
            ],
            cwd=root,
        )
        try:
            proof = (
                json.loads(proof_result.stdout) if proof_result.returncode == 0 else {}
            )
        except json.JSONDecodeError:
            proof = {}
        if (
            changed.returncode == 1
            and day_tree.returncode == 0
            and merge_tree.returncode == 0
            and day_tree.stdout.strip() == merge_tree.stdout.strip()
            and proof.get("day_id") == day_id
            and proof.get("source_mode") == "guide-only"
            and proof.get("learner_status") == "Validé"
            and proof.get("conformity") == "conforme"
        ):
            return merge
    return None


def _phase_tag_is_valid(
    root: Path,
    tag: str,
    expected: str,
    *,
    require_current_key: bool = True,
) -> bool:
    resolved = run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"], cwd=root
    )
    kind = run(["git", "cat-file", "-t", f"refs/tags/{tag}"], cwd=root)
    verified = run(["git", "verify-tag", tag], cwd=root)
    trusted_fingerprints = _allowed_signing_fingerprints(root)
    current_fingerprint = _ssh_signing_fingerprint(root, require_agent=False)
    verified_signers = re.findall(
        r'Good "git" signature for ([A-Za-z0-9@._+-]+) with '
        r"[A-Za-z0-9@._+-]+ key (SHA256:[A-Za-z0-9+/]+)(?:\s|$)",
        verified.stdout + verified.stderr,
    )
    expected_fingerprints = (
        {current_fingerprint} if require_current_key else trusted_fingerprints
    )
    return (
        resolved.returncode == 0
        and resolved.stdout.strip() == expected
        and kind.returncode == 0
        and kind.stdout.strip() == "tag"
        and verified.returncode == 0
        and None not in expected_fingerprints
        and len(verified_signers) == 1
        and verified_signers[0][0] == PERSONAL_SIGNING_PRINCIPAL
        and verified_signers[0][1] in expected_fingerprints
    )


def _remote_phase_tag_identities(
    root: Path, tags: set[str]
) -> dict[str, tuple[str, str]]:
    if not tags:
        return {}
    result = run(
        [
            "git",
            "ls-remote",
            "--tags",
            "origin",
            "refs/tags/phase-*",
        ],
        cwd=root,
    )
    if result.returncode != 0:
        raise LearningError(
            "Impossible de vérifier les tags de phase sur le dépôt distant origin."
        )
    references: dict[str, dict[str, str]] = {tag: {} for tag in tags}
    for line in result.stdout.splitlines():
        commit, separator, reference = line.partition("\t")
        match = re.fullmatch(r"refs/tags/(phase-(?:0[0-9]|1[0-3]))(\^\{\})?", reference)
        if match is None or match.group(1) not in tags:
            continue
        tag = match.group(1)
        kind = "peeled" if match.group(2) else "direct"
        if (
            not separator
            or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None
            or kind in references[tag]
        ):
            raise LearningError(f"Réponse distante ambiguë pour le tag {tag}.")
        references[tag][kind] = commit
    identities: dict[str, tuple[str, str]] = {}
    for tag, values in references.items():
        if not values:
            continue
        if set(values) != {"direct", "peeled"}:
            raise LearningError(
                f"Le tag distant {tag} doit être un tag annoté et signé."
            )
        identities[tag] = values["direct"], values["peeled"]
    return identities


def _remote_phase_tag_identity(root: Path, tag: str) -> tuple[str, str] | None:
    return _remote_phase_tag_identities(root, {tag}).get(tag)


def recover_pending_phase_tag(
    root: Path, state: dict[str, Any], completed: set[str]
) -> None:
    relevant = [
        (f"phase-{phase:02d}", f"J{boundary:03d}")
        for phase, boundary in enumerate(PHASE_BOUNDARIES)
        if f"J{boundary:03d}" in completed
    ]
    remote_identities: dict[str, tuple[str, str]] | None = None
    for tag, boundary_day in relevant:
        expected_merge = _merged_baseline_for_day(root, boundary_day)
        if not expected_merge:
            continue
        if not _phase_tag_is_valid(
            root, tag, expected_merge, require_current_key=False
        ):
            state["pending_phase_tag"] = tag
            state["pending_phase_commit"] = expected_merge
            return
        local_object = run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag}"], cwd=root
        )
        if remote_identities is None:
            remote_identities = _remote_phase_tag_identities(
                root, {value[0] for value in relevant}
            )
        remote_identity = remote_identities.get(tag)
        if local_object.returncode != 0 or remote_identity != (
            local_object.stdout.strip(),
            expected_merge,
        ):
            state["pending_phase_tag"] = tag
            state["pending_phase_commit"] = expected_merge
            return


def reconstruct_state(root: Path) -> dict[str, Any]:
    """Reconstruit la progression portable depuis les preuves du checkout.

    L'état reste local pour ne jamais salir une PR après sa fusion. Les preuves
    versionnées sont donc l'autorité de reprise après un clone ou la perte du
    cache local. Une branche quotidienne active n'est jamais considérée comme
    terminée uniquement parce que son fichier local annonce ``conforme``.
    """

    state = new_state()
    active_hint = _branch_day_hint(root)
    if active_hint is not None and _merged_baseline_for_day(root, active_hint):
        raise LearningError(
            "La branche quotidienne courante est déjà fusionnée ; "
            "reconstruis la progression depuis origin/master."
        )
    days_root = root / "learning" / "days"
    pending_context: tuple[str, str, str] | None = None
    if not days_root.is_dir() and active_hint is None:
        pending_context = _pending_branch_context(root, DEFAULT_DAY)
        if pending_context is None:
            return state

    records: dict[str, dict[str, Any]] = {}
    completed: set[str] = set()
    for proof_path in sorted(days_root.glob("J[0-9][0-9][0-9]/.proof/proof.json")):
        day_id = proof_path.parent.parent.name
        try:
            proof = read_json(proof_path)
        except LearningError:
            continue
        if proof.get("day_id") != day_id:
            continue
        records[day_id] = proof
        commits = proof.get("commits", [])
        checkpoint_map: dict[str, str] = {}
        if isinstance(commits, list):
            for name, value in zip(("prediction", "attempt"), commits, strict=False):
                if isinstance(value, str):
                    checkpoint_map[name] = value
        raw_guide = proof.get("guide", {})
        proof_guide = raw_guide if isinstance(raw_guide, dict) else {}
        day_state: dict[str, Any] = {
            "source_mode": proof.get("source_mode", "guide-only"),
            "guide_version": proof_guide.get("version"),
            "guide_sha256": proof_guide.get("sha256"),
            "activation": proof.get("activation"),
            "checkpoint_commits": checkpoint_map,
            "commit_checkpoints": list(checkpoint_map),
        }
        activation_record_path = proof_path.parent / "activation.json"
        if activation_record_path.exists():
            try:
                activation_record = read_json(activation_record_path)
            except LearningError:
                activation_record = {}
            resume_source = activation_record.get("resume_source_branch")
            if (
                activation_record.get("schema_version") == 1
                and activation_record.get("day_id") == day_id
                and activation_record.get("activation") == proof.get("activation")
                and isinstance(resume_source, str)
                and re.fullmatch(
                    r"learn/j\d{3}(?:-(?:retry|resume)-\d+)?", resume_source
                )
            ):
                day_state["resume_source_branch"] = resume_source
        try:
            receipt = raw_evidence_receipt(root, day_id)
        except LearningError:
            receipt = None
        raw = proof.get("raw_evidence")
        if (
            receipt is not None
            and isinstance(raw, dict)
            and raw == {"id": receipt["id"], "sha256": receipt["sha256"]}
        ):
            day_state["raw_evidence"] = dict(receipt)
        state["days"][day_id] = day_state
        try:
            valid_day = not validate_day(root, day_id)
        except LearningError:
            valid_day = False
        if (
            proof.get("learner_status") == "Validé"
            and proof.get("conformity") == "conforme"
            and valid_day
            and _merged_baseline_for_day(root, day_id) is not None
        ):
            completed.add(day_id)

    for journal_path in sorted(days_root.glob("J[0-9][0-9][0-9]/learner.md")):
        day_id = journal_path.parent.name
        try:
            identity = learner_guide_identity(journal_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            identity = None
        if identity is None:
            continue
        version, digest = identity
        day_state = state["days"].setdefault(day_id, {})
        day_state.setdefault("guide_version", version)
        day_state.setdefault("guide_sha256", digest)

    for taint_path in sorted(
        days_root.glob("J[0-9][0-9][0-9]/.proof/source-mode.json")
    ):
        day_id = taint_path.parent.parent.name
        day_state = state["days"].setdefault(day_id, {})
        day_state["source_mode"] = "training-only"
        day_state["ignored_artifact_baseline"] = {}

    state["completed_days"] = sorted(completed)
    state["consolidation_queue"] = []

    recover_pending_phase_tag(root, state, completed)

    active_branch_pending = active_hint is not None and active_hint not in completed
    if active_branch_pending:
        active_day: str | None = active_hint
        branch = current_branch(root) or ""
        active_state = state["days"].setdefault(active_hint, {})
        authoritative_context = _pending_branch_context(root, active_hint)
        if authoritative_context is not None and authoritative_context[0] != branch:
            raise LearningError(
                "Le checkout courant est une ancienne génération de la journée ; "
                f"reprends sur la branche autoritaire {authoritative_context[0]}."
            )
        if authoritative_context is not None:
            _apply_blocked_source_context(active_state, authoritative_context)
        if _branch_day_hint(root) == active_hint:
            active_state["branch"] = branch
            retry_match = re.search(r"-retry-(\d+)$", branch)
            resume_match = re.search(r"-resume-(\d+)$", branch)
            if retry_match:
                active_state["retry_count"] = int(retry_match.group(1))
            if resume_match:
                active_state["resume_count"] = int(resume_match.group(1))
        active_proof = records.get(active_hint, {})
        activation = active_proof.get("activation")
        if not isinstance(activation, dict) and active_hint > "J370":
            activation_path = (
                day_directory(root, active_hint) / ".proof" / "activation.json"
            )
            if activation_path.exists():
                try:
                    activation_record = read_json(activation_path)
                    if (
                        activation_record.get("schema_version") == 1
                        and activation_record.get("day_id") == active_hint
                        and isinstance(activation_record.get("activation"), dict)
                    ):
                        activation = activation_record["activation"]
                        resume_source = activation_record.get("resume_source_branch")
                        if isinstance(resume_source, str):
                            state["days"].setdefault(active_hint, {})[
                                "resume_source_branch"
                            ] = resume_source
                except LearningError:
                    activation = None
            activation = activation or _branch_activation_hint(root)
            if isinstance(activation, dict):
                state["days"].setdefault(active_hint, {})["activation"] = activation
        if isinstance(activation, dict) and active_hint > "J370":
            state["consolidation_queue"] = [active_hint]
            if activation.get("kind") == "blocked-day":
                trigger = activation.get("triggered_by")
                state["suspended_day"] = trigger
                consolidation_state = state["days"].setdefault(active_hint, {})
                if not isinstance(consolidation_state.get("resume_source_branch"), str):
                    context = (
                        _blocked_source_context(root, trigger)
                        if isinstance(trigger, str)
                        else None
                    )
                    if context is None:
                        raise LearningError(
                            "La branche source et le guide de la consolidation "
                            "bloquée sont introuvables."
                        )
                    source_branch, version, digest = context
                    consolidation_state["resume_source_branch"] = source_branch
                    consolidation_state.setdefault("guide_version", version)
                    consolidation_state.setdefault("guide_sha256", digest)
        if active_hint <= "J370" and "-resume-" in branch:
            completed_consolidation = next(
                (
                    day_id
                    for day_id, proof in sorted(records.items(), reverse=True)
                    if day_id in completed
                    and isinstance(proof.get("activation"), dict)
                    and proof["activation"].get("kind") == "blocked-day"
                    and proof["activation"].get("triggered_by") == active_hint
                ),
                None,
            )
            if completed_consolidation:
                resumed = state["days"].setdefault(active_hint, {})
                consolidation_state = state["days"].get(completed_consolidation, {})
                source_branch = consolidation_state.get("resume_source_branch")
                context = (
                    _blocked_branch_context(root, active_hint, source_branch)
                    if isinstance(source_branch, str)
                    else _blocked_source_context(root, active_hint)
                )
                if context is None:
                    raise LearningError(
                        "La branche du journal bloqué à reprendre est introuvable."
                    )
                if (
                    consolidation_state.get("guide_version") != context[1]
                    or consolidation_state.get("guide_sha256") != context[2]
                ):
                    raise LearningError(
                        "L'épinglage du guide de consolidation diffère du "
                        "journal bloqué."
                    )
                _apply_blocked_source_context(resumed, context)
                resumed["resume_from_consolidation"] = completed_consolidation
                resumed["resume_source_branch"] = source_branch
                resumed["branch"] = branch
                current_resume = re.search(r"-resume-(\d+)$", branch)
                if current_resume:
                    resumed["resume_count"] = int(current_resume.group(1))
                expected_resume_receipt = {
                    "schema_version": 1,
                    "day_id": active_hint,
                    "resume_from_consolidation": completed_consolidation,
                    "resume_source_branch": source_branch,
                    "guide_version": context[1],
                    "guide_sha256": context[2],
                }
                receipt_path = resume_receipt_path(root, active_hint)
                try:
                    resumed["resume_prepared"] = (
                        receipt_path.exists()
                        and read_json(receipt_path) == expected_resume_receipt
                    )
                except LearningError:
                    resumed["resume_prepared"] = False
    else:
        pending_branch_consolidation = _pending_consolidation_branch(root, completed)
        outstanding_block = next(
            (
                (day_id, str(proof["activation"].get("triggered_by")))
                for day_id, proof in sorted(records.items(), reverse=True)
                if day_id in completed
                and day_id > "J370"
                and isinstance(proof.get("activation"), dict)
                and proof["activation"].get("kind") == "blocked-day"
                and str(proof["activation"].get("triggered_by")) not in completed
            ),
            None,
        )
        pending_consolidation = next(
            (
                day_id
                for day_id, proof in sorted(records.items())
                if day_id > "J370"
                and day_id not in completed
                and isinstance(proof.get("activation"), dict)
                and proof["activation"].get("kind")
                in {"blocked-day", "pathway-completion"}
            ),
            None,
        )
        if pending_branch_consolidation:
            context, activation_record = pending_branch_consolidation
            active_day = str(activation_record["day_id"])
            activation = activation_record["activation"]
            consolidation_state = state["days"].setdefault(active_day, {})
            _apply_blocked_source_context(consolidation_state, context)
            consolidation_state["activation"] = activation
            state["consolidation_queue"] = [active_day]
            if activation.get("kind") == "blocked-day":
                trigger = activation.get("triggered_by")
                source_branch = activation_record.get("resume_source_branch")
                source_context = (
                    _blocked_branch_context(root, trigger, source_branch)
                    if isinstance(trigger, str) and isinstance(source_branch, str)
                    else None
                )
                if source_context != (
                    source_branch,
                    context[1],
                    context[2],
                ):
                    raise LearningError(
                        "La source versionnée de la consolidation est incohérente."
                    )
                state["suspended_day"] = trigger
                consolidation_state["resume_source_branch"] = source_branch
            for baseline in ("origin/master", "master"):
                branch_base = run(["git", "merge-base", context[0], baseline], cwd=root)
                if branch_base.returncode == 0 and branch_base.stdout.strip():
                    consolidation_state["start_commit"] = branch_base.stdout.strip()
                    consolidation_state["base_commit"] = branch_base.stdout.strip()
                    break
        elif pending_consolidation:
            active_day = pending_consolidation
            state["consolidation_queue"] = [pending_consolidation]
            activation = records[pending_consolidation]["activation"]
            if activation.get("kind") == "blocked-day":
                state["suspended_day"] = activation.get("triggered_by")
        elif outstanding_block:
            consolidation, active_day = outstanding_block
            consolidation_state = state["days"].get(consolidation, {})
            source_branch = consolidation_state.get("resume_source_branch")
            context = (
                _blocked_branch_context(root, active_day, source_branch)
                if isinstance(source_branch, str)
                else _blocked_source_context(root, active_day)
            )
            if context is None:
                raise LearningError(
                    "La branche du journal bloqué à reprendre est introuvable."
                )
            if (
                consolidation_state.get("guide_version") != context[1]
                or consolidation_state.get("guide_sha256") != context[2]
            ):
                raise LearningError(
                    "L'épinglage du guide de consolidation diffère du journal bloqué."
                )
            _apply_blocked_source_context(
                state["days"].setdefault(active_day, {}), context
            )
            consolidation_merge = _merged_baseline_for_day(root, consolidation)
            remote_master = verified_remote_master_head(root)
            if (
                consolidation_merge is None
                or run(
                    [
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        consolidation_merge,
                        remote_master,
                    ],
                    cwd=root,
                ).returncode
            ):
                raise LearningError(
                    "La fusion de consolidation n'est pas une baseline "
                    "vérifiable de origin/master."
                )
            plan_resumed_attempt(
                root,
                state,
                active_day,
                consolidation,
                start_commit=remote_master,
            )
        else:
            active_day = next(
                (
                    f"J{number:03d}"
                    for number in range(1, TOTAL_MAIN_DAYS + 1)
                    if f"J{number:03d}" not in completed
                ),
                None,
            )
            if active_day is None:
                remaining = [
                    f"J{number:03d}"
                    for number in range(TOTAL_MAIN_DAYS + 1, TOTAL_DAYS + 1)
                    if f"J{number:03d}" not in completed
                ]
                state["consolidation_queue"] = remaining
                for consolidation in remaining:
                    consolidation_state = state["days"].setdefault(consolidation, {})
                    consolidation_state["activation"] = {
                        "kind": "pathway-completion",
                        "triggered_by": "J370",
                    }
                    consolidation_state["branch"] = (
                        f"learn/{consolidation.lower()}-pathway-j370"
                    )
                active_day = remaining[0] if remaining else None

    if (
        not active_branch_pending
        and active_day is not None
        and int(active_day.removeprefix("J")) <= TOTAL_MAIN_DAYS
    ):
        next_state = state["days"].setdefault(active_day, {})
        context = pending_context or _pending_branch_context(root, active_day)
        if context is not None:
            _apply_blocked_source_context(next_state, context)
        remote = run(
            ["git", "rev-parse", "--verify", "origin/master^{commit}"], cwd=root
        )
        if (
            remote.returncode == 0
            and re.fullmatch(r"[0-9a-f]{40,64}", remote.stdout.strip()) is not None
        ):
            start_commit = remote.stdout.strip()
            branch = next_state.get("branch")
            if context is not None and isinstance(branch, str):
                branch_base = run(
                    ["git", "merge-base", branch, "origin/master"], cwd=root
                )
                if branch_base.returncode == 0 and branch_base.stdout.strip():
                    start_commit = branch_base.stdout.strip()
            next_state.setdefault("start_commit", start_commit)
            next_state.setdefault("base_commit", start_commit)

    state["active_day"] = active_day
    state["next_day"] = (
        _next_main_day(active_day)
        if active_day and int(active_day.removeprefix("J")) <= TOTAL_MAIN_DAYS
        else None
    )
    state["updated_at"] = now_iso()
    return state


def _validate_cached_state_authority(root: Path, state: dict[str, Any]) -> None:
    active_day = state.get("active_day")
    if not isinstance(active_day, str) or re.fullmatch(r"J\d{3}", active_day) is None:
        return
    raw_days = state.get("days")
    day_state = raw_days.get(active_day) if isinstance(raw_days, dict) else None
    cached = day_state if isinstance(day_state, dict) else {}
    cached_branch = cached.get("branch")
    current = current_branch(root)
    current_hint = _branch_day_hint(root)
    if current_hint is not None:
        if current_hint != active_day:
            raise LearningError(
                f"Le checkout {current or '?'} ne correspond pas à la journée "
                f"active {active_day}; retourne sur master ou sur sa branche active."
            )
        if isinstance(cached_branch, str) and current != cached_branch:
            raise LearningError(
                "Le checkout quotidien diffère de la branche enregistrée dans "
                "le cache local."
            )

    authoritative = _pending_branch_context(root, active_day)
    if authoritative is None:
        return
    branch, version, digest = authoritative
    cache_is_hydratable = cached_branch is None and current == branch
    if cached_branch != branch and not cache_is_hydratable:
        raise LearningError(
            "Le cache local désigne une ancienne génération de la journée ; "
            f"supprime .learning/state.json puis reprends sur {branch}."
        )
    if current_hint == active_day and current != branch:
        raise LearningError(
            f"Le checkout courant est une ancienne génération ; reprends sur {branch}."
        )
    if cached.get("guide_version") not in (None, version) or cached.get(
        "guide_sha256"
    ) not in (None, digest):
        raise LearningError(
            "Le pin du guide dans le cache local diffère de la branche autoritaire."
        )
    if int(active_day.removeprefix("J")) > TOTAL_MAIN_DAYS:
        activation_record = _consolidation_branch_activation(root, active_day, branch)
        if activation_record is None and current == branch:
            activation_path = day_directory(root, active_day) / ".proof/activation.json"
            try:
                candidate = read_json(activation_path)
            except LearningError:
                candidate = None
            expected_activation = _branch_activation_hint(root)
            if (
                isinstance(candidate, dict)
                and candidate.get("schema_version") == 1
                and candidate.get("day_id") == active_day
                and candidate.get("activation") == expected_activation
            ):
                activation_record = candidate
        if activation_record is None:
            raise LearningError(
                "Le reçu d'activation de la consolidation autoritaire est invalide."
            )
        if cached.get("activation") != activation_record.get(
            "activation"
        ) or cached.get("resume_source_branch") != activation_record.get(
            "resume_source_branch"
        ):
            raise LearningError(
                "Le cache local diffère de l'activation ou de la branche source "
                "versionnée de la consolidation."
            )


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        return reconstruct_state(root)
    state = read_json(path)
    _validate_cached_state_authority(root, state)
    return state


def save_state(root: Path, state: dict[str, Any]) -> None:
    path = state_path(root)
    existing = read_json(path) if path.exists() else None
    comparable = {key: value for key, value in state.items() if key != "updated_at"}
    existing_comparable = (
        {key: value for key, value in existing.items() if key != "updated_at"}
        if existing
        else None
    )
    if existing and comparable == existing_comparable:
        state["updated_at"] = existing["updated_at"]
        return
    state["updated_at"] = now_iso()
    atomic_json(path, state)


def phase_for_day(day_id: str) -> int | None:
    number = int(day_id.removeprefix("J"))
    for phase, boundary in enumerate(PHASE_BOUNDARIES):
        if number <= boundary:
            return phase
    return None


def current_branch(root: Path) -> str | None:
    result = run(["git", "branch", "--show-current"], cwd=root)
    branch = result.stdout.strip()
    return branch if result.returncode == 0 and branch else None


def git_worktree_clean(root: Path) -> bool:
    result = run(["git", "status", "--porcelain"], cwd=root)
    return result.returncode == 0 and not result.stdout.strip()


def git_dirty_paths(root: Path) -> list[str]:
    result = run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
    )
    if result.returncode != 0:
        raise LearningError("Impossible de lire l'état Git du dépôt.")
    paths: list[str] = []
    entries = result.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise LearningError("Sortie Git porcelain illisible.")
        status = entry[:2]
        paths.append(entry[3:])
        if any(marker in {"R", "C"} for marker in status) and index < len(entries):
            original = entries[index]
            index += 1
            if original:
                paths.append(original)
    return paths


def ignored_learning_artifacts(root: Path) -> list[str]:
    """Liste les artefacts ignorés non ambiants susceptibles de venir du lab."""

    result = run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
        cwd=root,
    )
    if result.returncode != 0:
        raise LearningError("Impossible d'inspecter les artefacts Git ignorés.")
    artifacts: list[str] = []
    for value in result.stdout.split("\0"):
        if not value:
            continue
        path = Path(value)
        if (
            not path.parts
            or path.parts[0] in IGNORED_RUNTIME_ROOTS
            or path.parts[0] in IGNORED_SENSITIVE_ROOTS
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
            or path.name.lstrip(".") == "env"
            or path.name.lstrip(".").startswith("env.")
        ):
            continue
        artifacts.append(value)
    return sorted(set(artifacts))


def ignored_artifact_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for value in ignored_learning_artifacts(root):
        path = ensure_inside(root, root / value)
        try:
            if path.is_symlink():
                fingerprint = sha256_text("symlink:" + os.readlink(path))
            elif path.is_file():
                fingerprint = sha256_file(path)
            else:
                raise LearningError(
                    f"Artefact ignoré non régulier impossible à borner : {value}"
                )
        except OSError as exc:
            raise LearningError(f"Artefact ignoré illisible : {value}") from exc
        snapshot[value] = fingerprint
    return snapshot


def confirm(message: str) -> bool:
    if not sys.stdin.isatty():
        return False
    return input(f"{message} [o/N] : ").strip().lower() in {"o", "oui"}


def _gh_json(arguments: list[str], root: Path) -> Any:
    result = run(["gh", *arguments], cwd=root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise LearningError(detail[0] if detail else "Échec de GitHub CLI.")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LearningError("Réponse GitHub illisible.") from exc


def switch_day_branch(
    root: Path, branch: str, *, start_commit: str | None = None
) -> None:
    local = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=root)
    remote_ref = f"refs/remotes/origin/{branch}"
    remote = run(["git", "show-ref", "--verify", remote_ref], cwd=root)
    if start_commit:
        commit = run(["git", "cat-file", "-e", f"{start_commit}^{{commit}}"], cwd=root)
        if commit.returncode != 0:
            raise LearningError(
                "La baseline Git de la journée est absente du dépôt local."
            )
        for reference, exists in ((branch, local), (f"origin/{branch}", remote)):
            if (
                exists.returncode == 0
                and run(
                    ["git", "merge-base", "--is-ancestor", start_commit, reference],
                    cwd=root,
                ).returncode
                != 0
            ):
                raise LearningError(
                    f"La branche existante {branch} ne repose pas sur "
                    "la baseline prévue."
                )
    if current_branch(root) == branch:
        return
    if not git_worktree_clean(root):
        raise LearningError(
            "Le dépôt contient des changements étrangers à la journée ; "
            "le cockpit refuse de changer de branche."
        )
    if local.returncode == 0:
        command = ["git", "switch", branch]
    else:
        if remote.returncode == 0:
            command = ["git", "switch", "--track", "-c", branch, f"origin/{branch}"]
        else:
            command = ["git", "switch", "-c", branch]
            if start_commit:
                command.append(start_commit)
    result = run(command, cwd=root)
    if result.returncode != 0:
        raise LearningError((result.stderr or result.stdout).strip())


def ensure_github_tracking(
    root: Path,
    state: dict[str, Any],
    day: DayCard,
    *,
    interactive: bool,
) -> None:
    """Crée le suivi paresseux sans commit, push ou contenu apprenant."""

    day_state = state["days"].setdefault(day.day_id, {})
    branch = str(day_state.get("branch") or f"learn/{day.day_id.lower()}")
    issue_url = day_state.get("issue_url")
    try:
        if not issue_url:
            issues = _gh_json(
                [
                    "issue",
                    "list",
                    "--state",
                    "all",
                    "--search",
                    f'"[{day.day_id}]" in:title',
                    "--limit",
                    "20",
                    "--json",
                    "number,title,url",
                ],
                root,
            )
            exact = next(
                (
                    item
                    for item in issues
                    if str(item.get("title", "")).startswith(f"[{day.day_id}]")
                ),
                None,
            )
            if exact:
                day_state["issue_url"] = exact["url"]
                day_state["issue_number"] = exact["number"]
            elif interactive and confirm(
                "Créer le suivi privé de cette journée sur GitHub ?"
            ):
                result = run(
                    [
                        "gh",
                        "issue",
                        "create",
                        "--title",
                        f"[{day.day_id}] {day.title}",
                        "--body",
                        (
                            f"Référence : {day.reference}\n\n"
                            f"Objectif : {day.objective}\n\n"
                            "Le contenu apprenant reste dans learner.md."
                        ),
                    ],
                    cwd=root,
                )
                if result.returncode != 0:
                    raise LearningError((result.stderr or result.stdout).strip())
                issue_url = result.stdout.strip().splitlines()[-1]
                issue_match = re.search(r"/issues/([1-9][0-9]*)/?$", issue_url)
                if issue_match is None:
                    raise LearningError(
                        "GitHub n'a pas renvoyé un numéro d'issue exploitable."
                    )
                day_state["issue_url"] = issue_url
                day_state["issue_number"] = int(issue_match.group(1))
            else:
                raise LearningError("Le suivi GitHub n'a pas été autorisé.")

        local_branch = current_branch(root)
        if local_branch != branch:
            switch_day_branch(
                root,
                branch,
                start_commit=(
                    str(day_state["start_commit"])
                    if day_state.get("start_commit")
                    else None
                ),
            )
        day_state["branch"] = branch
        day_state["github_mode"] = "managed"
    except LearningError as exc:
        day_state["github_mode"] = "manual-fallback"
        day_state["github_error"] = str(exc)
        if current_branch(root) != branch and git_worktree_clean(root):
            try:
                switch_day_branch(
                    root,
                    branch,
                    start_commit=(
                        str(day_state["start_commit"])
                        if day_state.get("start_commit")
                        else None
                    ),
                )
                day_state["branch"] = branch
            except LearningError:
                pass
        print(
            "Suivi GitHub en mode manuel borné. La journée peut être préparée, "
            "mais elle ne pourra pas être soumise avant réconciliation."
        )
    save_state(root, state)


def remote_branch_exists(root: Path, branch: str) -> bool:
    result = run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=root
    )
    return result.returncode == 0


def ensure_draft_pr(
    root: Path,
    state: dict[str, Any],
    day: DayCard,
    *,
    interactive: bool,
) -> None:
    day_state = state["days"].get(day.day_id, {})
    branch = day_state.get("branch")
    if not branch or day_state.get("pr_url") or not remote_branch_exists(root, branch):
        return
    try:
        existing = _gh_json(
            [
                "pr",
                "list",
                "--state",
                "all",
                "--head",
                str(branch),
                "--json",
                "url",
                "--limit",
                "1",
            ],
            root,
        )
        if existing:
            day_state["pr_url"] = existing[0]["url"]
        elif interactive and confirm("Créer la demande de preuve en brouillon ?"):
            issue_number = day_state.get("issue_number")
            body = "Preuve quotidienne générée par le cockpit."
            if issue_number:
                body += f"\n\nCloses #{issue_number}"
            result = run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--draft",
                    "--base",
                    "master",
                    "--head",
                    str(branch),
                    "--title",
                    f"[{day.day_id}] {day.title}",
                    "--body",
                    body,
                ],
                cwd=root,
            )
            if result.returncode != 0:
                raise LearningError((result.stderr or result.stdout).strip())
            day_state["pr_url"] = result.stdout.strip()
        save_state(root, state)
    except LearningError as exc:
        day_state["github_mode"] = "manual-fallback"
        day_state["github_error"] = str(exc)
        save_state(root, state)


def refresh_ci(
    root: Path, state: dict[str, Any], day_id: str, *, persist: bool = True
) -> str:
    day_state = state["days"].get(day_id, {})
    pr_url = day_state.get("pr_url")
    if not pr_url:
        return "pending"
    result = run(
        ["gh", "pr", "checks", str(pr_url), "--json", "name,state,bucket,link"],
        cwd=root,
    )
    if result.returncode not in {0, 1, 8}:
        return "pending"
    try:
        checks = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return "pending"
    if not isinstance(checks, list) or not all(
        isinstance(item, dict) for item in checks
    ):
        return "pending"
    buckets = {str(item.get("bucket", "")).lower() for item in checks}
    named_checks = {
        str(item.get("name")): str(item.get("bucket", "")).lower()
        for item in checks
        if isinstance(item.get("name"), str)
    }
    duplicate_names = len(named_checks) != len(checks)
    if buckets & {"fail", "cancel"}:
        conclusion = "non_conforme"
    elif (
        not duplicate_names
        and REQUIRED_CI_CHECK_NAMES <= set(named_checks)
        and all(named_checks[name] == "pass" for name in REQUIRED_CI_CHECK_NAMES)
    ):
        conclusion = "conforme"
    else:
        conclusion = "pending"
    if conclusion == "pending":
        return conclusion
    if not persist:
        return conclusion
    payload = {
        "schema_version": 1,
        "conclusion": conclusion,
        "checks": [
            {key: item.get(key) for key in ("name", "state", "bucket")}
            for item in checks
        ],
        "checked_at": now_iso(),
    }
    target = day_directory(root, day_id) / ".proof" / "ci.json"
    if target.exists():
        existing = read_json(target)
        comparable_existing = {
            key: value for key, value in existing.items() if key != "checked_at"
        }
        comparable_payload = {
            key: value for key, value in payload.items() if key != "checked_at"
        }
        if comparable_existing == comparable_payload:
            return conclusion
    atomic_json(target, payload)
    return conclusion


def day_directory(root: Path, day_id: str) -> Path:
    if not re.fullmatch(r"J\d{3}", day_id):
        raise LearningError(f"Identifiant de journée invalide : {day_id}")
    return ensure_inside(root, root / "learning" / "days" / day_id)


def learner_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / "learner.md"


def assert_day_activation(
    manifest: dict[str, Any], state: dict[str, Any], day_id: str
) -> None:
    phase = phase_for_day(day_id)
    audited = {int(value) for value in manifest["audited_phases"]}
    if phase is not None and phase not in audited:
        raise LearningError(
            f"La phase {phase} n'est pas encore auditée et activée dans le guide."
        )
    if phase is None and day_id not in state.get("consolidation_queue", []):
        raise LearningError(
            f"La consolidation {day_id} doit être activée par un blocage ou la clôture."
        )


def append_capture(root: Path, day_id: str, event: str, value: str) -> None:
    target = day_directory(root, day_id) / ".proof" / "captures.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "timestamp": now_iso(),
        "event": event,
        "sha256": sha256_text(value),
    }
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def git_commits(root: Path, base: str | None) -> list[str]:
    if not base:
        return []
    result = run(["git", "log", "--format=%H", f"{base}..HEAD"], cwd=root)
    return result.stdout.splitlines() if result.returncode == 0 else []


def checkpoint_commits(day_state: dict[str, Any]) -> list[str]:
    recorded = day_state.get("checkpoint_commits", {})
    if not isinstance(recorded, dict):
        return []
    return [
        str(recorded[name])
        for name in ("prediction", "attempt")
        if isinstance(recorded.get(name), str)
    ]


def section_digests(markdown: str, titles: tuple[str, ...]) -> dict[str, str]:
    return {title: sha256_text(section(markdown, title)) for title in titles}


def review_state(
    root: Path,
    day_id: str,
    manifest: dict[str, Any],
    markdown: str,
) -> tuple[str, dict[str, Any]]:
    path = day_directory(root, day_id) / ".proof" / "review.json"
    if not path.exists():
        return "pending", {}
    payload = read_json(path)
    if payload.get("guide_sha256") != manifest["sha256"]:
        return "pending", payload
    if payload.get("section_digests") != section_digests(markdown, REVIEW_SECTIONS):
        return "pending", payload
    return str(payload.get("status", "pending")), payload


def ci_state(root: Path, day_id: str) -> str:
    path = day_directory(root, day_id) / ".proof" / "ci.json"
    if path.exists():
        return str(read_json(path).get("conclusion", "pending"))
    return "pending"


def update_proof(
    root: Path,
    manifest: dict[str, Any],
    state: dict[str, Any],
    day: DayCard,
) -> dict[str, Any]:
    path = learner_path(root, day.day_id)
    markdown = path.read_text(encoding="utf-8")
    day_state = state["days"].setdefault(day.day_id, {})
    review, review_payload = review_state(root, day.day_id, manifest, markdown)
    ci = ci_state(root, day.day_id)
    checks = {
        "positive": meaningful(section(markdown, "Test positif")),
        "negative": meaningful(section(markdown, "Refus attendu")),
        "rollback": meaningful(section(markdown, "Rollback")),
        "ci": ci,
    }
    status = learner_status(markdown)
    source_mode = day_state.get("source_mode", "guide-only")
    receipt = raw_evidence_receipt(root, day.day_id)
    raw_record = receipt or {}
    if receipt is not None:
        day_state["raw_evidence"] = dict(receipt)
    raw_evidence = {
        "id": raw_record.get("id"),
        "sha256": raw_record.get("sha256"),
    }
    review_criteria = review_payload.get("criteria", [])
    review_acquired = bool(review_criteria) and all(
        isinstance(item, dict) and item.get("result") == "acquired"
        for item in review_criteria
    )
    raw_ready = receipt is not None
    prior_checkpoints = {"prediction", "attempt"} <= set(
        day_state.get("commit_checkpoints", [])
    )
    phase = phase_for_day(day.day_id)
    activation = (
        {"kind": "audited-phase", "phase": phase}
        if phase is not None
        else day_state.get("activation", {"kind": "unrecorded"})
    )
    conformity = "pending"
    if status == "Validé" and all(
        checks[key] for key in ("positive", "negative", "rollback")
    ):
        conformity = (
            "conforme"
            if (
                ci == "conforme"
                and review == "ready"
                and review_acquired
                and source_mode == "guide-only"
                and raw_ready
                and prior_checkpoints
            )
            else "non_conforme"
        )
    payload = {
        "schema_version": 1,
        "day_id": day.day_id,
        "guide": {
            "version": manifest["active_version"],
            "sha256": manifest["sha256"],
            "refs": guide_references(day),
        },
        "activation": activation,
        "source_mode": source_mode,
        "learner_status": status or "En cours",
        "commits": checkpoint_commits(day_state),
        "checks": checks,
        "review": {
            "status": review,
            "criteria": review_criteria,
            "guide_sha256": review_payload.get("guide_sha256"),
            "section_digests": review_payload.get("section_digests", {}),
        },
        "raw_evidence": raw_evidence,
        "section_digests": section_digests(markdown, PROOF_SECTIONS),
        "conformity": conformity,
        "timestamps": {
            "started_at": day_state.get("started_at"),
            "updated_at": now_iso(),
        },
    }
    proof_path = day_directory(root, day.day_id) / ".proof" / "proof.json"
    if proof_path.exists():
        existing = read_json(proof_path)
        existing_without_time = dict(existing)
        payload_without_time = dict(payload)
        existing_without_time.pop("timestamps", None)
        payload_without_time.pop("timestamps", None)
        if existing_without_time == payload_without_time:
            payload["timestamps"] = existing["timestamps"]
            return payload
    atomic_json(proof_path, payload)
    return payload


def final_seal_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / ".proof" / "final-seal.json"


def checkpoint_plan_path(root: Path, day_id: str) -> Path:
    return day_directory(root, day_id) / ".proof" / "checkpoint-plan.json"


def checkpoint_plan_for_commit(
    root: Path, day_id: str, checkpoint: str, commit: str
) -> dict[str, Any] | None:
    if checkpoint not in {"prediction", "attempt", "final"}:
        return None
    plan_path = str(checkpoint_plan_path(root, day_id).relative_to(root))
    result = run(["git", "show", f"{commit}:{plan_path}"], cwd=root)
    if result.returncode != 0:
        return None
    try:
        plan = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(plan, dict) or set(plan) != {
        "schema_version",
        "day_id",
        "checkpoint",
        "base_head",
        "paths",
    }:
        return None
    paths = plan.get("paths")
    if (
        plan.get("schema_version") != 1
        or plan.get("day_id") != day_id
        or plan.get("checkpoint") != checkpoint
        or not isinstance(plan.get("base_head"), str)
        or re.fullmatch(r"[0-9a-f]{40,64}", plan["base_head"]) is None
        or not isinstance(paths, list)
        or not paths
        or not all(
            isinstance(path, str)
            and path
            and not Path(path).is_absolute()
            and ".." not in Path(path).parts
            for path in paths
        )
        or paths != sorted(set(paths))
    ):
        return None
    parents = run(["git", "show", "-s", "--format=%P", commit], cwd=root)
    if parents.returncode != 0 or parents.stdout.strip().split() != [plan["base_head"]]:
        return None
    changed = run(
        [
            "git",
            "diff",
            "--no-renames",
            "--name-only",
            f"{plan['base_head']}..{commit}",
        ],
        cwd=root,
    )
    if changed.returncode != 0 or set(changed.stdout.splitlines()) != set(paths):
        return None
    if plan_path not in paths:
        return None
    anchor = (
        final_seal_path(root, day_id)
        if checkpoint == "final"
        else learner_path(root, day_id)
    )
    if str(anchor.relative_to(root)) not in paths:
        return None
    protected = [
        path
        for path in paths
        if any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in PROTECTED_LEARNING_PATHS
        )
    ]
    if protected:
        return None
    day_prefix = str(day_directory(root, day_id).relative_to(root)) + "/"
    if checkpoint in {"prediction", "final"} and any(
        not path.startswith(day_prefix) for path in paths
    ):
        return None
    return plan


def prepare_final_seal(
    root: Path,
    state: dict[str, Any],
    day: DayCard,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    day_state = state.get("days", {}).get(day.day_id, {})
    checkpoints = day_state.get("checkpoint_commits", {})
    prediction = (
        checkpoints.get("prediction") if isinstance(checkpoints, dict) else None
    )
    attempt = checkpoints.get("attempt") if isinstance(checkpoints, dict) else None
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40,64}", value)
        for value in (prediction, attempt)
    ):
        raise LearningError(
            "Les jalons prévision et tentative doivent précéder le final."
        )
    proof_path = day_directory(root, day.day_id) / ".proof" / "proof.json"
    journal = learner_path(root, day.day_id)
    if not proof_path.is_file() or not journal.is_file():
        raise LearningError("La preuve et le journal doivent exister avant le final.")
    payload = {
        "schema_version": 1,
        "day_id": day.day_id,
        "guide": {
            "version": manifest["active_version"],
            "sha256": manifest["sha256"],
        },
        "learner_status": learner_status(journal.read_text(encoding="utf-8")),
        "learner_sha256": sha256_file(journal),
        "proof_sha256": sha256_file(proof_path),
        "checkpoint_commits": {
            "prediction": prediction,
            "attempt": attempt,
        },
    }
    target = final_seal_path(root, day.day_id)
    if not target.exists() or read_json(target) != payload:
        atomic_json(target, payload)
    return payload


def final_seal_errors(
    root: Path,
    day_id: str,
    proof: dict[str, Any],
    markdown: str,
) -> list[str]:
    target = final_seal_path(root, day_id)
    if not target.is_file():
        return [f"{day_id}: final-seal.json absent"]
    try:
        seal = read_json(target)
    except LearningError as exc:
        return [f"{day_id}: {exc}"]
    expected_fields = {
        "schema_version",
        "day_id",
        "guide",
        "learner_status",
        "learner_sha256",
        "proof_sha256",
        "checkpoint_commits",
    }
    if set(seal) != expected_fields:
        return [f"{day_id}: schéma du scellement final invalide"]
    proof_guide = proof.get("guide")
    commits = proof.get("commits")
    expected_checkpoints = (
        {"prediction": commits[0], "attempt": commits[1]}
        if isinstance(commits, list) and len(commits) == 2
        else None
    )
    expected = {
        "schema_version": 1,
        "day_id": day_id,
        "guide": (
            {
                "version": proof_guide.get("version"),
                "sha256": proof_guide.get("sha256"),
            }
            if isinstance(proof_guide, dict)
            else None
        ),
        "learner_status": learner_status(markdown),
        "learner_sha256": sha256_text(markdown),
        "proof_sha256": sha256_file(day_directory(root, day_id) / ".proof/proof.json"),
        "checkpoint_commits": expected_checkpoints,
    }
    return [] if seal == expected else [f"{day_id}: scellement final incohérent"]


def current_git_head(root: Path) -> str | None:
    result = run(["git", "rev-parse", "HEAD"], cwd=root)
    return result.stdout.strip() if result.returncode == 0 else None


def infer_day_base(root: Path) -> str | None:
    for baseline in ("origin/master", "master"):
        result = run(["git", "merge-base", "HEAD", baseline], cwd=root)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return current_git_head(root)


def hydrate_checkpoint_state(
    root: Path, day_id: str, day_state: dict[str, Any]
) -> None:
    relatives = (
        str(learner_path(root, day_id).relative_to(root)),
        str(final_seal_path(root, day_id).relative_to(root)),
    )
    history = run(
        [
            "git",
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x00%s",
            "HEAD",
            "--",
            *relatives,
        ],
        cwd=root,
    )
    if history.returncode != 0:
        return
    labels = {
        f"{day_id}: prévision": "prediction",
        f"{day_id}: tentative": "attempt",
        f"{day_id}: résultat final": "final",
    }
    revisions_relative = str(
        (day_directory(root, day_id) / ".proof/revisions.json").relative_to(root)
    )
    local_checkpoints: dict[str, str] = {}
    for line in history.stdout.splitlines():
        commit, separator, subject = line.partition("\0")
        checkpoint = labels.get(subject)
        if (
            not separator
            or checkpoint is None
            or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None
        ):
            continue
        if checkpoint == "prediction" and local_checkpoints:
            continue
        replacing = checkpoint in local_checkpoints
        if replacing and checkpoint == "prediction":
            continue
        plan = checkpoint_plan_for_commit(root, day_id, checkpoint, commit)
        candidate_state = dict(day_state)
        candidate_state["checkpoint_commits"] = dict(local_checkpoints)
        if checkpoint == "prediction":
            expected_parent = _trusted_mainline_commit(
                root, plan.get("base_head") if plan is not None else None
            )
        else:
            expected_parent = (
                validated_revision_parent(
                    root,
                    day_id,
                    checkpoint,
                    candidate_state,
                    revision_commit=commit,
                    require_recorded_chain=True,
                )
                if replacing
                else expected_checkpoint_parent(
                    root,
                    day_id,
                    checkpoint,
                    candidate_state,
                    allow_revision=False,
                )
            )
        if plan is None or plan.get("base_head") != expected_parent:
            continue
        if replacing and revisions_relative not in plan.get("paths", []):
            continue
        if checkpoint == "attempt" and "prediction" not in local_checkpoints:
            continue
        if checkpoint == "final" and "attempt" not in local_checkpoints:
            continue
        if checkpoint == "attempt" and replacing:
            local_checkpoints.pop("final", None)
        local_checkpoints[checkpoint] = commit
        if checkpoint == "prediction":
            day_state["base_commit"] = expected_parent
            if "start_commit" in day_state:
                day_state["start_commit"] = expected_parent
    for reopened_checkpoint in ("attempt", "final"):
        candidate_state = dict(day_state)
        candidate_state["checkpoint_commits"] = dict(local_checkpoints)
        if (
            validated_revision_parent(
                root,
                day_id,
                reopened_checkpoint,
                candidate_state,
                require_recorded_chain=True,
            )
            is None
        ):
            continue
        local_checkpoints.pop("final", None)
        if reopened_checkpoint == "attempt":
            local_checkpoints.pop("attempt", None)
        break
    branch = day_state.get("branch")
    if not isinstance(branch, str):
        branch = current_branch(root)
    remote_ref = f"origin/{branch}" if isinstance(branch, str) else ""
    remote_exists = (
        bool(remote_ref)
        and run(
            ["git", "rev-parse", "--verify", f"{remote_ref}^{{commit}}"], cwd=root
        ).returncode
        == 0
    )
    published: dict[str, str] = {}
    for name in ("prediction", "attempt", "final"):
        commit = local_checkpoints.get(name)
        if commit is None:
            break
        if (
            not remote_exists
            or run(
                ["git", "merge-base", "--is-ancestor", commit, remote_ref], cwd=root
            ).returncode
            != 0
        ):
            break
        published[name] = commit
    day_state["checkpoint_commits"] = published
    day_state["commit_checkpoints"] = list(published)
    if day_state.get("pending_checkpoint") or published == local_checkpoints:
        return
    head = current_git_head(root)
    unpublished = [
        (name, commit)
        for name, commit in local_checkpoints.items()
        if name not in published
    ]
    if not unpublished or unpublished[-1][1] != head:
        return
    checkpoint, commit = unpublished[-1]
    plan = checkpoint_plan_for_commit(root, day_id, checkpoint, commit)
    if plan is None:
        return
    day_state["pending_checkpoint"] = {
        "name": checkpoint,
        "base_head": plan["base_head"],
        "paths": plan["paths"],
        "commit": commit,
    }


def prepare_resumed_day(root: Path, day_id: str, day_state: dict[str, Any]) -> None:
    if not day_state.get("resume_from_consolidation") or day_state.get(
        "resume_prepared"
    ):
        return
    day_state["checkpoint_commits"] = {}
    day_state["commit_checkpoints"] = []
    day_state.pop("pending_checkpoint", None)
    day_state.pop("raw_evidence", None)
    day_state["command_index"] = 0
    proof_directory = day_directory(root, day_id) / ".proof"
    for name in ("ci.json", "review.json", "review.md"):
        target = proof_directory / name
        if target.exists():
            target.unlink()
    resume_from = day_state.get("resume_from_consolidation")
    source_branch = day_state.get("resume_source_branch")
    version = day_state.get("guide_version")
    digest = day_state.get("guide_sha256")
    if not all(
        isinstance(value, str)
        for value in (resume_from, source_branch, version, digest)
    ):
        raise LearningError("Contexte versionné de reprise incomplet.")
    atomic_json(
        resume_receipt_path(root, day_id),
        {
            "schema_version": 1,
            "day_id": day_id,
            "resume_from_consolidation": resume_from,
            "resume_source_branch": source_branch,
            "guide_version": version,
            "guide_sha256": digest,
        },
    )
    day_state["resume_prepared"] = True


def restored_resumption_journal(
    root: Path, day_id: str, day_state: dict[str, Any]
) -> str | None:
    if not day_state.get("resume_from_consolidation"):
        return None
    source_branch = day_state.get("resume_source_branch")
    if not isinstance(source_branch, str):
        raise LearningError("La branche source de la reprise est absente.")
    if (
        re.fullmatch(
            rf"learn/{day_id.lower()}(?:-(?:retry|resume)-\d+)?", source_branch
        )
        is None
    ):
        raise LearningError("La branche source de la reprise est invalide.")
    context = _blocked_branch_context(root, day_id, source_branch)
    expected = (
        source_branch,
        day_state.get("guide_version"),
        day_state.get("guide_sha256"),
    )
    if context is None or context != expected:
        raise LearningError(
            "La branche source de la reprise diverge ou son guide n'est pas épinglé."
        )
    relative = str(learner_path(root, day_id).relative_to(root))
    journals: list[str] = []
    for reference in (source_branch, f"origin/{source_branch}"):
        resolved = run(
            ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root
        )
        if resolved.returncode != 0:
            continue
        result = run(["git", "show", f"{reference}:{relative}"], cwd=root)
        if result.returncode != 0:
            raise LearningError(
                "Le journal bloqué est absent de sa branche historique."
            )
        journals.append(result.stdout)
    if not journals or len(set(journals)) != 1:
        raise LearningError(
            "Les copies locale et distante du journal bloqué divergent."
        )
    restored = journals[0]
    if re.search(rf"(?m)^#\s+{re.escape(day_id)}\b", restored) is None:
        raise LearningError("Le journal archivé ne correspond pas à la journée.")
    if learner_guide_identity(restored) != expected[1:]:
        raise LearningError("L'identité du guide restauré est incohérente.")
    return restored


def ensure_day(
    root: Path,
    manifest: dict[str, Any],
    guide: Path,
    state: dict[str, Any],
) -> tuple[DayCard, Path]:
    day_id = str(state.get("active_day") or DEFAULT_DAY)
    assert_day_activation(manifest, state, day_id)
    day_state = state["days"].setdefault(day_id, {})
    raw_activation = day_state.get("activation")
    day = activated_day_card(
        guide,
        day_id,
        raw_activation if isinstance(raw_activation, dict) else None,
    )
    path = learner_path(root, day_id)
    if path.exists():
        try:
            journal_identity = learner_guide_identity(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise LearningError(f"Journal illisible pour {day_id}.") from exc
        if journal_identity is None:
            raise LearningError(f"L'identité du guide est absente du journal {day_id}.")
        journal_version, journal_hash = journal_identity
        for key, value in (
            ("guide_version", journal_version),
            ("guide_sha256", journal_hash),
        ):
            recorded = day_state.get(key)
            if recorded is not None and recorded != value:
                raise LearningError(
                    f"L'épinglage {key} du journal {day_id} est incohérent."
                )
            day_state.setdefault(key, value)
    pinned_version = day_state.get("guide_version")
    pinned_hash = day_state.get("guide_sha256")
    if (pinned_version and pinned_version != manifest["active_version"]) or (
        pinned_hash and pinned_hash != manifest["sha256"]
    ):
        raise LearningError(
            f"{day_id} est liée au guide {pinned_version or '?'} "
            f"({pinned_hash or '?'}); termine ou reprends la journée "
            "explicitement avant de changer de version."
        )
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        restored = restored_resumption_journal(root, day_id, day_state)
        path.write_text(
            restored if restored is not None else render_template(root, manifest, day),
            encoding="utf-8",
        )
    try:
        restored_identity = learner_guide_identity(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise LearningError(f"Journal illisible pour {day_id}.") from exc
    expected_identity = (
        str(day_state.get("guide_version") or manifest["active_version"]),
        str(day_state.get("guide_sha256") or manifest["sha256"]),
    )
    if restored_identity != expected_identity:
        raise LearningError(f"L'identité du guide du journal {day_id} est incohérente.")
    if int(day_id.removeprefix("J")) > TOTAL_MAIN_DAYS:
        activation = day_state.get("activation")
        if not isinstance(activation, dict):
            raise LearningError(f"Activation de consolidation absente pour {day_id}.")
        activation_path = day_directory(root, day_id) / ".proof" / "activation.json"
        activation_record = {
            "schema_version": 1,
            "day_id": day_id,
            "activation": activation,
        }
        resume_source = day_state.get("resume_source_branch")
        if isinstance(resume_source, str):
            activation_record["resume_source_branch"] = resume_source
        if (
            not activation_path.exists()
            or read_json(activation_path) != activation_record
        ):
            atomic_json(activation_path, activation_record)
    proof_path = day_directory(root, day_id) / ".proof" / "proof.json"
    if proof_path.exists():
        try:
            existing_proof = read_json(proof_path)
        except LearningError:
            existing_proof = {}
        guide_record = existing_proof.get("guide", {})
        if isinstance(guide_record, dict):
            if isinstance(guide_record.get("version"), str):
                day_state.setdefault("guide_version", guide_record["version"])
            if isinstance(guide_record.get("sha256"), str):
                day_state.setdefault("guide_sha256", guide_record["sha256"])
        if isinstance(existing_proof.get("source_mode"), str):
            day_state.setdefault("source_mode", existing_proof["source_mode"])
        activation = existing_proof.get("activation")
        if isinstance(activation, dict):
            day_state.setdefault("activation", activation)
        receipt = raw_evidence_receipt(root, day_id)
        raw = existing_proof.get("raw_evidence")
        if (
            receipt is not None
            and isinstance(raw, dict)
            and raw == {"id": receipt["id"], "sha256": receipt["sha256"]}
        ):
            day_state.setdefault("raw_evidence", dict(receipt))
    day_state.setdefault("started_at", now_iso())
    day_state.setdefault("base_commit", infer_day_base(root))
    if has_training_taint(root, day_id):
        day_state["source_mode"] = "training-only"
        day_state["ignored_artifact_baseline"] = {}
    else:
        day_state.setdefault("source_mode", "guide-only")
    day_state.setdefault("command_index", 0)
    day_state.setdefault("checkpoint_commits", {})
    if "ignored_artifact_baseline" not in day_state:
        try:
            day_state["ignored_artifact_baseline"] = ignored_artifact_snapshot(root)
        except LearningError:
            day_state["ignored_artifact_baseline"] = {}
    day_state.setdefault("guide_version", manifest["active_version"])
    day_state.setdefault("guide_sha256", manifest["sha256"])
    day_state.setdefault("issue_url", None)
    day_state.setdefault("pr_url", None)
    hydrate_checkpoint_state(root, day_id, day_state)
    if "attempt" in set(day_state.get("commit_checkpoints", [])):
        day_state["command_index"] = len(day.commands)
    prepare_resumed_day(root, day_id, day_state)
    save_state(root, state)
    return day, path


def mark_training_only(root: Path, state: dict[str, Any], day_id: str) -> None:
    state["days"].setdefault(day_id, {})["source_mode"] = "training-only"
    atomic_json(
        source_mode_receipt_path(root, day_id),
        {
            "schema_version": 1,
            "day_id": day_id,
            "source_mode": "training-only",
        },
    )
    save_state(root, state)
    append_capture(root, day_id, "source-mode", "training-only")


def training_attempt_paths(
    root: Path, base_commit: str, ignored_baseline: dict[str, str] | None = None
) -> list[str]:
    changed = run(
        ["git", "diff", "--name-only", "--no-renames", "-z", base_commit, "--"],
        cwd=root,
    )
    if changed.returncode != 0:
        raise LearningError("Impossible de borner les fichiers de la tentative.")
    paths = {path for path in changed.stdout.split("\0") if path}
    paths.update(git_dirty_paths(root))
    baseline = ignored_baseline or {}
    current_ignored = ignored_artifact_snapshot(root)
    paths.update(
        path for path, digest in current_ignored.items() if baseline.get(path) != digest
    )
    safe: list[str] = []
    for path in sorted(paths):
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise LearningError("Un chemin de tentative sort du dépôt.")
        ensure_inside(root, root / candidate)
        safe.append(path)
    protected = [
        path
        for path in safe
        if any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in PROTECTED_LEARNING_PATHS
        )
    ]
    if protected:
        raise LearningError(
            "Une tentative aidée a modifié le plan de contrôle protégé : "
            + ", ".join(protected)
        )
    if not safe:
        raise LearningError("Aucun fichier de tentative n'est disponible à archiver.")
    return safe


def _restore_attempt_baseline(root: Path, base_commit: str, paths: list[str]) -> None:
    current = run(["git", "ls-files", "-z", "--", *paths], cwd=root)
    baseline = run(
        ["git", "ls-tree", "-r", "--name-only", "-z", base_commit, "--", *paths],
        cwd=root,
    )
    if current.returncode != 0 or baseline.returncode != 0:
        raise LearningError("Impossible d'identifier les fichiers à restaurer.")
    tracked = {
        path
        for output in (current.stdout, baseline.stdout)
        for path in output.split("\0")
        if path
    }
    if tracked:
        restored = run(
            [
                "git",
                "restore",
                f"--source={base_commit}",
                "--staged",
                "--worktree",
                "--",
                *sorted(tracked),
            ],
            cwd=root,
        )
        if restored.returncode != 0:
            raise LearningError("Impossible de restaurer la baseline de la tentative.")
    untracked = sorted(set(paths) - tracked)
    if untracked:
        cleaned = run(["git", "clean", "-fdx", "--", *untracked], cwd=root)
        if cleaned.returncode != 0:
            raise LearningError("Impossible de retirer les fichiers aidés archivés.")


def restart_guide_only_attempt(
    root: Path,
    state: dict[str, Any],
    manifest: dict[str, Any],
    guide: Path,
    day: DayCard,
) -> int:
    day_state = state["days"].get(day.day_id, {})
    if day_state.get("source_mode") != "training-only":
        raise LearningError(
            "Seule une tentative training-only peut être reconstruite ainsi."
        )
    base_commit = day_state.get("base_commit")
    if not isinstance(base_commit, str):
        raise LearningError("La baseline propre de la tentative est introuvable.")
    baseline = run(["git", "cat-file", "-e", f"{base_commit}^{{commit}}"], cwd=root)
    ancestry = run(
        ["git", "merge-base", "--is-ancestor", base_commit, "HEAD"], cwd=root
    )
    if baseline.returncode != 0 or ancestry.returncode != 0:
        raise LearningError(
            "La baseline propre n'est pas un ancêtre vérifiable de la tentative."
        )
    ignored_baseline = day_state.get("ignored_artifact_baseline", {})
    if isinstance(ignored_baseline, list):
        # Ancien cache local : choix conservateur, tous les artefacts courants
        # non ambiants seront archivés puis nettoyés.
        ignored_baseline = {}
    if not isinstance(ignored_baseline, dict) or not all(
        isinstance(path, str)
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", digest)
        for path, digest in ignored_baseline.items()
    ):
        raise LearningError("La baseline des artefacts ignorés est invalide.")
    attempt_paths = training_attempt_paths(root, base_commit, ignored_baseline)
    if not confirm(
        "Archiver toute la tentative et ses livrables en deux copies chiffrées "
        "puis repartir d'un squelette vide sur une nouvelle branche ?"
    ):
        print("Reconstruction annulée.")
        return 0

    retry = int(day_state.get("retry_count", 0)) + 1
    activation = day_state.get("activation")
    if int(day.day_id.removeprefix("J")) > TOTAL_MAIN_DAYS:
        if not isinstance(activation, dict):
            raise LearningError(
                f"Activation de consolidation absente pour {day.day_id}."
            )
        kind = activation.get("kind")
        trigger = activation.get("triggered_by")
        branch_kind = {
            "blocked-day": "blocked",
            "pathway-completion": "pathway",
        }.get(kind)
        if (
            branch_kind is None
            or not isinstance(trigger, str)
            or not re.fullmatch(r"J\d{3}", trigger)
        ):
            raise LearningError("Activation de consolidation invalide.")
        branch = (
            f"learn/{day.day_id.lower()}-{branch_kind}-{trigger.lower()}-retry-{retry}"
        )
    else:
        branch = f"learn/{day.day_id.lower()}-retry-{retry}"
    original_branch = current_branch(root)
    exists = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=root)
    if exists.returncode == 0:
        raise LearningError(f"La branche de reconstruction existe déjà : {branch}")

    source_directory = day_directory(root, day.day_id)
    with tempfile.TemporaryDirectory(prefix="aegis-training-scope-") as temporary:
        scope = Path(temporary) / "attempt-paths.json"
        atomic_json(
            scope,
            {
                "schema_version": 1,
                "day_id": day.day_id,
                "base_commit": base_commit,
                "paths": attempt_paths,
            },
        )
        archive_sources = [scope]
        archive_sources.extend(
            root / path
            for path in attempt_paths
            if (root / path).exists() or (root / path).is_symlink()
        )
        archive_raw_evidence(root, day.day_id, archive_sources)
    archived_state = load_state(root)
    archived = archived_state["days"][day.day_id].get("raw_evidence")
    if not isinstance(archived, dict) or not archived.get("sha256"):
        raise LearningError("L'archive de la tentative n'a pas été vérifiée.")
    receipt_relative = str(
        raw_evidence_receipt_path(root, day.day_id).relative_to(root)
    )
    cleanup_paths = sorted(set(attempt_paths) | {receipt_relative})
    _restore_attempt_baseline(root, base_commit, cleanup_paths)
    switched = run(["git", "switch", "-c", branch, base_commit], cwd=root)
    if switched.returncode != 0:
        raise LearningError((switched.stderr or switched.stdout).strip())
    if git_dirty_paths(root):
        raise LearningError(
            "Le worktree n'est pas propre après l'archivage de la tentative."
        )

    source_directory.mkdir(parents=True, exist_ok=True)
    proof_directory = source_directory / ".proof"
    if proof_directory.exists():
        shutil.rmtree(proof_directory)
    learner = source_directory / "learner.md"
    learner.write_text(render_template(root, manifest, day), encoding="utf-8")
    training_attempts = list(day_state.get("training_attempts", []))
    training_attempts.append(
        {
            "ended_at": now_iso(),
            "branch": original_branch,
            "archive": {"id": archived.get("id"), "sha256": archived.get("sha256")},
        }
    )
    atomic_json(
        proof_directory / "training-attempts.json",
        {
            "schema_version": 1,
            "day_id": day.day_id,
            "attempts": training_attempts,
        },
    )
    if isinstance(activation, dict):
        activation_record = {
            "schema_version": 1,
            "day_id": day.day_id,
            "activation": activation,
        }
        resume_source = day_state.get("resume_source_branch")
        if isinstance(resume_source, str):
            activation_record["resume_source_branch"] = resume_source
        atomic_json(
            proof_directory / "activation.json",
            activation_record,
        )
    rebuilt_state: dict[str, Any] = {
        "started_at": now_iso(),
        "base_commit": base_commit,
        "source_mode": "guide-only",
        "guide_version": manifest["active_version"],
        "guide_sha256": manifest["sha256"],
        "issue_url": day_state.get("issue_url"),
        "issue_number": day_state.get("issue_number"),
        "pr_url": None,
        "branch": branch,
        "github_mode": "managed",
        "command_index": 0,
        "checkpoint_commits": {},
        "retry_count": retry,
        "training_attempts": training_attempts,
    }
    resume_count = int(day_state.get("resume_count", 0))
    if resume_count:
        rebuilt_state["resume_count"] = resume_count
    blocked_attempts = day_state.get("blocked_attempts")
    if isinstance(blocked_attempts, list):
        rebuilt_state["blocked_attempts"] = list(blocked_attempts)
    state["days"][day.day_id] = rebuilt_state
    if isinstance(activation, dict):
        state["days"][day.day_id]["activation"] = activation
        resume_source = day_state.get("resume_source_branch")
        if isinstance(resume_source, str):
            state["days"][day.day_id]["resume_source_branch"] = resume_source
    save_state(root, state)
    print(
        f"Nouvelle tentative guide-only préparée sur {branch}. "
        "L'ancienne tentative n'accorde aucun crédit."
    )
    return 0


def schedule_consolidation(root: Path, state: dict[str, Any], day_id: str) -> str:
    if int(day_id.removeprefix("J")) > TOTAL_MAIN_DAYS:
        raise LearningError(
            "Une consolidation bloquée reste active ; aucune seconde "
            "consolidation ne peut être empilée."
        )
    if state.get("suspended_day"):
        raise LearningError("Une journée est déjà suspendue par une consolidation.")
    used = set(state.get("completed_days", [])) | set(
        state.get("consolidation_queue", [])
    )
    consolidation = next(
        (
            f"J{number:03d}"
            for number in range(TOTAL_MAIN_DAYS + 1, TOTAL_DAYS + 1)
            if f"J{number:03d}" not in used
        ),
        None,
    )
    if consolidation is None:
        raise LearningError("Les 20 journées de consolidation sont déjà attribuées.")
    state["suspended_day"] = day_id
    state["consolidation_queue"].append(consolidation)
    consolidation_state = state["days"].setdefault(consolidation, {})
    consolidation_state["activation"] = {
        "kind": "blocked-day",
        "triggered_by": day_id,
    }
    consolidation_state["branch"] = (
        f"learn/{consolidation.lower()}-blocked-{day_id.lower()}"
    )
    blocked_state = state["days"].get(day_id, {})
    source_branch = blocked_state.get("branch")
    if (
        not isinstance(source_branch, str)
        or re.fullmatch(r"learn/j\d{3}(?:-(?:retry|resume)-\d+)?", source_branch)
        is None
    ):
        raise LearningError("La branche source de la journée bloquée est invalide.")
    consolidation_state["resume_source_branch"] = source_branch
    for key in ("guide_version", "guide_sha256"):
        value = blocked_state.get(key)
        if not isinstance(value, str):
            raise LearningError(
                "L'épinglage du guide de la journée bloquée est incomplet."
            )
        consolidation_state[key] = value
    base_commit = blocked_state.get("base_commit")
    if not isinstance(base_commit, str):
        raise LearningError("La baseline propre de la journée bloquée est absente.")
    consolidation_state["start_commit"] = base_commit
    state["active_day"] = consolidation
    state["next_day"] = day_id
    save_state(root, state)
    return consolidation


def pr_is_merged(
    root: Path,
    pr_url: str | None,
    checkpoint_commits_record: dict[str, Any] | None = None,
) -> str | None:
    if not pr_url:
        return None
    result = run(
        [
            "gh",
            "pr",
            "view",
            pr_url,
            "--json",
            "baseRefName,headRefOid,state,mergeCommit",
        ],
        cwd=root,
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, AttributeError):
        return None
    if payload.get("state") != "MERGED" or payload.get("baseRefName") != "master":
        return None
    checkpoints = checkpoint_commits_record or {}
    final = checkpoints.get("final")
    if not isinstance(final, str) or payload.get("headRefOid") != final:
        return None
    merge_record = payload.get("mergeCommit")
    merge_commit = merge_record.get("oid") if isinstance(merge_record, dict) else None
    if not isinstance(merge_commit, str):
        return None
    fetched = run(
        [
            "git",
            "fetch",
            "--quiet",
            "origin",
            "+refs/heads/master:refs/remotes/origin/master",
        ],
        cwd=root,
        timeout=120,
    )
    if fetched.returncode != 0:
        return None
    for commit in (final, merge_commit):
        if run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root).returncode:
            return None
    parents = run(["git", "rev-list", "--parents", "-n", "1", merge_commit], cwd=root)
    tokens = parents.stdout.split() if parents.returncode == 0 else []
    if len(tokens) != 3 or final not in tokens[1:]:
        return None
    merged = all(
        run(
            ["git", "merge-base", "--is-ancestor", commit, "origin/master"],
            cwd=root,
        ).returncode
        == 0
        for commit in (final, merge_commit)
    )
    return merge_commit if merged else None


def verified_remote_master_head(root: Path) -> str:
    result = run(["git", "rev-parse", "--verify", "origin/master^{commit}"], cwd=root)
    commit = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
        raise LearningError("La baseline fusionnée origin/master est introuvable.")
    return commit


def reconcile_phase_tag(root: Path, state: dict[str, Any]) -> bool:
    while True:
        tag = state.get("pending_phase_tag")
        expected = state.get("pending_phase_commit")
        if tag is None and expected is None:
            return True
        if (
            not isinstance(tag, str)
            or re.fullmatch(r"phase-(?:0[0-9]|1[0-3])", tag) is None
            or not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{40,64}", expected) is None
        ):
            raise LearningError("Demande de tag de phase locale invalide.")
        resolved = run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
            cwd=root,
        )
        if resolved.returncode != 0:
            remote_identity = _remote_phase_tag_identity(root, tag)
            if remote_identity is not None and remote_identity[1] == expected:
                print(
                    "Jalon de phase distant à récupérer : "
                    + shlex.join(["git", "fetch", "origin", "tag", tag])
                )
            elif remote_identity is None:
                print(
                    "Jalon de phase à signer personnellement : "
                    + shlex.join(
                        ["git", "tag", "-s", "-m", f"Jalon {tag}", tag, expected]
                    )
                )
            else:
                raise LearningError(
                    f"Le tag distant {tag} ne cible pas la baseline attendue."
                )
            return False
        if resolved.stdout.strip() != expected:
            raise LearningError(
                f"Le tag {tag} ne cible pas la baseline fusionnée attendue."
            )
        local_object = run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag}"], cwd=root
        )
        if (
            local_object.returncode != 0
            or re.fullmatch(r"[0-9a-f]{40,64}", local_object.stdout.strip()) is None
        ):
            raise LearningError(f"L'objet Git du tag {tag} est introuvable.")
        current_signature_valid = _phase_tag_is_valid(root, tag, expected)
        historical_signature_valid = current_signature_valid or _phase_tag_is_valid(
            root,
            tag,
            expected,
            require_current_key=False,
        )
        if not historical_signature_valid:
            raise LearningError(
                f"La signature cryptographique du tag {tag} n'est pas vérifiable."
            )
        remote_identity = _remote_phase_tag_identity(root, tag)
        remote_confirms_published_tag = remote_identity == (
            local_object.stdout.strip(),
            expected,
        )
        if not current_signature_valid and not remote_confirms_published_tag:
            raise LearningError(
                f"La signature cryptographique du tag {tag} n'est pas vérifiable."
            )
        if remote_identity is None:
            print(
                "Jalon de phase signé à publier : "
                + shlex.join(["git", "push", "origin", f"refs/tags/{tag}"])
            )
            return False
        if remote_identity[1] != expected:
            raise LearningError(
                f"Le tag distant {tag} ne cible pas la baseline fusionnée attendue."
            )
        if remote_identity[0] != local_object.stdout.strip():
            raise LearningError(
                f"L'objet distant du tag {tag} diffère du tag signé localement."
            )
        state.pop("pending_phase_tag", None)
        state.pop("pending_phase_commit", None)
        completed = {
            value for value in state.get("completed_days", []) if isinstance(value, str)
        }
        recover_pending_phase_tag(root, state, completed)
        save_state(root, state)
        print(f"Jalon de phase {tag} signé et publié sur origin.")


def submit_day_pr(
    root: Path, pr_url: str, checkpoint_commits_record: dict[str, Any]
) -> str | None:
    if not confirm("Soumettre puis fusionner cette journée sans squash ?"):
        return None
    ready = run(["gh", "pr", "ready", pr_url], cwd=root)
    if ready.returncode != 0 and "already marked" not in (ready.stderr or ""):
        raise LearningError((ready.stderr or ready.stdout).strip())
    merged = run(["gh", "pr", "merge", pr_url, "--merge"], cwd=root)
    if merged.returncode != 0:
        raise LearningError((merged.stderr or merged.stdout).strip())
    return pr_is_merged(root, pr_url, checkpoint_commits_record)


def _next_main_day(day_id: str) -> str | None:
    number = int(day_id.removeprefix("J"))
    return f"J{number + 1:03d}" if number < TOTAL_MAIN_DAYS else None


def _next_daily_branch_generation(
    root: Path, day_id: str, kind: str, recorded: int
) -> int:
    refs = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/heads",
            "refs/remotes/origin",
        ],
        cwd=root,
    )
    generations = {recorded}
    if refs.returncode == 0:
        pattern = re.compile(
            rf"(?:origin/)?learn/{day_id.lower()}-{re.escape(kind)}-(\d+)"
        )
        generations.update(
            int(match.group(1))
            for reference in refs.stdout.splitlines()
            if (match := pattern.fullmatch(reference)) is not None
        )
    return max(generations) + 1


def plan_resumed_attempt(
    root: Path,
    state: dict[str, Any],
    day_id: str,
    consolidation: str,
    *,
    start_commit: str | None = None,
) -> None:
    day_state = state["days"].setdefault(day_id, {})
    previous: dict[str, Any] = {
        "consolidation": consolidation,
        "branch": day_state.get("branch") or f"learn/{day_id.lower()}",
        "checkpoint_commits": dict(day_state.get("checkpoint_commits", {})),
    }
    if isinstance(day_state.get("raw_evidence"), dict):
        previous["raw_evidence"] = dict(day_state["raw_evidence"])
    day_state.setdefault("blocked_attempts", []).append(previous)
    resume_count = _next_daily_branch_generation(
        root, day_id, "resume", int(day_state.get("resume_count", 0))
    )
    start_commit = start_commit or current_git_head(root)
    if not start_commit:
        raise LearningError("Le HEAD de la consolidation fusionnée est introuvable.")
    source_branch = str(previous["branch"])
    day_state.update(
        {
            "resume_from_consolidation": consolidation,
            "resume_prepared": False,
            "resume_source_branch": source_branch,
            "resume_count": resume_count,
            "branch": f"learn/{day_id.lower()}-resume-{resume_count}",
            "start_commit": start_commit,
            "base_commit": start_commit,
            "pr_url": None,
            "github_mode": "managed",
            "source_mode": "guide-only",
            "command_index": 0,
            "checkpoint_commits": {},
            "commit_checkpoints": [],
        }
    )
    day_state.pop("pending_checkpoint", None)
    day_state.pop("raw_evidence", None)


def complete_day(
    root: Path,
    state: dict[str, Any],
    day_id: str,
    *,
    merged_baseline: str | None = None,
    next_start_commit: str | None = None,
) -> str | None:
    merged_baseline = merged_baseline or current_git_head(root)
    if not merged_baseline:
        raise LearningError("La baseline fusionnée est introuvable.")
    next_start_commit = next_start_commit or merged_baseline
    completed = state.setdefault("completed_days", [])
    if day_id not in completed:
        completed.append(day_id)
    state["days"].setdefault(day_id, {})["baseline_commit"] = merged_baseline
    number = int(day_id.removeprefix("J"))
    if number > TOTAL_MAIN_DAYS:
        queue = state.get("consolidation_queue", [])
        if day_id in queue:
            queue.remove(day_id)
        suspended = state.pop("suspended_day", None)
        if suspended:
            consolidation_state = state["days"].get(day_id, {})
            source_branch = consolidation_state.get("resume_source_branch")
            source_context = (
                _blocked_branch_context(root, suspended, source_branch)
                if isinstance(source_branch, str)
                else None
            )
            if source_context is None or source_context[1:] != (
                consolidation_state.get("guide_version"),
                consolidation_state.get("guide_sha256"),
            ):
                raise LearningError(
                    "La source versionnée de la journée à reprendre est incohérente."
                )
            _apply_blocked_source_context(
                state["days"].setdefault(suspended, {}), source_context
            )
            plan_resumed_attempt(
                root,
                state,
                suspended,
                day_id,
                start_commit=next_start_commit,
            )
        next_day = suspended or (queue[0] if queue else None)
    else:
        next_day = _next_main_day(day_id)
        if next_day is None:
            remaining = [
                f"J{value:03d}"
                for value in range(TOTAL_MAIN_DAYS + 1, TOTAL_DAYS + 1)
                if f"J{value:03d}" not in completed
            ]
            state["consolidation_queue"] = remaining
            for consolidation in remaining:
                consolidation_state = state["days"].setdefault(consolidation, {})
                consolidation_state["activation"] = {
                    "kind": "pathway-completion",
                    "triggered_by": "J370",
                }
                consolidation_state["branch"] = (
                    f"learn/{consolidation.lower()}-pathway-j370"
                )
            next_day = remaining[0] if remaining else None
    if next_day:
        next_state = state["days"].setdefault(next_day, {})
        next_state.setdefault("start_commit", next_start_commit)
        next_state.setdefault("base_commit", next_start_commit)
    state["active_day"] = next_day
    state["next_day"] = (
        _next_main_day(next_day)
        if next_day and int(next_day.removeprefix("J")) <= TOTAL_MAIN_DAYS
        else None
    )
    phase = phase_for_day(day_id)
    if phase is not None:
        boundaries = {
            0: 10,
            1: 40,
            2: 70,
            3: 100,
            4: 120,
            5: 155,
            6: 185,
            7: 210,
            8: 235,
            9: 260,
            10: 285,
            11: 305,
            12: 345,
            13: 370,
        }
        if number == boundaries[phase]:
            state["pending_phase_tag"] = f"phase-{phase:02d}"
            state["pending_phase_commit"] = merged_baseline
    save_state(root, state)
    return next_day


def show_next_command(day: DayCard, index: int) -> None:
    if not day.commands:
        print("Prochaine action : consulte la procédure de la fiche active.")
        return
    if index >= len(day.commands):
        return
    print(
        f"Prochaine commande proposée par le guide ({index + 1}/{len(day.commands)}) :"
    )
    print(f"  {day.commands[index]}")
    print("Avant de l'exécuter, explique ses options puis observe son code retour.")


def next_commit_checkpoint(
    markdown: str,
    day_state: dict[str, Any],
    day: DayCard | None = None,
    *,
    allow_validated_final: bool = False,
) -> str | None:
    completed = set(day_state.get("commit_checkpoints", []))
    if "prediction" not in completed and meaningful(section(markdown, "Ma prévision")):
        return "prediction"
    commands_complete = day is None or int(day_state.get("command_index", 0)) >= len(
        day.commands
    )
    attempt_ready = commands_complete and all(
        meaningful(section(markdown, title)) for title in LEARNER_SECTIONS
    )
    status = learner_status(markdown)
    resuming_block = bool(day_state.get("resume_from_consolidation")) and (
        status == "Bloqué"
    )
    if (
        "attempt" not in completed
        and attempt_ready
        and status != "Validé"
        and not resuming_block
    ):
        return "attempt"
    final_status = status == "Bloqué" or (status == "Validé" and allow_validated_final)
    if "attempt" in completed and "final" not in completed and final_status:
        return "final"
    return None


def checkpoint_paths(
    root: Path, day_id: str, pending: dict[str, Any] | None = None
) -> list[str]:
    if pending is not None:
        recorded = pending.get("paths")
        if (
            isinstance(recorded, list)
            and recorded
            and all(isinstance(path, str) for path in recorded)
        ):
            return list(recorded)
    prefix = str(day_directory(root, day_id).relative_to(root)) + "/"
    return sorted(path for path in git_dirty_paths(root) if path.startswith(prefix))


def checkpoint_candidate_paths(
    root: Path,
    day_id: str,
    checkpoint: str,
    *,
    base_commit: str | None = None,
) -> list[str]:
    dirty = sorted(set(git_dirty_paths(root)))
    committed: list[str] = []
    if base_commit:
        result = run(["git", "diff", "--name-only", f"{base_commit}..HEAD"], cwd=root)
        if result.returncode != 0:
            raise LearningError("Impossible de vérifier le plan de contrôle Git.")
        committed = result.stdout.splitlines()
    protected = [
        path
        for path in sorted(set(dirty + committed))
        if any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in PROTECTED_LEARNING_PATHS
        )
    ]
    if protected:
        raise LearningError(
            "Le plan de contrôle pédagogique a été modifié pendant la journée : "
            + ", ".join(protected)
        )
    day_prefix = str(day_directory(root, day_id).relative_to(root)) + "/"
    if checkpoint in {"prediction", "final"}:
        unrelated = [path for path in dirty if not path.startswith(day_prefix)]
        if unrelated:
            message = (
                "Écris et pousse la prévision avant de modifier le lab : "
                if checkpoint == "prediction"
                else "Le final ne peut sceller que les artefacts de la journée : "
            )
            raise LearningError(message + ", ".join(unrelated))
    if not dirty:
        raise LearningError("Aucun changement de la journée n'est prêt à versionner.")
    return dirty


def _path_status(root: Path, paths: list[str]) -> tuple[bool, bool]:
    result = run(["git", "status", "--porcelain", "--", *paths], cwd=root)
    if result.returncode != 0:
        raise LearningError("Impossible de lire l'état Git du journal.")
    staged = False
    unstaged = False
    for line in result.stdout.splitlines():
        if line.startswith("??"):
            unstaged = True
            continue
        staged = staged or (len(line) > 0 and line[0] != " ")
        unstaged = unstaged or (len(line) > 1 and line[1] != " ")
    return staged, unstaged


def checkpoint_unstaged_paths(root: Path, paths: list[str]) -> list[str]:
    tracked = run(
        ["git", "diff", "--no-renames", "--name-only", "--", *paths], cwd=root
    )
    untracked = run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *paths],
        cwd=root,
    )
    if tracked.returncode != 0 or untracked.returncode != 0:
        raise LearningError("Impossible d'identifier les chemins à indexer.")
    return sorted(set(tracked.stdout.splitlines() + untracked.stdout.splitlines()))


def _verified_commit_hash(root: Path, value: Any) -> str | None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
        return None
    resolved = run(
        ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
        cwd=root,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != value:
        return None
    return value


def _trusted_mainline_commit(root: Path, value: Any) -> str | None:
    commit = _verified_commit_hash(root, value)
    if commit is None:
        return None
    remote = run(["git", "rev-parse", "--verify", "origin/master^{commit}"], cwd=root)
    reference = "origin/master" if remote.returncode == 0 else "master"
    local = run(["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root)
    if (
        local.returncode != 0
        or run(
            ["git", "merge-base", "--is-ancestor", commit, reference], cwd=root
        ).returncode
        != 0
    ):
        return None
    return commit


def _revision_history(
    root: Path, day_id: str, revision_commit: str | None = None
) -> dict[str, Any] | None:
    revisions_path = day_directory(root, day_id) / ".proof/revisions.json"
    if revision_commit is None:
        if not revisions_path.is_file():
            return None
        try:
            history = read_json(revisions_path)
        except LearningError:
            return None
    else:
        if _verified_commit_hash(root, revision_commit) is None:
            return None
        relative = str(revisions_path.relative_to(root))
        snapshot = run(
            ["git", "show", f"{revision_commit}:{relative}"],
            cwd=root,
        )
        if snapshot.returncode != 0:
            return None
        try:
            history = json.loads(snapshot.stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(history, dict):
            return None
    revisions = history.get("revisions")
    if (
        set(history) != {"schema_version", "day_id", "revisions"}
        or history.get("schema_version") != 1
        or history.get("day_id") != day_id
        or not isinstance(revisions, list)
        or not revisions
        or not isinstance(revisions[-1], dict)
    ):
        return None
    return history


def _latest_revision_record(
    root: Path, day_id: str, revision_commit: str | None = None
) -> dict[str, Any] | None:
    history = _revision_history(root, day_id, revision_commit)
    if history is None:
        return None
    revisions = history["revisions"]
    latest = revisions[-1]
    return latest if isinstance(latest, dict) else None


def _checkpoint_chain_is_valid(
    root: Path,
    day_id: str,
    prediction: Any,
    attempt: Any,
    final: Any,
    *,
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> bool:
    prediction_commit = _verified_commit_hash(root, prediction)
    attempt_commit = _verified_commit_hash(root, attempt)
    final_commit = _verified_commit_hash(root, final)
    if not all((prediction_commit, attempt_commit, final_commit)):
        return False
    pair = (attempt_commit, final_commit)
    if pair in seen:
        return False
    visited = seen | {pair}
    prediction_plan = checkpoint_plan_for_commit(
        root, day_id, "prediction", prediction_commit
    )
    attempt_plan = checkpoint_plan_for_commit(root, day_id, "attempt", attempt_commit)
    final_plan = checkpoint_plan_for_commit(root, day_id, "final", final_commit)
    subjects = {
        name: run(["git", "show", "-s", "--format=%s", commit], cwd=root)
        for name, commit in (
            ("prediction", prediction_commit),
            ("attempt", attempt_commit),
            ("final", final_commit),
        )
    }
    if (
        prediction_plan is None
        or attempt_plan is None
        or final_plan is None
        or _trusted_mainline_commit(root, prediction_plan.get("base_head"))
        != prediction_plan.get("base_head")
        or subjects["prediction"].returncode != 0
        or subjects["prediction"].stdout.strip() != f"{day_id}: prévision"
        or subjects["attempt"].returncode != 0
        or subjects["attempt"].stdout.strip() != f"{day_id}: tentative"
        or subjects["final"].returncode != 0
        or subjects["final"].stdout.strip() != f"{day_id}: résultat final"
    ):
        return False

    if attempt_plan.get("base_head") != prediction_commit:
        record = _latest_revision_record(root, day_id, attempt_commit)
        revisions_relative = str(
            (day_directory(root, day_id) / ".proof/revisions.json").relative_to(root)
        )
        if (
            not isinstance(record, dict)
            or record.get("mode") != "full-reattempt"
            or revisions_relative not in attempt_plan.get("paths", [])
        ):
            return False
        previous_attempt = record.get("previous_attempt")
        previous_final = record.get("previous_final")
        if not _checkpoint_chain_is_valid(
            root,
            day_id,
            prediction_commit,
            previous_attempt,
            previous_final,
            seen=visited,
        ):
            return False
        previous_state = {
            "checkpoint_commits": {
                "prediction": prediction_commit,
                "attempt": previous_attempt,
                "final": previous_final,
            }
        }
        if validated_revision_parent(
            root,
            day_id,
            "attempt",
            previous_state,
            revision_commit=attempt_commit,
            require_recorded_chain=True,
            validate_previous_chain=False,
        ) != attempt_plan.get("base_head"):
            return False

    if final_plan.get("base_head") == attempt_commit:
        return True
    record = _latest_revision_record(root, day_id, final_commit)
    revisions_relative = str(
        (day_directory(root, day_id) / ".proof/revisions.json").relative_to(root)
    )
    if (
        not isinstance(record, dict)
        or record.get("mode") != "reseal-after-base-update"
        or record.get("previous_attempt") != attempt_commit
        or revisions_relative not in final_plan.get("paths", [])
    ):
        return False
    previous_final = record.get("previous_final")
    if not _checkpoint_chain_is_valid(
        root,
        day_id,
        prediction_commit,
        attempt_commit,
        previous_final,
        seen=visited,
    ):
        return False
    previous_state = {
        "checkpoint_commits": {
            "prediction": prediction_commit,
            "attempt": attempt_commit,
            "final": previous_final,
        }
    }
    return validated_revision_parent(
        root,
        day_id,
        "final",
        previous_state,
        revision_commit=final_commit,
        require_recorded_chain=True,
        validate_previous_chain=False,
    ) == final_plan.get("base_head")


def validated_revision_parent(
    root: Path,
    day_id: str,
    checkpoint: str,
    day_state: dict[str, Any],
    *,
    revision_commit: str | None = None,
    require_recorded_chain: bool = False,
    validate_previous_chain: bool = True,
) -> str | None:
    """Valide la dernière réouverture avant d'autoriser un jalon de remplacement."""

    expected_mode = {
        "attempt": "full-reattempt",
        "final": "reseal-after-base-update",
    }.get(checkpoint)
    if expected_mode is None:
        return None
    latest = _latest_revision_record(root, day_id, revision_commit)
    if latest is None:
        return None
    required_fields = {
        "reopened_at",
        "mode",
        "previous_attempt",
        "previous_final",
        "head_at_reopen",
    }
    if frozenset(latest) not in {
        frozenset(required_fields),
        frozenset(required_fields | {"raw_evidence"}),
    }:
        return None
    if latest.get("mode") != expected_mode or not _valid_timestamp(
        latest.get("reopened_at")
    ):
        return None
    raw = latest.get("raw_evidence")
    if raw is not None and (
        not isinstance(raw, dict)
        or set(raw) != {"id", "sha256"}
        or not isinstance(raw.get("id"), str)
        or re.fullmatch(rf"{re.escape(day_id.lower())}-[0-9a-f]{{32}}", raw["id"])
        is None
        or re.fullmatch(r"[0-9a-f]{64}", str(raw.get("sha256", ""))) is None
    ):
        return None

    previous_attempt = _verified_commit_hash(root, latest.get("previous_attempt"))
    previous_final = _verified_commit_hash(root, latest.get("previous_final"))
    head_at_reopen = _verified_commit_hash(root, latest.get("head_at_reopen"))
    if not all((previous_attempt, previous_final, head_at_reopen)):
        return None
    recorded = day_state.get("checkpoint_commits")
    checkpoints = recorded if isinstance(recorded, dict) else {}
    if require_recorded_chain and (
        checkpoints.get("attempt") != previous_attempt
        or checkpoints.get("final") != previous_final
    ):
        return None
    for name, previous in (
        ("attempt", previous_attempt),
        ("final", previous_final),
    ):
        if name in checkpoints and checkpoints.get(name) != previous:
            return None
    prediction = checkpoints.get("prediction")
    if (
        _verified_commit_hash(root, prediction) is None
        or run(
            ["git", "merge-base", "--is-ancestor", prediction, previous_attempt],
            cwd=root,
        ).returncode
        != 0
    ):
        return None

    attempt_plan = checkpoint_plan_for_commit(root, day_id, "attempt", previous_attempt)
    final_plan = checkpoint_plan_for_commit(root, day_id, "final", previous_final)
    attempt_subject = run(
        ["git", "show", "-s", "--format=%s", previous_attempt], cwd=root
    )
    final_subject = run(["git", "show", "-s", "--format=%s", previous_final], cwd=root)
    if (
        attempt_plan is None
        or final_plan is None
        or (
            validate_previous_chain
            and not _checkpoint_chain_is_valid(
                root,
                day_id,
                prediction,
                previous_attempt,
                previous_final,
            )
        )
        or attempt_subject.returncode != 0
        or attempt_subject.stdout.strip() != f"{day_id}: tentative"
        or final_subject.returncode != 0
        or final_subject.stdout.strip() != f"{day_id}: résultat final"
        or run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                previous_attempt,
                previous_final,
            ],
            cwd=root,
        ).returncode
        != 0
        or run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                previous_final,
                head_at_reopen,
            ],
            cwd=root,
        ).returncode
        != 0
        or run(
            ["git", "merge-base", "--is-ancestor", head_at_reopen, "HEAD"],
            cwd=root,
        ).returncode
        != 0
    ):
        return None
    if expected_mode == "full-reattempt":
        return head_at_reopen

    parents = run(["git", "rev-list", "--parents", "-n", "1", head_at_reopen], cwd=root)
    parent_tokens = parents.stdout.split() if parents.returncode == 0 else []
    if (
        len(parent_tokens) != 3
        or parent_tokens[0] != head_at_reopen
        or previous_final not in parent_tokens[1:]
    ):
        return None
    other_parent = next(
        (parent for parent in parent_tokens[1:] if parent != previous_final), None
    )
    if (
        other_parent is None
        or run(
            ["git", "rev-parse", "--verify", "origin/master^{commit}"], cwd=root
        ).returncode
        != 0
        or run(
            ["git", "merge-base", "--is-ancestor", other_parent, "origin/master"],
            cwd=root,
        ).returncode
        != 0
    ):
        return None
    expected_tree = run(
        ["git", "merge-tree", "--write-tree", previous_final, other_parent],
        cwd=root,
    )
    actual_tree = run(["git", "rev-parse", f"{head_at_reopen}^{{tree}}"], cwd=root)
    expected_tree_id = expected_tree.stdout.strip()
    actual_tree_id = actual_tree.stdout.strip()
    if (
        expected_tree.returncode != 0
        or actual_tree.returncode != 0
        or re.fullmatch(r"[0-9a-f]{40,64}", expected_tree_id) is None
        or expected_tree_id != actual_tree_id
    ):
        return None
    return head_at_reopen


def expected_checkpoint_parent(
    root: Path,
    day_id: str,
    checkpoint: str,
    day_state: dict[str, Any],
    *,
    allow_revision: bool = True,
) -> str | None:
    checkpoints = day_state.get("checkpoint_commits")
    recorded = checkpoints if isinstance(checkpoints, dict) else {}
    if checkpoint == "prediction":
        expected = day_state.get("base_commit") or day_state.get("start_commit")
    elif checkpoint == "attempt":
        expected = recorded.get("prediction")
    elif checkpoint == "final":
        expected = recorded.get("attempt")
    else:
        return None

    if allow_revision:
        revision_parent = validated_revision_parent(root, day_id, checkpoint, day_state)
        if revision_parent is not None:
            expected = revision_parent
    if (
        not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-f]{40,64}", expected) is None
    ):
        return None
    return expected


def begin_checkpoint(
    root: Path, state: dict[str, Any], day_id: str, checkpoint: str
) -> None:
    day_state = state["days"].setdefault(day_id, {})
    base_head = current_git_head(root)
    if not base_head:
        raise LearningError("La baseline Git du jalon est introuvable.")
    expected_parent = expected_checkpoint_parent(root, day_id, checkpoint, day_state)
    if expected_parent is None:
        raise LearningError(
            f"Le parent autorisé du jalon {checkpoint} est introuvable."
        )
    if base_head != expected_parent:
        raise LearningError(
            f"Le jalon {checkpoint} doit suivre directement son parent autorisé; "
            "aucun commit intermédiaire n'est permis."
        )
    paths = checkpoint_candidate_paths(
        root,
        day_id,
        checkpoint,
        base_commit=str(
            day_state.get("base_commit") or day_state.get("start_commit") or ""
        )
        or None,
    )
    plan_path = checkpoint_plan_path(root, day_id)
    plan_relative = str(plan_path.relative_to(root))
    paths = sorted(set(paths) | {plan_relative})
    plan = {
        "schema_version": 1,
        "day_id": day_id,
        "checkpoint": checkpoint,
        "base_head": base_head,
        "paths": paths,
    }
    atomic_json(plan_path, plan)
    day_state["pending_checkpoint"] = {
        "name": checkpoint,
        "base_head": base_head,
        "paths": paths,
        "plan_sha256": sha256_file(plan_path),
    }
    save_state(root, state)


def guide_pending_checkpoint(root: Path, state: dict[str, Any], day_id: str) -> bool:
    """Retourne True lorsqu'une seule commande Git a été proposée puis s'arrête."""

    day_state = state["days"].get(day_id, {})
    pending = day_state.get("pending_checkpoint")
    if not pending:
        return False
    paths = checkpoint_paths(root, day_id, pending)
    staged, unstaged = _path_status(root, paths)
    checkpoint = str(pending["name"])
    labels = {
        "prediction": "prévision",
        "attempt": "tentative",
        "final": "résultat final",
    }
    if unstaged:
        add_paths = checkpoint_unstaged_paths(root, paths)
        if not add_paths:
            raise LearningError("L'état Git du plan gelé est incohérent.")
        print("Prochaine commande Git :")
        print("  " + shlex.join(["git", "add", "--", *add_paths]))
        return True
    if staged:
        message = f"{day_id}: {labels[checkpoint]}"
        print("Prochaine commande Git :")
        print(
            "  " + shlex.join(["git", "commit", "--only", "-m", message, "--", *paths])
        )
        return True
    head = current_git_head(root)
    if head and head != pending.get("base_head"):
        base_head = pending.get("base_head")
        if (
            not isinstance(base_head, str)
            or re.fullmatch(r"[0-9a-f]{40,64}", base_head) is None
        ):
            raise LearningError("La baseline du jalon Git est invalide.")
        parents = run(["git", "show", "-s", "--format=%P", head], cwd=root)
        if parents.returncode != 0 or parents.stdout.strip().split() != [base_head]:
            raise LearningError("Le jalon Git doit être un commit direct du plan gelé.")
        changed = run(
            [
                "git",
                "diff",
                "--no-renames",
                "--name-only",
                f"{base_head}..{head}",
            ],
            cwd=root,
        )
        if changed.returncode != 0:
            raise LearningError("Impossible de vérifier le contenu du jalon Git.")
        changed_paths = set(changed.stdout.splitlines())
        expected_paths = set(paths)
        if changed_paths != expected_paths:
            extra = sorted(changed_paths - expected_paths)
            missing = sorted(expected_paths - changed_paths)
            details = []
            if extra:
                details.append("ajouts hors plan : " + ", ".join(extra))
            if missing:
                details.append("chemins gelés absents : " + ", ".join(missing))
            raise LearningError(
                "Le commit du jalon diffère du plan gelé (" + "; ".join(details) + ")."
            )
        plan = checkpoint_plan_for_commit(root, day_id, checkpoint, head)
        if (
            plan is None
            or plan.get("base_head") != base_head
            or plan.get("paths") != paths
        ):
            raise LearningError("Le reçu versionné du plan de jalon est invalide.")
        expected_plan_sha = pending.get("plan_sha256")
        if isinstance(expected_plan_sha, str):
            committed_plan = run(
                [
                    "git",
                    "show",
                    f"{head}:{checkpoint_plan_path(root, day_id).relative_to(root)}",
                ],
                cwd=root,
            )
            if (
                committed_plan.returncode != 0
                or sha256_text(committed_plan.stdout) != expected_plan_sha
            ):
                raise LearningError("Le plan de jalon a changé après son gel.")
        checkpoint_anchor = (
            final_seal_path(root, day_id)
            if checkpoint == "final"
            else learner_path(root, day_id)
        )
        anchor_relative = str(checkpoint_anchor.relative_to(root))
        if anchor_relative in changed_paths:
            recorded_commit = pending.get("commit")
            if recorded_commit and recorded_commit != head:
                raise LearningError(
                    "Un nouveau commit est apparu avant la fin du jalon courant."
                )
            pending["commit"] = head
            save_state(root, state)
            upstream = run(
                [
                    "git",
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                ],
                cwd=root,
            )
            if upstream.returncode != 0:
                print("Prochaine commande Git :")
                print("  git push --set-upstream origin HEAD")
                return True
            ahead = run(["git", "rev-list", "--count", "@{upstream}..HEAD"], cwd=root)
            if ahead.returncode != 0 or int(ahead.stdout.strip() or "0") > 0:
                print("Prochaine commande Git :")
                print("  git push")
                return True
            completed = day_state.setdefault("commit_checkpoints", [])
            if checkpoint not in completed:
                completed.append(checkpoint)
            day_state.setdefault("checkpoint_commits", {})[checkpoint] = head
            day_state.pop("pending_checkpoint", None)
            save_state(root, state)
            return False
    print("Le jalon Git est attendu, mais aucun changement n'est préparé.")
    return True


def status_gate_errors(
    root: Path,
    manifest: dict[str, Any],
    state: dict[str, Any],
    day: DayCard,
    markdown: str,
    live_ci: str,
) -> list[str]:
    day_state = state["days"].get(day.day_id, {})
    errors: list[str] = []
    if "attempt" not in set(day_state.get("commit_checkpoints", [])):
        errors.append("le jalon tentative doit être poussé")
    if live_ci != "conforme":
        errors.append("la CI de la tentative doit être conforme")
    review, review_payload = review_state(root, day.day_id, manifest, markdown)
    criteria = review_payload.get("criteria", [])
    if (
        review != "ready"
        or not criteria
        or any(
            not isinstance(item, dict) or item.get("result") != "acquired"
            for item in criteria
        )
    ):
        errors.append("la revue liée à cette version doit être ready")
    try:
        receipt = raw_evidence_receipt(root, day.day_id, required=True)
    except LearningError:
        receipt = None
    raw = day_state.get("raw_evidence", {})
    if receipt is None or raw != receipt:
        errors.append("la preuve brute doit être chiffrée sur deux stockages")
    if day_state.get("source_mode") != "guide-only":
        errors.append("la tentative training-only doit être reconstruite")
    return errors


def raw_evidence_storage_errors(root: Path, day_id: str) -> list[str]:
    """Revérifie les deux archives locales juste avant une fusion créditable."""

    try:
        receipt = raw_evidence_receipt(root, day_id, required=True)
        assert receipt is not None
        config = read_json(local_config_path(root))
        primary = _outside_repository(
            root, str(config.get("raw_store", "")), "Le stockage principal"
        )
        offline = _outside_repository(
            root, str(config.get("offline_store", "")), "Le stockage hors ligne"
        )
    except (LearningError, OSError) as exc:
        return [str(exc)]
    if primary == offline or not primary.is_dir() or not offline.is_dir():
        return ["les deux stockages de preuve distincts ne sont pas disponibles"]
    try:
        if primary.stat().st_dev == offline.stat().st_dev:
            return ["les deux copies de preuve utilisent le même système de fichiers"]
    except OSError:
        return ["les stockages de preuve ne peuvent pas être inspectés"]
    filename = f"{receipt['id']}.tar.zst.age"
    copies = (primary / filename, offline / filename)
    for copy in copies:
        try:
            if copy.is_symlink() or not copy.is_file():
                return [f"copie chiffrée absente ou non régulière : {copy}"]
            if sha256_file(copy) != receipt["sha256"]:
                return [f"empreinte de copie chiffrée invalide : {copy}"]
        except OSError:
            return [f"copie chiffrée illisible : {copy}"]
    return []


def reopen_final_checkpoint(
    root: Path,
    state: dict[str, Any],
    day_id: str,
    *,
    confirmed: bool = False,
) -> int:
    """Rouvre de façon traçable un cycle devenu obsolète après son final."""

    day_state = state.get("days", {}).get(day_id, {})
    checkpoints = day_state.get("checkpoint_commits", {})
    old_final = checkpoints.get("final") if isinstance(checkpoints, dict) else None
    old_attempt = checkpoints.get("attempt") if isinstance(checkpoints, dict) else None
    if not isinstance(old_final, str) or not isinstance(old_attempt, str):
        raise LearningError("Aucun jalon final complet n'est disponible à rouvrir.")
    head = current_git_head(root)
    if (
        not head
        or run(
            ["git", "merge-base", "--is-ancestor", old_final, head], cwd=root
        ).returncode
    ):
        raise LearningError(
            "L'ancien jalon final n'est pas un ancêtre du HEAD courant."
        )
    parents = run(["git", "rev-list", "--parents", "-n", "1", head], cwd=root)
    parent_tokens = parents.stdout.split() if parents.returncode == 0 else []
    verified_base_update = False
    if head != old_final and len(parent_tokens) == 3 and old_final in parent_tokens[1:]:
        other_parent = next(
            (parent for parent in parent_tokens[1:] if parent != old_final), None
        )
        fetched = run(
            [
                "git",
                "fetch",
                "--quiet",
                "origin",
                "+refs/heads/master:refs/remotes/origin/master",
            ],
            cwd=root,
            timeout=120,
        )
        other_is_master = (
            bool(other_parent)
            and fetched.returncode == 0
            and run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    str(other_parent),
                    "origin/master",
                ],
                cwd=root,
            ).returncode
            == 0
        )
        expected_tree = run(
            ["git", "merge-tree", "--write-tree", old_final, str(other_parent)],
            cwd=root,
        )
        actual_tree = run(["git", "rev-parse", f"{head}^{{tree}}"], cwd=root)
        expected_tree_id = expected_tree.stdout.strip()
        actual_tree_id = actual_tree.stdout.strip()
        verified_base_update = (
            other_is_master
            and expected_tree.returncode == 0
            and actual_tree.returncode == 0
            and re.fullmatch(r"[0-9a-f]{40,64}", expected_tree_id) is not None
            and expected_tree_id == actual_tree_id
        )
    merge_update_only = verified_base_update and git_worktree_clean(root)
    mode = "reseal-after-base-update" if merge_update_only else "full-reattempt"
    explanation = (
        "conserver la tentative et recréer seulement le jalon final"
        if merge_update_only
        else "invalider tentative, CI, revue et reçu brut avant un nouveau passage"
    )
    if not confirmed and not confirm(
        f"Rouvrir {day_id} ({explanation}) ? L'historique restera tracé"
    ):
        print("Réouverture annulée.")
        return 0

    proof_directory = day_directory(root, day_id) / ".proof"
    history_path = proof_directory / "revisions.json"
    if history_path.exists():
        history = read_json(history_path)
        attempts = history.get("revisions")
        if (
            history.get("schema_version") != 1
            or history.get("day_id") != day_id
            or not isinstance(attempts, list)
        ):
            raise LearningError("Historique de réouverture invalide.")
    else:
        attempts = []
    raw = day_state.get("raw_evidence")
    record: dict[str, Any] = {
        "reopened_at": now_iso(),
        "mode": mode,
        "previous_attempt": old_attempt,
        "previous_final": old_final,
        "head_at_reopen": head,
    }
    if isinstance(raw, dict) and raw.get("id") and raw.get("sha256"):
        record["raw_evidence"] = {"id": raw["id"], "sha256": raw["sha256"]}
    attempts.append(record)
    atomic_json(
        history_path,
        {"schema_version": 1, "day_id": day_id, "revisions": attempts},
    )

    checkpoints.pop("final", None)
    completed = day_state.get("commit_checkpoints", [])
    if isinstance(completed, list):
        day_state["commit_checkpoints"] = [
            name for name in completed if name != "final"
        ]
    day_state.pop("pending_checkpoint", None)
    stale_final_seal = final_seal_path(root, day_id)
    if stale_final_seal.exists():
        stale_final_seal.unlink()
    if not merge_update_only:
        checkpoints.pop("attempt", None)
        day_state["commit_checkpoints"] = [
            name
            for name in day_state.get("commit_checkpoints", [])
            if name != "attempt"
        ]
        day_state["command_index"] = 0
        day_state.pop("raw_evidence", None)
        for name in (
            "ci.json",
            "review.json",
            "review.md",
            "raw-evidence.json",
            "proof.json",
        ):
            target = proof_directory / name
            if target.exists():
                target.unlink()
    save_state(root, state)
    print(
        f"{day_id} rouvert en mode {mode}. "
        + (
            "Une CI conforme permettra de sceller un nouveau final."
            if merge_update_only
            else "Passe le statut à À reprendre, rejoue les commandes et les preuves."
        )
    )
    return 0


def submission_seal_errors(
    root: Path,
    pr_url: str | None,
    checkpoint_commits_record: dict[str, Any] | None = None,
    *,
    day_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    head = current_git_head(root)
    if not git_worktree_clean(root):
        errors.append("le worktree contient des changements non scellés")
    if day_id is not None:
        errors.extend(raw_evidence_storage_errors(root, day_id))
    checkpoints = checkpoint_commits_record or {}
    for name in ("prediction", "attempt", "final"):
        commit = checkpoints.get(name)
        if not isinstance(commit, str):
            errors.append(f"le jalon {name} est absent")
            continue
        ancestor = run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root)
        if ancestor.returncode != 0:
            errors.append(f"le jalon {name} n'est pas un ancêtre du HEAD")
    if isinstance(checkpoints.get("final"), str) and checkpoints["final"] != head:
        errors.append("le HEAD courant n'est pas le jalon final")
    upstream = run(["git", "rev-parse", "--abbrev-ref", "@{upstream}"], cwd=root)
    if upstream.returncode != 0:
        errors.append("la branche n'a pas de branche distante")
    else:
        counts = run(
            ["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
            cwd=root,
        )
        if counts.returncode != 0 or counts.stdout.split() != ["0", "0"]:
            errors.append("la branche locale et sa branche distante divergent")
    if not pr_url:
        errors.append("la draft PR est absente")
    else:
        result = run(
            [
                "gh",
                "pr",
                "view",
                pr_url,
                "--json",
                "baseRefName,headRefOid,state,mergeCommit",
            ],
            cwd=root,
        )
        try:
            pr = json.loads(result.stdout)
            remote_head = pr.get("headRefOid")
        except (json.JSONDecodeError, AttributeError):
            pr = {}
            remote_head = None
        if result.returncode != 0 or not head or remote_head != head:
            errors.append("le HEAD de la PR ne correspond pas au HEAD local")
        if pr.get("baseRefName") != "master":
            errors.append("la PR ne cible pas la branche master")
    return errors


def run_interactive(root: Path, *, details: bool, no_editor: bool) -> int:
    interactive = sys.stdin.isatty() and not no_editor
    initialize_local_config(root, interactive=interactive)
    checks = doctor(root, include_remote=True)
    print_doctor(checks, details=details)
    if any(not item.ok and item.blocking for item in checks):
        print(
            "\nLe cockpit n'ouvre aucune journée tant que ces contrôles "
            "bloquants échouent."
        )
        return 2
    manifest, guide = active_manifest(root)
    state = load_state(root)
    completed = {
        value for value in state.get("completed_days", []) if isinstance(value, str)
    }
    recover_pending_phase_tag(root, state, completed)
    save_state(root, state)
    if not reconcile_phase_tag(root, state):
        print("La journée suivante reste fermée jusqu'à la publication de ce jalon.")
        return 3
    if (
        state.get("active_day") is None
        and len(state.get("completed_days", [])) == TOTAL_DAYS
    ):
        print("Parcours complet : 390/390 journées conformes.")
        return 0
    pending_day_id = str(state.get("active_day") or DEFAULT_DAY)
    manifest, guide = curriculum_for_day(root, manifest, guide, state, pending_day_id)
    assert_day_activation(manifest, state, pending_day_id)
    pending_state = state.get("days", {}).get(pending_day_id, {})
    pending_activation = pending_state.get("activation")
    pending_day = activated_day_card(
        guide,
        pending_day_id,
        pending_activation if isinstance(pending_activation, dict) else None,
    )
    if interactive:
        ensure_github_tracking(root, state, pending_day, interactive=True)
    day, path = ensure_day(root, manifest, guide, state)
    live_ci = ci_state(root, day.day_id)
    if interactive:
        ensure_draft_pr(root, state, day, interactive=True)
        current_day_state = state["days"].get(day.day_id, {})
        final_pushed = "final" in set(current_day_state.get("commit_checkpoints", []))
        pending_checkpoint = bool(current_day_state.get("pending_checkpoint"))
        live_ci = refresh_ci(
            root,
            state,
            day.day_id,
            persist=not final_pushed and not pending_checkpoint,
        )
    if guide_pending_checkpoint(root, state, day.day_id):
        return 0
    completed = len(state.get("completed_days", []))
    print(f"\n{day.day_id} — {day.title}")
    print(
        f"Progression : {completed}/{TOTAL_DAYS} (progression, pas score de maîtrise)"
    )
    print(f"Objectif : {day.objective}")
    print(f"Garde-fou : {day.guardrail}")
    markdown = path.read_text(encoding="utf-8")
    day_state = state["days"].setdefault(day.day_id, {})
    command_index = int(day_state.get("command_index", 0))
    needed = next_learning_step(markdown, day, day_state)
    validation_errors = (
        status_gate_errors(root, manifest, state, day, markdown, live_ci)
        if learner_status(markdown) == "Validé"
        else []
    )
    if validation_errors:
        needed = "Statut"
    checkpoint = next_commit_checkpoint(
        markdown,
        day_state,
        day,
        allow_validated_final=not validation_errors,
    )
    if checkpoint:
        if checkpoint == "final":
            update_proof(root, manifest, state, day)
            prepare_final_seal(root, state, day, manifest)
        begin_checkpoint(root, state, day.day_id, checkpoint)
        guide_pending_checkpoint(root, state, day.day_id)
        return 0
    if details:
        print(f"\nRéférence : {day.reference}\n{day.details}")
    if needed is None:
        proof = update_proof(root, manifest, state, day)
        print(
            f"Contrôle : apprenant={proof['learner_status']}, "
            f"CI={proof['checks']['ci']}, revue={proof['review']['status']}."
        )
        if proof["learner_status"] == "Bloqué":
            if not git_worktree_clean(root):
                print(
                    "Consolidation différée : le worktree de la journée bloquée "
                    "doit être entièrement scellé."
                )
                return 3
            if int(day.day_id.removeprefix("J")) > TOTAL_MAIN_DAYS:
                print(
                    "Cette consolidation reste active : une consolidation ne "
                    "peut pas en ouvrir une seconde."
                )
                checkpoints = day_state.get("checkpoint_commits", {})
                has_final = isinstance(checkpoints, dict) and isinstance(
                    checkpoints.get("final"), str
                )
                if has_final:
                    if interactive and confirm(
                        "Rouvrir le jalon final pour reprendre cette consolidation ?"
                    ):
                        result = reopen_final_checkpoint(
                            root, state, day.day_id, confirmed=True
                        )
                        if result == 0:
                            open_editor(path, "Statut")
                        return result
                    print(
                        "Action de reprise : python3 tools/learn.py reopen-final "
                        + day.day_id
                    )
                else:
                    print(
                        f"Passe le statut à À reprendre dans {path.relative_to(root)}."
                    )
                    if interactive:
                        open_editor(path, "Statut")
                return 3
            consolidation = schedule_consolidation(root, state, day.day_id)
            print(
                f"Journée suspendue. {consolidation} devient la journée active de "
                "consolidation."
            )
            return 0
        if proof["conformity"] != "conforme":
            return 3
        if live_ci != "conforme":
            print("La dernière révision distante attend encore une CI conforme.")
            return 3
        day_state = state["days"].get(day.day_id, {})
        if set(day_state.get("checkpoint_commits", {})) != {
            "prediction",
            "attempt",
            "final",
        }:
            print("Les trois jalons Git poussés ne sont pas encore scellés.")
            return 3
        pr_url = day_state.get("pr_url")
        seal_errors = submission_seal_errors(
            root,
            pr_url,
            day_state.get("checkpoint_commits", {}),
            day_id=day.day_id,
        )
        if seal_errors:
            print("Fusion refusée : " + "; ".join(seal_errors) + ".")
            if interactive and confirm(
                "Rouvrir ce jalon final pour reprendre le cycle proprement ?"
            ):
                return reopen_final_checkpoint(root, state, day.day_id, confirmed=True)
            print(
                "Action de reprise : python3 tools/learn.py reopen-final " + day.day_id
            )
            return 3
        checkpoints = day_state.get("checkpoint_commits", {})
        merge_commit = pr_is_merged(root, pr_url, checkpoints)
        if interactive and pr_url and not merge_commit:
            merge_commit = submit_day_pr(root, str(pr_url), checkpoints)
        if not merge_commit:
            print(
                "La preuve est conforme, mais la demande GitHub doit être "
                "réconciliée et fusionnée avant la journée suivante."
            )
            return 3
        following = complete_day(
            root,
            state,
            day.day_id,
            merged_baseline=merge_commit,
            next_start_commit=verified_remote_master_head(root),
        )
        print(f"Baseline enregistrée. Prochaine journée : {following or 'aucune'}.")
        reconcile_phase_tag(root, state)
        return 0
    print(f"Prochaine étape : {needed}")
    if needed == "Mes observations" and meaningful(section(markdown, "Ma prévision")):
        show_next_command(day, command_index)
    status_errors = (
        status_gate_errors(root, manifest, state, day, markdown, live_ci)
        if needed == "Statut"
        else []
    )
    if status_errors:
        print(
            "Validation indisponible : "
            + "; ".join(status_errors)
            + ". Les statuts Bloqué et À reprendre restent accessibles."
        )
    if no_editor or not interactive:
        print(f"Fichier à compléter : {path.relative_to(root)}")
        return 0
    choice = (
        input(
            "Entrée: ouvrir | c: professeur Codex | d: détails | p: pause | "
            "a: déclarer une aide extérieure | b: archiver une preuve brute | "
            "r: recommencer guide-only | u: rouvrir le final : "
        )
        .strip()
        .lower()
    )
    if choice == "p":
        print("État technique conservé. Relance `make learn` pour reprendre.")
        return 0
    if choice == "a":
        mark_training_only(root, state, day.day_id)
        print(
            "Tentative classée entraînement. Une reconstruction guide-only "
            "sera nécessaire."
        )
        return 0
    if choice == "b":
        values = shlex.split(
            input("Chemin(s) de preuve brute à chiffrer (séparés par espace) : ")
        )
        if not values or not confirm(
            "Créer deux copies chiffrées hors Git avec la clé publique configurée ?"
        ):
            print("Archivage annulé.")
            return 0
        return archive_raw_evidence(root, day.day_id, [Path(value) for value in values])
    if choice == "r":
        return restart_guide_only_attempt(root, state, manifest, guide, day)
    if choice == "u":
        return reopen_final_checkpoint(root, state, day.day_id)
    if choice == "c":
        return launch_professor(root, day, path, needed)
    if choice == "d":
        print(f"\n{day.details}\nRéférence précise : {day.reference}")
        input("Entrée pour ouvrir le journal : ")
    before = section(markdown, needed)
    try:
        open_editor(path, needed)
    except LearningError as exc:
        print(exc, file=sys.stderr)
        return 2
    after_markdown = path.read_text(encoding="utf-8")
    after = section(after_markdown, needed)
    if before != after and meaningful(after):
        append_capture(root, day.day_id, "learner-section-completed", after)
        print("Rubrique détectée. Le contenu reste sous ton contrôle.")
    else:
        print("Rubrique encore incomplète ; elle restera la prochaine étape.")
    if (
        needed == "Mes observations"
        and before != after
        and meaningful(after)
        and command_index < len(day.commands)
    ):
        day_state["command_index"] = command_index + 1
        save_state(root, state)
        append_capture(
            root,
            day.day_id,
            "guide-command-interpreted",
            day.commands[command_index],
        )
    updated_markdown = path.read_text(encoding="utf-8")
    day_state = state["days"].setdefault(day.day_id, {})
    updated_status = learner_status(updated_markdown)
    if day_state.get("resume_from_consolidation") and updated_status != "Bloqué":
        day_state.pop("resume_from_consolidation", None)
        day_state.pop("resume_prepared", None)
        save_state(root, state)
    update_proof(root, manifest, state, day)
    updated_status_errors = (
        status_gate_errors(root, manifest, state, day, updated_markdown, live_ci)
        if updated_status == "Validé"
        else []
    )
    if updated_status_errors:
        print("Validation refusée : " + "; ".join(updated_status_errors) + ".")
        return 3
    checkpoint = next_commit_checkpoint(
        updated_markdown,
        day_state,
        day,
        allow_validated_final=True,
    )
    if checkpoint:
        if checkpoint == "final":
            prepare_final_seal(root, state, day, manifest)
        begin_checkpoint(root, state, day.day_id, checkpoint)
        guide_pending_checkpoint(root, state, day.day_id)
    return 0


def proof_commit_errors(root: Path, commits: list[Any]) -> list[str]:
    if (
        len(commits) != 2
        or len(set(commits)) != len(commits)
        or any(not re.fullmatch(r"[0-9a-f]{40,64}", str(item)) for item in commits)
    ):
        return ["jalons Git de prévision/tentative absents"]
    prediction, attempt = (str(value) for value in commits)
    for label, commit in (("prévision", prediction), ("tentative", attempt)):
        if run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root).returncode:
            return [f"jalon Git {label} introuvable"]
    if run(
        ["git", "merge-base", "--is-ancestor", prediction, attempt], cwd=root
    ).returncode:
        return ["le jalon prévision n'est pas un ancêtre de la tentative"]
    if run(
        ["git", "merge-base", "--is-ancestor", attempt, "HEAD"], cwd=root
    ).returncode:
        return ["le jalon tentative n'est pas un ancêtre du checkout"]
    return []


def validate_day(root: Path, day_id: str) -> list[str]:
    errors: list[str] = []
    manifest, active_guide = active_manifest(root)
    phase = phase_for_day(day_id)
    if phase is not None and phase not in {
        int(value) for value in manifest["audited_phases"]
    }:
        errors.append(f"{day_id}: phase {phase} non auditée")
    path = learner_path(root, day_id)
    if not path.exists():
        return [f"{day_id}: learner.md absent"]
    markdown = path.read_text(encoding="utf-8")
    journal_guide = learner_guide_identity(markdown)
    if journal_guide is None:
        errors.append(f"{day_id}: identité du guide absente du journal")
    missing = [
        title for title in LEARNER_SECTIONS if not meaningful(section(markdown, title))
    ]
    if missing:
        errors.append(f"{day_id}: rubriques incomplètes: {', '.join(missing)}")
    status = learner_status(markdown)
    if status not in ALLOWED_STATUSES:
        errors.append(f"{day_id}: statut invalide")
    if status == "Validé":
        proof_path = day_directory(root, day_id) / ".proof" / "proof.json"
        if not proof_path.exists():
            return [*errors, f"{day_id}: proof.json absent"]
        proof = read_json(proof_path)
        if proof.get("day_id") != day_id:
            errors.append(f"{day_id}: identifiant de preuve incohérent")
        raw_proof_guide = proof.get("guide", {})
        proof_guide = raw_proof_guide if isinstance(raw_proof_guide, dict) else {}
        if not proof_guide:
            errors.append(f"{day_id}: guide de preuve absent")
        elif journal_guide != (
            proof_guide.get("version"),
            proof_guide.get("sha256"),
        ):
            errors.append(f"{day_id}: guide du journal et de la preuve incohérents")
        guide = active_guide
        if proof_guide:
            try:
                guide = registered_guide(
                    root,
                    manifest,
                    str(proof_guide.get("version", "")),
                    str(proof_guide.get("sha256", "")),
                    phase=phase,
                )
            except LearningError as exc:
                errors.append(f"{day_id}: {exc}")
        activation = proof.get("activation")
        try:
            day = activated_day_card(
                guide,
                day_id,
                activation if isinstance(activation, dict) else None,
            )
        except LearningError as exc:
            return [*errors, f"{day_id}: {exc}"]
        expected_guide = {
            "version": proof_guide.get("version"),
            "sha256": proof_guide.get("sha256"),
            "refs": guide_references(day),
        }
        if proof.get("guide") != expected_guide:
            errors.append(f"{day_id}: guide de preuve incohérent")
        if phase is not None:
            if activation != {"kind": "audited-phase", "phase": phase}:
                errors.append(f"{day_id}: activation de phase incohérente")
        elif not isinstance(activation, dict) or activation.get("kind") not in {
            "blocked-day",
            "pathway-completion",
        }:
            errors.append(f"{day_id}: consolidation sans activation vérifiable")
        if proof.get("source_mode") != "guide-only":
            errors.append(f"{day_id}: tentative d'entraînement non créditable")
        if has_reachable_training_taint(root, day_id):
            errors.append(
                f"{day_id}: reçu d'entraînement présent dans l'ascendance Git"
            )
        checks = proof.get("checks", {})
        if not isinstance(checks, dict) or not all(
            checks.get(key) for key in ("positive", "negative", "rollback")
        ):
            errors.append(f"{day_id}: contrôles positif/refus/rollback incomplets")
        if checks.get("ci") != "conforme":
            errors.append(f"{day_id}: CI non conforme")
        raw = proof.get("raw_evidence", {})
        try:
            receipt = raw_evidence_receipt(root, day_id, required=True)
        except LearningError:
            receipt = None
        expected_raw = (
            {"id": receipt["id"], "sha256": receipt["sha256"]}
            if receipt is not None
            else None
        )
        if raw != expected_raw:
            errors.append(f"{day_id}: référence de preuve brute invalide")
        errors.extend(final_seal_errors(root, day_id, proof, markdown))
        commits = proof.get("commits", [])
        if not isinstance(commits, list):
            errors.append(f"{day_id}: jalons Git de prévision/tentative absents")
        else:
            errors.extend(
                f"{day_id}: {message}" for message in proof_commit_errors(root, commits)
            )
        if proof.get("section_digests") != section_digests(markdown, PROOF_SECTIONS):
            errors.append(f"{day_id}: contenu modifié après génération de la preuve")
        review_manifest = {"sha256": proof_guide.get("sha256")}
        review, review_payload = review_state(root, day_id, review_manifest, markdown)
        expected_review = {
            "status": review,
            "criteria": review_payload.get("criteria", []),
            "guide_sha256": review_payload.get("guide_sha256"),
            "section_digests": review_payload.get("section_digests", {}),
        }
        if review != "ready" or proof.get("review") != expected_review:
            errors.append(f"{day_id}: revue absente, périmée ou incohérente")
        if not expected_review["criteria"] or any(
            not isinstance(item, dict) or item.get("result") != "acquired"
            for item in expected_review["criteria"]
        ):
            errors.append(f"{day_id}: critère de revue à reprendre")
        if proof.get("conformity") != "conforme":
            errors.append(f"{day_id}: preuve non conforme")
    return errors


def validate_all(root: Path) -> int:
    active_manifest(root)
    days_root = root / "learning" / "days"
    errors: list[str] = []
    if days_root.exists():
        for directory in sorted(days_root.glob("J[0-9][0-9][0-9]")):
            errors.extend(validate_day(root, directory.name))
    if errors:
        for error in errors:
            print(f"ERREUR: {error}", file=sys.stderr)
        return 1
    print("Contrat d'apprentissage conforme.")
    return 0


def roadmap_content(manifest: dict[str, Any], guide: Path) -> str:
    text = guide.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^## Calendrier des 14 phases\s*\n(\| Phase .*?)(?=\n---)", text
    )
    if not match:
        raise LearningError("Table des phases introuvable dans le guide actif.")
    phase_table = match.group(1).strip()
    audited = {int(value) for value in manifest["audited_phases"]}
    activation_rows = ["| Phase | Activation |", "| ---: | --- |"]
    for phase in range(14):
        status = (
            "Active" if phase in audited else "En attente d'audit et de versionnement"
        )
        activation_rows.append(f"| {phase} | {status} |")
    return (
        "# Roadmap générée depuis le guide actif\n\n"
        "> Ne pas éditer manuellement. Régénérer avec `make learn-roadmap`.\n\n"
        f"- Version : `{manifest['active_version']}`\n"
        f"- SHA-256 : `{manifest['sha256']}`\n"
        f"- Parcours : {TOTAL_MAIN_DAYS} journées principales + "
        f"{TOTAL_CONSOLIDATION_DAYS} consolidations obligatoires\n"
        "- Progression publique : journées conformes / 390, sans valeur de score\n\n"
        "## Calendrier du guide\n\n"
        f"{phase_table}\n\n"
        "## Activation pédagogique\n\n" + "\n".join(activation_rows) + "\n"
    )


def write_roadmap(root: Path) -> int:
    manifest, guide = active_manifest(root)
    target = root / "learning" / "roadmap.md"
    target.write_text(roadmap_content(manifest, guide), encoding="utf-8")
    print(f"Roadmap régénérée : {target.relative_to(root)}")
    return 0


def _outside_repository(root: Path, value: str, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.is_relative_to(root.resolve()):
        raise LearningError(f"{label} doit être situé hors du dépôt Git.")
    return path


def archive_raw_evidence(root: Path, day_id: str, sources: list[Path]) -> int:
    """Chiffre une archive sans supprimer les sources ni journaliser leur contenu."""

    config = read_json(local_config_path(root))
    recipient = str(config.get("age_recipient", "")).strip()
    if not AGE_RECIPIENT.fullmatch(recipient):
        raise LearningError(
            "Ajoute une clé publique dédiée `age_recipient` valide dans "
            ".learning/local.json."
        )
    primary = _outside_repository(
        root, str(config.get("raw_store", "")), "Le stockage principal"
    )
    offline = _outside_repository(
        root, str(config.get("offline_store", "")), "Le stockage hors ligne"
    )
    if primary == offline:
        raise LearningError(
            "Les deux copies chiffrées doivent utiliser deux stockages distincts."
        )
    if not _command_available("age") or not _tar_supports_zstd(root):
        raise LearningError(
            "`age` et GNU tar avec `--zstd` sont requis pour archiver une preuve brute."
        )
    resolved_sources: list[Path] = []
    for source in sources:
        candidate = source.expanduser().resolve()
        if not candidate.exists():
            raise LearningError(f"Source de preuve absente : {source}")
        resolved_sources.append(candidate)
    if not resolved_sources:
        raise LearningError("Au moins une source de preuve est requise.")
    primary.mkdir(parents=True, exist_ok=True)
    if not offline.is_dir():
        raise LearningError(
            "Le stockage hors ligne doit être monté et exister avant l'archivage."
        )
    if primary.stat().st_dev == offline.stat().st_dev:
        raise LearningError(
            "Les deux copies doivent résider sur deux systèmes de fichiers distincts."
        )
    evidence_id = f"{day_id.lower()}-{uuid.uuid4().hex}"
    filename = f"{evidence_id}.tar.zst.age"
    primary_target = primary / filename
    offline_target = offline / filename
    with tempfile.TemporaryDirectory(prefix="aegis-evidence-") as temporary:
        bundle = Path(temporary) / f"{evidence_id}.tar.zst"
        encrypted = Path(temporary) / filename
        tar_result = run(
            [
                "tar",
                "--create",
                "--zstd",
                "--file",
                str(bundle),
                "--",
                *[str(path) for path in resolved_sources],
            ],
            cwd=root,
            timeout=300,
        )
        if tar_result.returncode != 0:
            raise LearningError("La création de l'archive brute a échoué.")
        age_result = run(
            [
                "age",
                "--encrypt",
                "--recipient",
                recipient,
                "--output",
                str(encrypted),
                str(bundle),
            ],
            cwd=root,
            timeout=300,
        )
        if age_result.returncode != 0:
            raise LearningError("Le chiffrement de la preuve brute a échoué.")
        shutil.copy2(encrypted, primary_target)
        shutil.copy2(encrypted, offline_target)
    digest = sha256_file(primary_target)
    if sha256_file(offline_target) != digest:
        raise LearningError("Les deux copies chiffrées ne sont pas identiques.")
    receipt = {
        "schema_version": 1,
        "id": evidence_id,
        "sha256": digest,
        "copies": 2,
        "retention": RAW_EVIDENCE_RETENTION,
        "verified_at": now_iso(),
    }
    atomic_json(raw_evidence_receipt_path(root, day_id), receipt)
    state = load_state(root)
    state["days"].setdefault(day_id, {})["raw_evidence"] = dict(receipt)
    save_state(root, state)
    print(f"Preuve brute chiffrée en deux copies : {evidence_id} ({digest})")
    return 0


def record_review(root: Path, day_id: str, status: str, criteria: list[str]) -> int:
    if status not in {"ready", "changes-requested"}:
        raise LearningError("Revue attendue : ready ou changes-requested.")
    manifest, guide = active_manifest(root)
    state = load_state(root)
    manifest, guide = curriculum_for_day(root, manifest, guide, state, day_id)
    day_state = state.get("days", {}).get(day_id, {})
    activation = day_state.get("activation")
    day = activated_day_card(
        guide,
        day_id,
        activation if isinstance(activation, dict) else None,
    )
    assert_day_activation(manifest, state, day_id)
    learner = learner_path(root, day.day_id)
    if not learner.exists():
        raise LearningError(f"Journal absent pour {day_id}.")
    markdown_source = learner.read_text(encoding="utf-8")
    missing = [
        title
        for title in REVIEW_SECTIONS
        if not meaningful(section(markdown_source, title))
    ]
    if missing:
        raise LearningError(
            "Revue prématurée, rubriques incomplètes : " + ", ".join(missing)
        )
    payload = {
        "schema_version": 1,
        "day_id": day_id,
        "status": status,
        "guide_sha256": manifest["sha256"],
        "section_digests": section_digests(markdown_source, REVIEW_SECTIONS),
        "criteria": [
            {
                "criterion": value,
                "result": "acquired" if status == "ready" else "to_redo",
            }
            for value in criteria
        ],
        "reviewed_at": now_iso(),
        "certification": "consultative-non-certifying",
    }
    proof_directory = day_directory(root, day_id) / ".proof"
    atomic_json(proof_directory / "review.json", payload)
    result_label = "acquis" if status == "ready" else "à reprendre"
    markdown = [
        f"# Revue Codex — {day_id}",
        "",
        f"Statut: {status}",
        "",
        "Cette revue est consultative et ne constitue pas une certification.",
        "",
        "## Critères",
        "",
    ]
    markdown.extend(f"- {criterion}: {result_label}" for criterion in criteria)
    (proof_directory / "review.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )
    print(f"Revue {status} enregistrée pour {day_id}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    subparsers = parser.add_subparsers(dest="command")
    learn = subparsers.add_parser("run", help="Démarrer ou reprendre la journée")
    learn.add_argument("--details", action="store_true")
    learn.add_argument("--no-editor", action="store_true")
    doctor_parser = subparsers.add_parser("doctor", help="Vérifier les prérequis")
    doctor_parser.add_argument("--local-only", action="store_true")
    subparsers.add_parser("validate", help="Valider le contrat des journées")
    subparsers.add_parser("roadmap", help="Régénérer la roadmap du guide actif")
    review = subparsers.add_parser("review", help="Enregistrer la revue Codex")
    review.add_argument("day_id")
    review.add_argument("status", choices=("ready", "changes-requested"))
    review.add_argument("criteria", nargs="+")
    archive = subparsers.add_parser("archive", help=argparse.SUPPRESS)
    archive.add_argument("day_id")
    archive.add_argument("sources", nargs="+", type=Path)
    reopen = subparsers.add_parser(
        "reopen-final", help="Rouvrir un jalon final devenu obsolète"
    )
    reopen.add_argument("day_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    root = arguments.repo_root.resolve()
    try:
        if arguments.command in {None, "run"}:
            return run_interactive(
                root,
                details=getattr(arguments, "details", False),
                no_editor=getattr(arguments, "no_editor", False),
            )
        if arguments.command == "doctor":
            initialize_local_config(root, interactive=False)
            checks = doctor(root, include_remote=not arguments.local_only)
            print_doctor(checks, details=True)
            return 1 if any(not item.ok and item.blocking for item in checks) else 0
        if arguments.command == "validate":
            return validate_all(root)
        if arguments.command == "roadmap":
            return write_roadmap(root)
        if arguments.command == "review":
            return record_review(
                root, arguments.day_id, arguments.status, arguments.criteria
            )
        if arguments.command == "archive":
            return archive_raw_evidence(root, arguments.day_id, arguments.sources)
        if arguments.command == "reopen-final":
            state = load_state(root)
            if state.get("active_day") != arguments.day_id:
                raise LearningError(
                    "Seule la journée active peut rouvrir son jalon final."
                )
            return reopen_final_checkpoint(root, state, arguments.day_id)
    except (LearningError, subprocess.SubprocessError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    parser.error("Commande inconnue")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
