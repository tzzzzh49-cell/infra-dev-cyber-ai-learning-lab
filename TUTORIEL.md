# Tutoriel de prise en main

Ce tutoriel explique comment utiliser ce dépôt pour apprendre avec le guide,
construire le lab et produire une preuve GitHub vérifiable.

La commande principale est :

```bash
make learn
```

Le cockpit te montre une seule étape à la fois. Tu n'as donc pas besoin de
mémoriser tout le fonctionnement du dépôt avant de commencer.

## Démarrage express

Si tu veux aller directement à l'essentiel :

1. ouvre un terminal dans le dépôt ;
2. lance `make learn` ;
3. réponds aux questions de configuration du premier lancement ;
4. complète uniquement la rubrique ouverte dans `learner.md` ;
5. relance `make learn` après chaque action proposée.

Le reste de ce tutoriel explique ces étapes et les garde-fous associés.

## 1. Les règles essentielles

Avant toute manipulation, retiens ces six règles :

1. Le guide actif dans `curriculum/` est l'unique source d'apprentissage.
2. Tu écris toi-même toutes les réponses de ton fichier `learner.md`.
3. Tu fais une prévision avant de modifier le lab.
4. Tu exécutes une seule commande logique à la fois et tu observes son résultat.
5. Tu ne valides jamais une journée uniquement parce qu'une commande fonctionne.
6. Tu n'exécutes aucune action destructive, privilégiée ou facturable sans
   vérifier la cible, les conséquences et le retour arrière.

> Ce dépôt est public. Tout fichier, commit, issue et historique poussé sur
> GitHub doit être considéré comme visible par tous. Utilise uniquement les
> alias du lab et conserve secrets, preuves brutes, adresses réelles, noms DNS
> réels et chemins personnels hors du dépôt.

La fiche RNCP du site France Compétences ne doit pas être utilisée pour
compléter le guide. Si tu consultes une solution, une démonstration ou une autre
source, la tentative devient un entraînement non créditable. Le cockpit permet
ensuite de recommencer proprement depuis le guide.

Le parcours compte 370 journées principales et 20 consolidations. Une seule
journée est active à la fois et la durée de deux heures est un repère, pas une
limite. La progression publique n'est ni une note, ni une certification.

> État actuel du dépôt : seule la phase 0, de J001 à J010, est activée. Le
> cockpit refusera d'ouvrir une phase future tant que son audit et son
> versionnement ne seront pas terminés.

## 2. Ce qu'il faut préparer

Place-toi à la racine du dépôt :

```bash
cd /opt/infra-dev-cyber-ai-learning-lab
```

Le premier `make learn` vérifie notamment :

- Git et la visibilité publique du dépôt GitHub ;
- GitHub CLI avec une session active ;
- un éditeur de texte ;
- une signature Git personnelle ;
- `age` et GNU tar avec la prise en charge de Zstandard ;
- trois alias SSH pseudonymes pour Fedora, Ubuntu et le VPS ;
- deux emplacements de preuve chiffrée hors du dépôt et placés sur deux systèmes
  de fichiers distincts.

La configuration locale est enregistrée dans `.learning/local.json`. Ce fichier
est ignoré par Git et ne doit contenir ni clé privée, ni adresse réelle, ni
secret.

Au premier lancement, prépare :

- les alias de tes machines, par exemple `fedora-lab`, `ubuntu-lab` et
  `vps-lab` ;
- une clé publique `age` dédiée commençant par `age1` ;
- un dossier principal hors du dépôt pour les preuves chiffrées ;
- un second dossier sur un support ou système de fichiers distinct.

Pour afficher le diagnostic complet sans démarrer une journée :

```bash
make learn-doctor
```

Lis chaque ligne en erreur, corrige seulement le prérequis indiqué, puis relance
la même commande. La procédure détaillée pour la signature personnelle se trouve
dans [`docs/learning-cockpit.md`](docs/learning-cockpit.md).

## 3. Démarrer ou reprendre une journée

Dans un terminal interactif, lance :

```bash
make learn
```

Cette commande reprend automatiquement la journée active. Elle affiche :

- le numéro et le titre de la journée ;
- la progression, qui n'est pas une note ;
- l'objectif observable ;
- le garde-fou ;
- la prochaine rubrique ou commande à traiter.

Le cockpit ouvre ensuite le fichier suivant à la bonne rubrique :

```text
learning/days/JNNN/learner.md
```

`JNNN` représente la journée active, par exemple `J001`.

Si tu veux seulement afficher l'étape sans ouvrir l'éditeur :

```bash
python3 tools/learn.py run --no-editor
```

Pour afficher davantage de contexte provenant de la fiche active :

```bash
python3 tools/learn.py run --details
```

## 4. Utiliser le professeur Codex

Lorsque le menu du cockpit apparaît, appuie sur `c` pour lancer le professeur
Codex. Le cockpit lui transmet la journée, la référence exacte du guide et la
rubrique attendue.

Si tu ouvres Codex toi-même, demande explicitement :

```text
Utilise $aegis-professor pour reprendre ma journée active.
```

Le professeur peut :

- reformuler l'objectif du guide ;
- expliquer une option avant son premier usage ;
- poser une question courte ;
- lire des informations en lecture seule ;
- donner un indice après une erreur.

Le professeur ne doit pas rédiger `learner.md`, décider de ton statut ou
exécuter à ta place les mutations du lab.

## 5. Le cycle simple d'une journée

Une journée suit toujours le même enchaînement.

### Étape A — Lire avant d'agir

Lis l'objectif, la cible, le garde-fou et le rollback demandé. Ne modifie encore
rien.

### Étape B — Écrire ta prévision

Complète `Ma prévision` avec ce que tu penses observer et pourquoi. Écris avec
tes propres mots. Il n'est pas nécessaire d'avoir raison : la comparaison entre
ta prévision et le résultat fait partie de l'apprentissage.

Relance ensuite :

```bash
make learn
```

Le cockpit prépare le premier jalon Git, appelé `prediction`.

### Étape C — Suivre une commande à la fois

Le cockpit affiche une commande provenant de la fiche active. Avant de
l'exécuter :

1. identifie sa cible ;
2. explique les options nouvelles ;
3. vérifie si elle modifie quelque chose ;
4. rappelle le rollback prévu.

Exécute la commande toi-même, observe la sortie et son code retour, puis écris
le résultat utile dans `Mes observations`. Ne copie pas une transcription
complète du terminal.

Relance `make learn` après chaque étape. Le cockpit ne passe à la commande
suivante que lorsque la rubrique attendue a été complétée.

### Étape D — Expliquer et tester

Complète progressivement les rubriques demandées :

- `Mon explication` ;
- `Test positif` ;
- `Refus attendu` ;
- `Rollback` ;
- `Erreur utile`, si une erreur significative a été corrigée ;
- `Synthèse personnelle sans notes` ;
- les résumés et assertions destinés à la publication.

Le guide indique si un test, un refus ou un rollback est obligatoire, pertinent
ou non applicable pour la journée.

Quand les commandes et rubriques requises sont terminées, le cockpit prépare le
jalon `attempt`. Ce commit inclut le journal et les livrables du lab prévus par
la journée.

### Étape E — Choisir ton statut

Tu es la seule personne autorisée à choisir le statut du journal :

- `En cours` : tu continues normalement ;
- `À reprendre` : le résultat doit être retravaillé ;
- `Bloqué` : tu ne peux plus progresser proprement ;
- `Validé` : tu sais refaire et expliquer ce qui était demandé.

Écrire `Statut: Validé` ne suffit pas à terminer la journée. Il faut aussi une
CI conforme et une revue Codex `ready`.

### Étape F — Sceller le résultat final

Après ton verdict, la preuve et la revue, le cockpit prépare le jalon `final`.
La chaîne Git attendue est directe :

```text
baseline → prediction → attempt → final
```

Cette chaîne permet de distinguer ce que tu avais prévu, ce que tu as réellement
fait et le résultat que tu as décidé de présenter.

## 6. Exécuter les commandes Git proposées

Le cockpit ne cache pas les mutations Git. Il affiche une seule commande à la
fois, généralement dans cet ordre :

```text
git add ...
git commit ...
git push ...
```

Exécute exactement la commande affichée, puis relance :

```bash
make learn
```

Ne crée pas de commit intermédiaire entre deux jalons et ne modifie pas le plan
de checkpoint. La branche quotidienne doit être fusionnée sans squash afin de
préserver les trois jalons.

Le cockpit crée ou réconcilie l'issue, la branche quotidienne et la draft PR.
La journée suivante reste verrouillée tant que la PR n'est pas fusionnée et que
les trois conditions suivantes ne sont pas réunies :

- ton statut est `Validé` ;
- la CI est `Conforme` ;
- la revue Codex est `ready`.

## 7. Comprendre le menu

Lorsque le cockpit attend une décision, les raccourcis principaux sont :

| Touche | Action |
| --- | --- |
| `Entrée` | Ouvrir le journal à la rubrique attendue |
| `c` | Lancer le professeur Codex |
| `d` | Afficher les détails de la fiche |
| `p` | Mettre la séance en pause |
| `a` | Déclarer l'usage d'une aide extérieure |
| `b` | Archiver une preuve brute chiffrée |
| `r` | Recommencer une tentative uniquement depuis le guide |
| `u` | Rouvrir un jalon final devenu obsolète |

Déclarer une aide extérieure avec `a` ne supprime rien. La tentative est classée
comme entraînement. L'option `r` archive ensuite ce travail et crée une branche
propre depuis la baseline antérieure.

## 8. Conserver une preuve brute

Une preuve brute peut être un fichier de résultat utile produit pendant le lab.
Pour l'archiver, utilise l'option `b` du menu et indique son chemin.

Le cockpit :

1. crée une archive chiffrée ;
2. l'enregistre dans les deux stockages configurés hors du dépôt ;
3. vérifie les deux empreintes ;
4. conserve seulement un identifiant opaque et un SHA-256 dans Git.

Ne place jamais dans Git une clé privée, un jeton, une adresse réelle, une
archive brute ou une transcription complète du terminal.

## 9. Que faire en cas de problème ?

### Le premier lancement est refusé

Exécute :

```bash
make learn-doctor
```

Corrige uniquement les contrôles marqués comme bloquants. Ne désactive pas un
garde-fou pour faire disparaître l'erreur.

### Je suis bloqué depuis 30 minutes

Arrête les changements. Conserve l'erreur exacte, écris trois hypothèses et
choisis `Statut: Bloqué`. Le parcours activera une journée de consolidation sans
donner de crédit à une solution extérieure.

### J'ai utilisé une solution ou une autre source

Relance `make learn`, choisis `a`, puis utilise `r` lorsque tu es prêt à
recommencer uniquement depuis le guide.

### Mon final est devenu obsolète

Utilise l'option `u` ou la commande affichée par le cockpit :

```bash
python3 tools/learn.py reopen-final JNNN
```

Remplace `JNNN` par la journée active. N'efface pas manuellement les anciens
commits ou les reçus de réouverture.

### J'ai fermé le terminal ou perdu le cache local

Relance simplement :

```bash
make learn
```

La progression est reconstruite depuis les preuves versionnées et les branches
distantes valides.

### Git affiche des changements inattendus

Commence par une observation sans mutation :

```bash
git status --short
```

Ne lance ni reset destructif, ni suppression en masse. Identifie d'abord les
fichiers et demande de l'aide si leur origine n'est pas claire.

## 10. Exemple : commencer J001

La première journée active porte sur le périmètre, les règles de sécurité et la
baseline du lab.

1. Lance `make learn`.
2. Lis l'objectif et le garde-fou affichés.
3. Écris ta prévision avant toute modification.
4. Observe autant que possible Fedora, Ubuntu, le VPS et le dépôt en lecture
   seule.
5. Suis les commandes de la fiche une par une.
6. Produis les livrables demandés par J001 sans inventer de critère absent du
   guide.
7. Explique tes observations, ton test et ton rollback.
8. Choisis toi-même le statut de la journée.
9. Exécute les commandes Git proposées et relance `make learn` après chacune.

Le tutoriel ne fournit volontairement aucune réponse à J001 : la preuve doit
venir de ton observation et de ton explication.

## 11. Où trouver les informations ?

| Besoin | Fichier ou commande |
| --- | --- |
| Commencer ou reprendre | `make learn` |
| Diagnostiquer les prérequis | `make learn-doctor` |
| Guide actif | [`curriculum/active.json`](curriculum/active.json) |
| Fiche pédagogique | [`Guide_370_jours_RNCP41996_Secure_AI_Ops_pas_a_pas.md`](curriculum/v2.1.0/Guide_370_jours_RNCP41996_Secure_AI_Ops_pas_a_pas.md) |
| Journal de la journée | `learning/days/JNNN/learner.md` |
| Vue des 390 journées | [`learning/roadmap.md`](learning/roadmap.md) |
| Correspondance guide/lab | [`learning/lab-map.yml`](learning/lab-map.yml) |
| Aide technique du dépôt | `make help-dev` |
| Contrat technique du cockpit | [`docs/learning-cockpit.md`](docs/learning-cockpit.md) |

Les fichiers `.proof/`, les outils du cockpit, le guide et les workflows sont
des mécanismes de contrôle. Ne les modifie pas pendant une journée
d'apprentissage.

## 12. Checklist de fin de séance

Avant de fermer le terminal, vérifie :

- [ ] J'ai écrit avec mes propres mots.
- [ ] J'ai utilisé uniquement le guide pour la tentative créditable.
- [ ] J'ai expliqué la cible et les options avant l'action.
- [ ] J'ai conservé le résultat utile sans copier tout le terminal.
- [ ] J'ai testé le résultat et le rollback lorsque la fiche le demande.
- [ ] J'ai déclaré toute aide extérieure.
- [ ] J'ai exécuté uniquement les commandes Git proposées.
- [ ] J'ai relancé `make learn` pour enregistrer l'état courant.

Pour reprendre plus tard, une seule commande suffit :

```bash
make learn
```
