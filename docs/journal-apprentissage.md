# Journal d’apprentissage

## Rôle du journal

Ce document suit ma progression dans le projet `infra-dev-cyber-ai-learning-lab`.

Le but n’est pas de remplir des cases, mais de garder une trace claire de ce que j’ai réellement appris, testé, corrigé et compris.

Chaque entrée doit idéalement contenir :

- un objectif ;
- une action réalisée ;
- une preuve concrète ;
- une difficulté ou une correction ;
- une prochaine étape.

---

## Méthode de travail

Comprendre → tester → documenter → automatiser → vérifier → améliorer

Règles personnelles :

- je documente ce que je comprends réellement ;
- je note les erreurs au lieu de les cacher ;
- je privilégie les petites étapes vérifiables ;
- je ne donne pas de pouvoir dangereux à l’automatisation ;
- je garde des preuves : commandes, scripts, rapports, commits, fichiers.

---

## Vue d’ensemble des jalons

| Jalon | Sujet | Statut | Preuve |
|---|---|---|---|
| 1 | Création du dépôt | Fait | `README.md`, `AGENTS.md`, `docs/` |
| 2 | Diagnostic local | Fait | `scripts/diagnostic_local.sh` |
| 3 | Mini API FastAPI | Fait | Endpoints `/health`, `/version`, `/diag` |
| 4 | Docker Compose | Fait | `Dockerfile`, `compose.yaml` |
| 5 | Reproductibilité Fedora 44 | Fait | `docs/reproductibilite-fedora-44-vm.md` |
| 6 | Makefile | En cours | `make check`, `make build`, `make health` |
| 7 | Tests automatisés | Prévu | `pytest` |
| 8 | CI GitHub Actions | Prévu | Workflow CI |
| 9 | VPS | Prévu | Déploiement contrôlé |
| 10 | OpenAI API / OpenClaw | Prévu | Résumé de rapports en lecture seule |

---

# Journal chronologique

## Étape 1 — Création et intention du projet

### Objectif

Créer un dépôt clair pour apprendre Linux, réseau, Docker, FastAPI, automatisation et cybersécurité défensive.

### Ce que j’ai compris

Un dépôt Git n’est pas seulement un endroit où stocker du code.  
C’est aussi une preuve de progression, de méthode et de rigueur.

La documentation doit commencer tôt, car elle explique pourquoi les choix techniques sont faits.

### Preuves

- `README.md`
- `AGENTS.md`
- `docs/securite.md`
- `docs/journal-apprentissage.md`

### Prochaine étape

Rendre le projet reproductible depuis une machine propre.

---

## Étape 2 — Diagnostic local en lecture seule

### Objectif

Créer un premier diagnostic local pour observer l’état d’une machine Linux sans rien modifier.

### Travail réalisé

Création du script :

```bash
scripts/diagnostic_local.sh
```

Le script produit un rapport Markdown dans :

```text
outputs/reports/
```

Il collecte notamment :

- la date du diagnostic ;
- le nom de la machine ;
- la version du système ;
- les interfaces réseau ;
- les routes réseau ;
- les ports ouverts ;
- l’espace disque ;
- la mémoire ;
- les conteneurs Docker ;
- le test de l’endpoint `/health`.

### Ce que j’ai compris

Un diagnostic est une photographie de l’état du système à un moment donné.

Ce type de rapport peut servir de preuve avant ou après une modification.

Le script doit rester en lecture seule pour éviter les actions dangereuses.

### Prochaine étape

Relier le diagnostic à l’API locale et au Makefile.

---

## Étape 3 — Mini API FastAPI

### Objectif

Créer une API locale simple qui servira de support pour Docker, les tests, les diagnostics et l’automatisation.

### Travail réalisé

Création d’une API FastAPI avec trois routes principales :

- `/health`
- `/version`
- `/diag`

L’API a été lancée avec Uvicorn puis testée avec `curl`.

### Ce que j’ai compris

Une API est un service qui répond à des requêtes HTTP.

Uvicorn sert à lancer l’application FastAPI.

L’endpoint `/health` est utile pour vérifier rapidement que le service fonctionne.

### Preuve

```bash
curl http://localhost:8000/health
```

### Prochaine étape

Lancer cette API dans Docker.

---

## Étape 4 — Docker Compose

### Objectif

Lancer la mini API FastAPI dans un conteneur Docker avec Docker Compose.

### Travail réalisé

Commande utilisée :

```bash
docker compose up --build -d
```

### Ce que j’ai compris

- un `Dockerfile` décrit comment construire l’image ;
- `compose.yaml` décrit comment lancer le service ;
- `docker compose config` vérifie la configuration ;
- `docker compose ps` vérifie si le conteneur tourne ;
- `docker compose logs` permet de comprendre ce qui se passe ;
- `curl /health` permet de vérifier que l’API répond.

### Blocage rencontré

Docker Compose n’était pas immédiatement disponible sur Fedora.

Il a fallu corriger l’installation du plugin Compose et les droits Docker.

### Conclusion

Le problème venait de l’environnement Docker local, pas du code de l’application.

### Prochaine étape

Stabiliser les commandes avec un Makefile.

---

## Étape 5 — Stabilisation du dépôt

### Objectif

Rendre le projet plus cohérent, reproductible et compréhensible.

### Travail réalisé

- vérification de la structure du dépôt ;
- création d’une branche dédiée ;
- harmonisation entre README, Makefile et scripts ;
- amélioration des commandes Makefile ;
- test de reproduction depuis zéro ;
- mise à jour de la documentation.

### Ce que j’ai appris

Un projet sérieux doit être vérifiable depuis un clone propre.

Le Makefile simplifie l’utilisation du projet et évite de devoir mémoriser toutes les commandes.

La documentation doit correspondre aux fichiers réellement présents.

### Difficultés rencontrées

- incohérence entre un nom de script et une commande documentée ;
- nécessité de tester chaque commande réellement ;
- différence entre “ça marche chez moi” et “ça marche depuis zéro”.

### Prochaine étape

Préparer les tests automatisés.

---

## Étape 6 — Documentation technique et sécurité

### Objectif

Structurer la documentation pour expliquer l’architecture, la sécurité et les décisions techniques.

### Travail réalisé

- amélioration de `docs/architecture.md` ;
- amélioration de `docs/securite.md` ;
- ajout d’un ADR sur le mode lecture seule ;
- ajout de liens depuis le README ;
- amélioration de la documentation de reproductibilité Fedora 44.

### Ce que j’ai appris

Un projet sérieux ne contient pas seulement du code.

Un ADR permet de justifier une décision technique.

Le mode lecture seule est important pour limiter les risques avant toute automatisation.

### Prochaine étape

Ajouter des tests automatisés avec pytest.

---

## Étape 7 — Makefile et commandes de contrôle

### Objectif

Piloter le projet avec des commandes simples et reproductibles.

### Travail réalisé

- ajout ou amélioration de `make help` ;
- ajout de `make check` ;
- vérification de `make build` ;
- vérification de `make up` ;
- vérification de `make health` ;
- vérification de `make version` ;
- vérification de `make diag` ;
- ajout ou vérification de `make logs` ;
- ajout d’un nettoyage léger avec `make clean`.

### Ce que j’ai compris

Un Makefile peut servir d’interface simple pour tout le projet.

`make -n` permet de voir une commande sans l’exécuter.

Les logs sont essentiels pour diagnostiquer une application.

Une commande `clean` ne doit pas être dangereuse.

### Prochaine étape

Créer les premiers tests automatisés et préparer la CI GitHub Actions.

---

# Compétences suivies

| Domaine | Niveau actuel | À consolider |
|---|---|---|
| Linux | Bases utiles pour diagnostic | Services, logs, permissions |
| Git | Commits, branches, push/pull | Historique propre, PR |
| Bash | Script de diagnostic | Robustesse, erreurs |
| FastAPI | API minimale | Tests, structure propre |
| Docker | Build et Compose | Volumes, réseau Docker |
| Sécurité | Lecture seule, prudence | Secrets, hardening |
| Documentation | README, docs, journal | Architecture plus visuelle |
| Automatisation | Makefile | CI, Ansible |

---

# Prochaines priorités

- Ajouter des tests pytest.
- Ajouter une CI GitHub Actions.
- Nettoyer le README si nécessaire.
- Préparer une documentation VPS séparée.
- Garder OpenAI API et OpenClaw en lecture seule au départ.

## Bilan du mois 1 — Stabilisation locale du projet

### Objectif du mois

L’objectif du premier mois était de stabiliser le dépôt, améliorer sa lisibilité et vérifier que le projet pouvait être reproduit sur une VM Fedora 44.

### Travail réalisé

- correction d’une incohérence entre le Makefile local et le Makefile visible sur GitHub ;
- amélioration des commandes Makefile ;
- vérification du lancement Docker Compose ;
- test des endpoints `/health`, `/version` et `/diag` ;
- amélioration du README ;
- ajout ou amélioration de la documentation technique ;
- documentation du mode lecture seule ;
- documentation de la reproduction sur Fedora 44.

### Ce que j’ai appris

- un projet peut fonctionner localement sans être correctement synchronisé avec GitHub ;
- une branche locale peut contenir des corrections absentes de `master` ;
- `git push origin master` envoie le `master` local vers GitHub ;
- `git pull --ff-only origin master` permet d’aligner l’historique local sans créer de commit de merge inattendu ;
- un Makefile rend un projet beaucoup plus facile à utiliser ;
- la reproductibilité est une compétence importante en DevOps ;
- documenter les erreurs permet de montrer une vraie progression.

### Difficultés rencontrées

- confusion entre branche locale et branche distante ;
- ancien nom de script encore présent sur GitHub ;
- compréhension des commits de merge ;
- vérification de la cohérence entre README, Makefile et scripts.

### Résultat obtenu

À la fin du mois 1, le projet est :
- clonable ;
- lançable localement ;
- testé manuellement ;
- documenté ;
- reproductible sur VM Fedora 44 ;
- prêt pour l’ajout de tests automatisés.

### Prochaine étape

Le mois 2 sera consacré à :
- ajouter `pytest` ;
- ajouter `ruff` ;
- vérifier les scripts Bash avec `shellcheck` ;
- ajouter une CI GitHub Actions ;
- préparer la version `v0.2.0`.

## Mois 2 — Semaine 1 — Premiers tests automatisés

Objectif de la semaine : ajouter des tests Python avec pytest pour vérifier automatiquement l’API FastAPI.

Ce que j’ai ajouté :
- un fichier `app/requirements-dev.txt` ;
- un dossier `app/tests/` ;
- des tests pour `/`, `/health`, `/version` et `/diag` ;
- une vraie commande `make test`.

Ce que j’ai appris :
- différence entre dépendances runtime et dépendances de développement ;
- rôle de `pytest` ;
- rôle de `TestClient` avec FastAPI ;
- importance de tester la structure des réponses JSON ;
- intérêt de lancer les tests avant chaque commit.

Difficultés rencontrées :
- import Python depuis la racine du projet ;
- distinction entre test manuel avec `curl` et test automatisé ;
- adaptation du Makefile.

Résultat :
- les tests peuvent être lancés avec `make test`.
