# Carte du dépôt

Cette page répond à une seule question : **où aller selon ce que je veux
faire ?** Le dépôt réunit un parcours d'apprentissage et le lab technique
construit pendant ce parcours. Ces deux axes sont liés, mais ils ne jouent pas
le même rôle.

## Les trois zones à retenir

| Zone | Rôle | Entrée principale |
| --- | --- | --- |
| Apprentissage | guide, progression et preuves | `make learn` |
| Lab technique | application, infrastructure et exploitation | `make help-dev` |
| Références | architecture, sécurité et procédures | [`docs/README.md`](README.md) |

## Rôle de chaque emplacement

| Emplacement | Contenu | À utiliser quand… |
| --- | --- | --- |
| `curriculum/` | versions immuables du guide et manifeste actif | tu consultes la source pédagogique officielle |
| `learning/` | roadmap, correspondance guide–lab, modèles et journées | tu suis ta progression ou produis une preuve |
| `app/` | API FastAPI et tests Python | tu développes ou testes le service de diagnostic |
| `compose*.yaml` | assemblage local et exposition publique | tu démarres les services du lab |
| `ansible/` | inventaire et automatisation Ansible | tu automatises une configuration système |
| `nginx/` | reverse proxy, OIDC et mTLS | tu travailles sur l'accès HTTPS au service |
| `systemd/` | unité de service du proxy public | tu intègres le lab au système du VPS |
| `backup/` | scripts Restic versionnés | tu configures ou testes la sauvegarde |
| `scripts/` | commandes opérateur et contrôles ciblés | tu installes, diagnostiques ou vérifies le lab |
| `tools/` | moteur interne du cockpit et de la publication | tu maintiens l'outillage pédagogique |
| `outputs/` | rapports, logs et sauvegardes générés localement | tu consultes un résultat d'exécution ; le contenu n'est pas versionné |
| `docs/` | documentation humaine et runbooks | tu cherches une explication ou une procédure |
| `site/` | gabarit de la preuve publique | tu maintiens la publication des preuves |
| `.github/` | CI, sécurité et publication | tu maintiens l'automatisation GitHub |
| `.codex/` | skill pédagogique Aegis Professor | tu maintiens le mode professeur |

## Les distinctions qui évitent les confusions

### `curriculum/` et `learning/`

- `curriculum/` dit **quoi apprendre**. `active.json` désigne l'unique version
  active ; les anciennes versions restent historiques.
- `learning/` dit **où tu en es** et comment relier le guide au lab. La journée
  courante vit sous `learning/days/<JOUR>/`.

### `backup/` et `outputs/backups/`

- `backup/` contient le code des opérations Restic ; il est versionné.
- `outputs/backups/` reçoit les données produites ; elles restent locales et
  hors Git.

### `scripts/` et `tools/`

- `scripts/` contient des actions techniques que l'opérateur peut lancer.
- `tools/` contient la mécanique interne du parcours ; elle n'est normalement
  pas nécessaire pour réaliser une journée.

### `docs/` et `learning/days/`

- `docs/` explique le projet de façon durable.
- `learning/days/` contient le travail et les preuves propres à une journée.

## Trois parcours de navigation

### Apprendre

1. Lancer `make learn`.
2. Modifier uniquement le `learner.md` ouvert par le cockpit.
3. Relancer `make learn` après l'action demandée.

Le [tutoriel](../TUTORIEL.md) détaille le premier lancement. La
[roadmap](../learning/roadmap.md) donne la vue d'ensemble sans remplacer le
guide actif.

### Comprendre le lab

1. Lire l'[architecture](architecture.md).
2. Consulter le [sommaire technique](README.md).
3. Ouvrir seulement le composant concerné dans `app/`, `ansible/`, `nginx/`,
   `backup/` ou `systemd/`.

### Développer ou exploiter

1. Lancer `make help-dev` pour choisir une commande supportée.
2. Effectuer le changement dans le dossier propriétaire du composant.
3. Vérifier avec `make check` ; réserver `make check-full` aux contrôles lourds.

## Règle pour les futurs ajouts

Avant de créer un nouvel élément à la racine, vérifier s'il appartient déjà à
une zone existante :

- code applicatif → `app/` ;
- automatisation opérateur → `scripts/` ou le dossier technique concerné ;
- documentation durable → `docs/` ;
- travail d'une journée → `learning/days/` ;
- sortie générée → `outputs/` ;
- source pédagogique officielle → `curriculum/`.

Un nouveau dossier racine doit représenter une responsabilité durable, être
référencé ici et avoir un propriétaire clair. Cette règle permet au lab de
grandir sans rendre sa navigation plus difficile.
