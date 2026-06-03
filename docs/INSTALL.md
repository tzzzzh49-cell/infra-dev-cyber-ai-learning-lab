# Installation manuelle sur VPS Ubuntu 24.04

Ce guide décrit les commandes à lancer manuellement sur un VPS.
Elles ne sont pas exécutées par l'agent de modification du dépôt.
Adaptez toujours les commandes à la documentation officielle OpenClaw et Hermes de la version installée.

## 1. Prérequis

- VPS Ubuntu 24.04 à jour.
- Accès SSH avec clé publique.
- Utilisateur non-root nommé ici `<utilisateur>`.
- Dépôt cloné depuis `<URL_DU_DEPOT_GITHUB>`.
- Aucun secret stocké dans Git.

Résultat attendu : vous pouvez ouvrir une session SSH avec `<utilisateur>` et travailler sans compte root direct.

## 2. Utilisateur non-root

Commandes manuelles à exécuter sur le VPS si l'utilisateur n'existe pas encore :

```bash
sudo adduser <utilisateur>
sudo usermod -aG sudo <utilisateur>
```

Résultat attendu : `<utilisateur>` peut administrer le VPS avec `sudo` si nécessaire.

## 3. SSH et UFW

Commandes manuelles typiques :

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Résultat attendu : SSH reste autorisé et le pare-feu est actif.
N'exposez pas OpenClaw ni MCP publiquement.

## 4. Docker Engine et Docker Compose v2

Docker est optionnel pour le MVP.
Il devient utile si plusieurs services persistants sont ajoutés.
Utilisez Docker Compose v2 avec la commande `docker compose`, pas `docker-compose`.

Commandes de vérification après installation manuelle selon la documentation officielle Docker :

```bash
docker --version
docker compose version
```

Résultat attendu : les deux commandes affichent une version et retournent un code de sortie 0.

## 5. Node.js LTS compatible avec OpenClaw

Installez une version Node.js LTS compatible avec la version OpenClaw utilisée.
Ne figez pas une version sans vérifier la documentation officielle OpenClaw.

Commandes de vérification :

```bash
node --version
npm --version
```

Résultat attendu : Node.js et npm répondent sans erreur.

## 6. Cloner le dépôt

```bash
cd ~
git clone <URL_DU_DEPOT_GITHUB> hermes-openclaw
cd ~/hermes-openclaw
```

Résultat attendu : le dépôt est disponible dans `~/hermes-openclaw`.

## 7. Configuration locale

```bash
cp .env.example .env
chmod 600 .env
```

Éditez `.env` localement avec vos vraies valeurs.
Ne commitez jamais `.env`.

Résultat attendu : `.env` existe uniquement sur la machine cible et reste privé.

## 8. Installation OpenClaw

Méthode principale à vérifier selon la version officielle OpenClaw :

```bash
# Exemple volontairement générique : consulter la documentation officielle OpenClaw.
openclaw --version
```

Résultat attendu après installation réelle : `openclaw --version` répond sans erreur.
Ne lancez pas d'onboarding réel sans avoir préparé les secrets localement.

## 9. Installation Hermes

Méthode principale à vérifier selon la version officielle Hermes :

```bash
# Exemple volontairement générique : consulter la documentation officielle Hermes.
hermes --version
```

Résultat attendu après installation réelle : `hermes --version` répond sans erreur.

## 10. Configuration MCP OpenClaw vers Hermes

Objectif : OpenClaw expose les événements de messagerie à MCP, puis Hermes utilise MCP pour lire le contexte et répondre.

À configurer manuellement selon les versions :

- URL locale OpenClaw : `http://127.0.0.1:18789`.
- Outils MCP autorisés au minimum nécessaire.
- Fournisseur IA et modèle via `.env` local.
- Aucun token dans les fichiers versionnés.

Résultat attendu : Hermes voit les outils MCP OpenClaw sans exposer OpenClaw sur Internet.

## 11. Test manuel Hermes

Commande manuelle de vérification non destructive :

```bash
hermes --version
```

Résultat attendu : la version Hermes s'affiche.
Un test conversationnel réel doit être fait seulement après configuration locale des secrets.

## 12. Test manuel OpenClaw

Commande manuelle de vérification non destructive :

```bash
openclaw gateway status
```

Résultat attendu : le statut de la gateway s'affiche si la commande existe dans la version installée.
Si la commande n'existe pas, utilisez l'équivalent documenté par OpenClaw.

## 13. Service systemd utilisateur

Commandes manuelles :

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hermes-openclaw-loop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-openclaw-loop.service
sudo loginctl enable-linger "$USER"
```

Résultat attendu : le service utilisateur démarre et redémarre automatiquement après reconnexion ou redémarrage.
`systemctl --user` accepte parfois le nom sans suffixe, mais la documentation utilise toujours `hermes-openclaw-loop.service`.

## 14. Commandes de vérification finales

```bash
systemctl --user status hermes-openclaw-loop.service
journalctl --user -u hermes-openclaw-loop.service -n 50 --no-pager
scripts/healthcheck.sh
```

Résultat attendu : service actif, journaux sans messages privés et healthcheck avec code de sortie 0.
