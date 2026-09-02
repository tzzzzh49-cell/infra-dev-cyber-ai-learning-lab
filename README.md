# Secure AI Ops Learning Lab

[![CI](https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/tzzzzh49-cell/infra-dev-cyber-ai-learning-lab/actions/workflows/ci.yml)

Ce dépôt permet d'apprendre en construisant un lab d'infrastructure sécurisé et
de produire des preuves GitHub vérifiables.

## Commencer ici

```bash
make learn
```

C'est la seule commande à retenir. Au premier lancement, elle vérifie le guide,
la confidentialité du dépôt, Git, GitHub CLI, `age`, l'éditeur, la signature Git
personnelle et les alias du lab. Ensuite, elle reprend toujours la journée
active.

Pour une prise en main expliquée pas à pas, consulte
[`TUTORIEL.md`](TUTORIEL.md).

Le cockpit affiche seulement :

- la synthèse précédente ;
- l'objectif et le garde-fou du jour ;
- la prochaine question ou commande logique ;
- l'état des contrôles.

Il ouvre automatiquement l'unique fichier à rédiger, `learner.md`, sur la bonne
rubrique. Les métadonnées de preuve et la mécanique GitHub restent en
arrière-plan.

## Contrat d'apprentissage

- Le guide actif versionné dans `curriculum/` est l'unique source
  d'enseignement et d'évaluation.
- La fiche France Compétences n'est pas une source d'apprentissage.
- Seul l'apprenant rédige `learner.md` et écrit `Statut: Validé`.
- Une tentative aidée par une autre source ou une démonstration est un
  entraînement ; elle doit être reconstruite depuis un état propre pour devenir
  créditable.
- Une journée passe seulement avec le statut de l'apprenant, une CI conforme et
  une revue Codex `ready`.
- La progression publique est `journées conformes / 390`. Ce n'est ni une note,
  ni une certification, ni une déclaration d'expertise.

Pour une séance de professorat, invoquer explicitement `$aegis-professor`. Les
tâches Codex ordinaires ne déclenchent aucun rituel pédagogique.

## Ce que contient le lab

Le support technique existant est conservé : API FastAPI, Docker Compose,
diagnostics système et réseau en lecture seule, Ansible, CI de qualité et de
sécurité, procédures VPS, mTLS, OIDC et sauvegardes Restic. Ces éléments sont des
candidats à auditer ; ils ne donnent aucun crédit automatique.

La correspondance entre le guide et le dépôt se trouve dans
[`learning/lab-map.yml`](learning/lab-map.yml). La roadmap est générée depuis la
version active du guide dans [`learning/roadmap.md`](learning/roadmap.md).

## Maintenance du lab

Les commandes techniques restent disponibles sans encombrer le parcours :

```bash
make help-dev
make check
```

La documentation d'architecture et d'exploitation reste indexée dans
[`docs/README.md`](docs/README.md). Les anciens journaux d'apprentissage sont
conservés dans `docs/archive/legacy-learning/` comme archives non canoniques.
