# Installation Hermes + OpenClaw Gateway

Ce guide décrit une installation cible sur VPS Ubuntu 24.04.
Les commandes sont à exécuter manuellement par l'administrateur du VPS.
Elles n'ont pas été exécutées par l'agent de modification du dépôt.

## 1. Prérequis Ubuntu 24.04

Prévoir :

- VPS Ubuntu 24.04 à jour ;
- accès SSH avec clé ;
- utilisateur non-root ;
- Git ;
- curl ;
- Docker Engine si nécessaire ;
- Docker Compose v2 via la commande `docker compose` ;
- Node.js LTS compatible avec OpenClaw ;
- OpenClaw ;
- Hermes.

Résultat attendu : le serveur accepte une connexion SSH par clé et l'utilisateur courant peut gérer les fichiers du projet dans son `$HOME`.

## 2. Utilisateur non-root

Exemple manuel, à adapter :

```bash
ssh <utilisateur>@<ip_du_serveur>
whoami
id
```

Résultat attendu : `whoami` affiche un utilisateur non-root.

## 3. SSH et UFW

Exemples manuels, à adapter à la politique du VPS :

```bash
ssh <utilisateur>@<ip_du_serveur>
ufw status
```

Résultat attendu : seul SSH est exposé au minimum.
OpenClaw et MCP ne doivent pas être ouverts publiquement.

Commandes d'administration possibles, à lancer uniquement après vérification humaine :

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Résultat attendu : UFW est actif et SSH reste accessible.

## 4. Docker Engine et Docker Compose v2

Docker Compose est optionnel pour le MVP.
Il devient utile si plusieurs services persistants sont ajoutés plus tard.
Utiliser la commande moderne :

```bash
docker compose version
```

Résultat attendu : une version de Docker Compose v2 s'affiche.

Ne pas utiliser `docker-compose` dans ce dépôt.

## 5. Node.js LTS compatible OpenClaw

Installer une version LTS compatible avec la documentation officielle OpenClaw du moment.
Ne pas figer une version dans ce dépôt sans validation officielle.

Vérification manuelle :

```bash
node --version
npm --version
```

Résultat attendu : Node.js et npm répondent sans erreur.

## 6. Récupérer le dépôt

```bash
git clone <URL_DU_DEPOT_GITHUB> ~/hermes-openclaw
cd ~/hermes-openclaw
git status --short
```

Résultat attendu : le dépôt est propre après clonage.

## 7. Configuration locale

Créer un fichier `.env` local à partir de l'exemple.
Ne jamais commiter `.env`.

```bash
cp .env.example .env
chmod 600 .env
```

Éditer ensuite les valeurs localement avec des secrets réels uniquement sur le VPS.

Résultat attendu : `.env` existe localement, est privé, et reste ignoré par Git.

## 8. Installation OpenClaw

Méthode principale à vérifier selon la version officielle OpenClaw :

```bash
openclaw --version
openclaw gateway status
```

Si OpenClaw n'est pas installé, suivre la documentation officielle OpenClaw correspondant à la version cible.
Ne pas exposer la gateway sur Internet.

Résultat attendu après installation : la commande `openclaw` existe et la gateway peut afficher un statut local.

## 9. Installation Hermes

Méthode principale à vérifier selon la version officielle Hermes :

```bash
hermes --version
```

Si Hermes n'est pas installé, suivre la documentation officielle Hermes correspondant à la version cible.
Configurer le fournisseur IA via `.env` local.

Résultat attendu après installation : la commande `hermes` existe et affiche sa version.

## 10. Configuration MCP OpenClaw vers Hermes

Objectif : OpenClaw reçoit un événement, MCP expose un pont local, Hermes lit le contexte autorisé et produit une réponse courte.

Principes :

- MCP écoute uniquement en local ;
- aucune clé dans un fichier versionné ;
- outils MCP limités aux actions nécessaires ;
- logs sans messages privés ;
- permissions strictes sur `~/.openclaw` et `~/.hermes`.

Exemple de variables locales :

```bash
OPENCLAW_GATEWAY_URL="http://127.0.0.1:18789"
HERMES_PROVIDER="<provider>"
HERMES_MODEL="<modele>"
```

Résultat attendu : Hermes connaît l'URL locale OpenClaw et le modèle configuré.

## 11. Test manuel Hermes

Commande indicative à vérifier selon la version officielle Hermes :

```bash
hermes --version
```

Résultat attendu : sortie de version et code retour `0`.

Un test de génération réel peut coûter de l'argent et nécessite des secrets locaux.
Il doit être lancé uniquement après validation humaine.

## 12. Test manuel OpenClaw

Commande indicative à vérifier selon la version officielle OpenClaw :

```bash
openclaw gateway status
```

Résultat attendu : statut local lisible, sans exposer de secret.

## 13. Installer le service systemd utilisateur

Le service est une unité utilisateur.
Il n'utilise pas `User=`.
Il utilise `%h` pour le dossier personnel.

Commandes manuelles demandées :

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hermes-openclaw-loop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-openclaw-loop.service
sudo loginctl enable-linger "$USER"
```

Résultat attendu : `hermes-openclaw-loop.service` est activé pour l'utilisateur courant.
`systemctl --user status hermes-openclaw-loop` peut aussi fonctionner car systemctl accepte souvent le nom sans suffixe.

## 14. Vérifications finales

```bash
scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
git status --short
```

Résultats attendus :

- healthcheck lisible ;
- service actif ou erreur exploitable ;
- logs sans messages privés ;
- aucun secret ou fichier local sensible suivi par Git.
