# Installation Hermes + OpenClaw Gateway

Ce guide décrit une installation manuelle sur VPS Ubuntu 24.04. Les commandes sont fournies pour l'opérateur humain. Elles n'ont pas été exécutées sur un VPS par l'agent de modification du dépôt.

## Pré-requis Ubuntu 24.04

- VPS Ubuntu 24.04 à jour.
- Accès SSH sécurisé.
- Utilisateur non-root avec droits d'administration.
- Git.
- Curl.
- Node.js LTS compatible avec OpenClaw.
- Docker Engine et Docker Compose v2 si plusieurs services persistants sont ajoutés.

Résultat attendu : le VPS est accessible, stable et administré depuis un compte non-root.

## Utilisateur non-root

Créer ou utiliser un utilisateur applicatif, par exemple `<utilisateur>`.

```bash
# Commandes manuelles à exécuter sur le VPS si nécessaire.
# Adapter l'utilisateur selon votre contexte.
adduser <utilisateur>
usermod -aG sudo <utilisateur>
```

Résultat attendu : l'exploitation quotidienne ne se fait pas avec `root`.

## SSH et UFW

Recommandations :

```bash
# Commandes manuelles à exécuter sur le VPS.
ssh <utilisateur>@<ip_du_serveur>
ufw allow OpenSSH
ufw enable
ufw status verbose
```

Résultat attendu : SSH reste autorisé et le pare-feu limite l'exposition réseau.

## Docker Engine et Docker Compose v2

Docker Compose est optionnel pour le MVP. Il devient utile si OpenClaw, Hermes, une base locale ou un service de monitoring doivent tourner comme services persistants.

Utiliser la syntaxe moderne :

```bash
docker compose version
docker compose config
```

Résultat attendu : la commande `docker compose` existe. Ne pas utiliser `docker-compose` dans ce projet.

## Node.js LTS compatible OpenClaw

Installer une version LTS compatible avec la version officielle d'OpenClaw utilisée. Ne pas figer une version sans vérifier la documentation officielle du moment.

```bash
node --version
npm --version
```

Résultat attendu : Node.js et npm répondent. La version est compatible avec OpenClaw.

## Cloner le dépôt

```bash
git clone <URL_DU_DEPOT_GITHUB> ~/hermes-openclaw
cd ~/hermes-openclaw
cp .env.example .env
chmod 600 .env
```

Résultat attendu : le dépôt est dans `~/hermes-openclaw` et le fichier `.env` local n'est pas versionné.

## Variables locales

Éditer `.env` localement avec des valeurs réelles uniquement sur le VPS :

```bash
OPENAI_API_KEY="<votre_cle>"
OPENROUTER_API_KEY="<votre_cle>"
TELEGRAM_BOT_TOKEN="<votre_token>"
HERMES_PROVIDER="<provider>"
HERMES_MODEL="<modele>"
OPENCLAW_GATEWAY_URL="http://127.0.0.1:18789"
```

Résultat attendu : les secrets restent hors Git.

## Installation OpenClaw

Méthode principale : suivre la documentation officielle OpenClaw de la version installée.

À vérifier selon version officielle :

```bash
# Exemple de contrôle manuel après installation.
command -v openclaw
openclaw --version
openclaw gateway status
```

Résultat attendu : la commande `openclaw` existe et le gateway peut être contrôlé localement.

## Installation Hermes

Méthode principale : suivre la documentation officielle Hermes de la version installée.

À vérifier selon version officielle :

```bash
# Exemple de contrôle manuel après installation.
command -v hermes
hermes --version
```

Résultat attendu : la commande `hermes` existe et l'agent peut être lancé en mode requête.

## Configuration MCP OpenClaw vers Hermes

Principe : OpenClaw expose ou pilote les événements de messagerie. MCP limite les actions disponibles. Hermes lit le contexte via MCP et renvoie une réponse à OpenClaw.

Points à configurer manuellement :

- URL locale OpenClaw : `http://127.0.0.1:18789`.
- Outils MCP autorisés en lecture/écriture minimale.
- Canal Telegram activé avant WhatsApp.
- Aucun outil MCP dangereux.
- Aucun endpoint OpenClaw/MCP exposé publiquement.

Résultat attendu : Hermes peut demander à MCP de lire un événement et de proposer une réponse, sans accès système non nécessaire.

## Test manuel Hermes

```bash
# Commande illustrative. Adapter selon la CLI Hermes officielle.
hermes --version
hermes run --once --prompt "Réponds en une phrase courte : test local."
```

Résultat attendu : Hermes répond localement. Ne pas conclure que le canal Telegram fonctionne avec ce test seul.

## Test manuel OpenClaw

```bash
# Commandes illustratives. Adapter selon la CLI OpenClaw officielle.
openclaw --version
openclaw gateway status
```

Résultat attendu : OpenClaw indique un gateway local actif ou fournit une erreur exploitable.

## Service systemd utilisateur

Installer l'unité utilisateur :

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hermes-openclaw-loop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-openclaw-loop.service
sudo loginctl enable-linger "$USER"
```

Résultat attendu : `hermes-openclaw-loop.service` démarre dans la session utilisateur. `systemctl --user status hermes-openclaw-loop` peut aussi fonctionner sans suffixe `.service`.

## Vérifications finales

```bash
git status --short
./scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service --since "15 minutes ago"
```

Résultats attendus : dépôt propre, commandes disponibles, service actif, logs sans secrets et sans contenu de messages privés.
