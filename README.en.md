# Secure AI Ops Learning Lab

This repository combines a secure infrastructure lab with verifiable GitHub
learning evidence. Its public claim is deliberately modest: **“I learn with
rigour.”**

It is the long-running project behind **AegisOps Twin**: a Secure AI Ops
platform progressively built to observe Linux, networks and PostgreSQL, then
produce evidence-backed hypotheses under human approval.

## Find your way

You do not need to understand the whole tree before starting. Pick the entry
that matches your current goal:

| I want to… | Start here |
| --- | --- |
| learn or resume the active day | `make learn` |
| see the learning plan | [`learning/roadmap.md`](learning/roadmap.md) |
| understand where things belong | [`docs/repository-map.md`](docs/repository-map.md) |
| understand the lab architecture | [`docs/architecture.en.md`](docs/architecture.en.md) |
| develop, test or operate the lab | `make help-dev` then [`docs/README.md`](docs/README.md) |

The key distinction is: `curriculum/` defines **what to learn**, `learning/`
holds **the journey and its evidence**, and the technical directories (`app/`,
`ansible/`, `nginx/`, `backup/`…) contain **what is being built**.

## Start here

```bash
make learn
```

This is the only learner command to remember. On first use it checks the active
guide, repository privacy, Git, GitHub CLI, `age`, the editor, personal Git
signing and pseudonymous lab aliases. Later runs resume the active day.

The cockpit shows one objective, one safety guardrail and one next action. It
opens the learner-owned `learner.md` at the expected section; proof metadata and
GitHub bookkeeping stay in the background.

## Learning contract

- The versioned active guide under `curriculum/` is the sole teaching and
  assessment source.
- The France Compétences page is not a learning source.
- Only the learner writes `learner.md` and `Statut: Validé`.
- Outside help or a full demonstration makes the attempt training-only until it
  is reconstructed from a clean state using the guide alone.
- A day advances only after learner validation, conforming CI and a `ready`
  Codex review.
- Public progress is `conforming days / 390`; it is not a score,
  certification or claim of expertise.

Professor mode is enabled only through an explicit `$aegis-professor`
invocation. Ordinary Codex work remains ordinary development work.

## Lab and maintainer commands

The existing FastAPI, Docker Compose, diagnostics, Ansible, security CI, VPS,
mTLS, OIDC and Restic material remains available as lab support. Existing work
is mapped in [`learning/lab-map.yml`](learning/lab-map.yml) but receives no
automatic learning credit.

```bash
make help-dev
make check
```

Technical documentation is indexed in [`docs/README.md`](docs/README.md).
