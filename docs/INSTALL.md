# Installation Hermes + OpenClaw Gateway sur Ubuntu 24.04

Ce guide décrit une installation cible sur VPS Ubuntu 24.04.
Les commandes sont à exécuter manuellement par l'administrateur du VPS.
Elles n'ont pas été lancées par l'agent de modification du dépôt.

## 1. Prérequis Ubuntu 24.04

Prévoir :

- un VPS Ubuntu Server 24.04 à jour ;
- un utilisateur non-root, par exemple `<utilisateur>` ;
- un accès SSH par clé ;
- Git ;
- Docker Engine et Docker Compose v2 si plusieurs services persistants sont
  ajoutés plus tard ;
- Node.js LTS compatible avec OpenClaw, sans figer une version non vérifiée ;
- OpenClaw et Hermes installés selon leurs documentations officielles.

Résultat attendu : le VPS est accessible, l'utilisateur non-root peut travailler
sans utiliser le compte `root` au quotidien.

## 2. Utilisateur non-root

Commande manuelle indicative :

```bash
adduser <utilisateur>
usermod -aG sudo <utilisateur>
```

Résultat attendu : l'utilisateur `<utilisateur>` existe et peut administrer le VPS
avec `sudo` lorsque c'est nécessaire.

## 3. SSH et UFW

Commandes manuelles indicatives :

```bash
ssh <utilisateur>@<ip_du_serveur>
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Résultat attendu : SSH reste autorisé, les autres ports ne sont pas ouverts par
défaut. OpenClaw et MCP ne doivent pas être exposés publiquement.

## 4. Docker Engine et Docker Compose v2

Docker Compose est optionnel pour le MVP Telegram si OpenClaw et Hermes tournent
comme processus locaux. Il devient utile si plusieurs services persistants sont
ajoutés : base locale, observabilité, gateway conteneurisée ou files de messages.

Commande de vérification manuelle :

```bash
docker --version
docker compose version
```

Résultat attendu : `docker compose` répond. Ne pas utiliser `docker-compose` dans
ce dépôt.

## 5. Node.js LTS compatible OpenClaw

OpenClaw peut dépendre d'un runtime Node.js selon sa distribution.
Installer une version LTS compatible avec la version officielle d'OpenClaw.
Ne pas figer une version ici sans vérification de la documentation officielle.

Commande de vérification manuelle :

```bash
node --version
npm --version
```

Résultat attendu : Node.js et npm répondent avec des versions LTS supportées par
OpenClaw.

## 6. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT_GITHUB> ~/hermes-openclaw
cd ~/hermes-openclaw
```

Résultat attendu : le dépôt est disponible dans `~/hermes-openclaw`.

## 7. Configuration locale `.env`

Créer un fichier local non versionné depuis l'exemple :

```bash
cp .env.example .env
chmod 600 .env
```

Remplacer uniquement dans `.env` les placeholders par les valeurs réelles.
Ne jamais commiter `.env`.

Résultat attendu : `.env` existe localement, avec permissions strictes, et reste
ignoré par Git.

## 8. Installation OpenClaw

Méthode principale : suivre la documentation officielle OpenClaw correspondant à
la version installée.

Commandes de vérification manuelle :

```bash
command -v openclaw
openclaw --help
```

Résultat attendu : la commande `openclaw` est trouvée et affiche son aide.

Note : les commandes d'onboarding, de connexion Telegram ou WhatsApp et les QR
codes ne doivent pas être exécutés automatiquement par ce dépôt.

## 9. Installation Hermes

Méthode principale : suivre la documentation officielle Hermes correspondant à la
version installée.

Commandes de vérification manuelle :

```bash
command -v hermes
hermes --version
```

Résultat attendu : la commande `hermes` est trouvée et affiche sa version.

## 10. Configuration MCP OpenClaw vers Hermes

Objectif : OpenClaw reçoit un événement, MCP expose les outils autorisés, Hermes
lit le contexte minimal et produit une réponse courte.

Exemple conceptuel à adapter selon les versions officielles :

```text
OpenClaw Gateway -> serveur MCP local -> Hermes Agent -> fournisseur IA
```

Résultat attendu : le pont MCP reste local, limité aux outils nécessaires, et
n'expose pas de port public.

## 11. Test manuel Hermes

Commande manuelle indicative, à adapter selon la CLI réelle :

```bash
hermes --version
```

Résultat attendu : Hermes répond sans contacter inutilement un modèle distant.
Pour un test LLM réel, vérifier le coût, le fournisseur et le modèle configurés.

## 12. Test manuel OpenClaw

Commande manuelle indicative, à adapter selon la CLI réelle :

```bash
openclaw gateway status
```

Résultat attendu : la gateway indique un état lisible. Aucun message privé ne doit
être copié dans les logs du dépôt.

## 13. Service systemd utilisateur

Installer l'unité utilisateur :

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hermes-openclaw-loop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-openclaw-loop.service
sudo loginctl enable-linger "$USER"
```

Résultat attendu : le service `hermes-openclaw-loop.service` est activé pour
l'utilisateur courant. `systemctl --user status hermes-openclaw-loop` peut aussi
fonctionner car systemd accepte souvent le nom sans suffixe `.service`.

## 14. Vérifications finales

```bash
scripts/healthcheck.sh
systemctl --user status hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
```

Résultat attendu : le healthcheck termine avec code 0 lorsque OpenClaw, Hermes et
le service utilisateur sont disponibles. Les logs ne doivent pas contenir de
messages privés.
