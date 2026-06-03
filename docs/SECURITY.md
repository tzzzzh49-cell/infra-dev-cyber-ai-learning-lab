# Sécurité

## Données sensibles du projet

Les données sensibles incluent :

- clés API IA ;
- token Telegram ;
- sessions WhatsApp ;
- fichiers `.env` réels ;
- clés SSH privées ;
- sauvegardes ;
- logs contenant des messages privés ;
- captures non floutées ;
- QR codes d'appairage.

## Règles secrets

- Ne jamais commiter de secret réel.
- Utiliser uniquement `<votre_token>`, `<votre_cle>`, `<ip_du_serveur>`, `<utilisateur>` et `<URL_DU_DEPOT_GITHUB>` dans la documentation.
- Révoquer immédiatement tout secret exposé.
- Vérifier le dépôt avant publication GitHub.

## `.env` local et `.env.example`

`.env.example` est versionné avec des placeholders.
`.env` reste local et doit avoir des permissions strictes :

```bash
chmod 600 .env
```

Résultat attendu : seul l'utilisateur courant peut lire le fichier.

## Sécurité VPS

- Utiliser Ubuntu 24.04 maintenu.
- Créer un utilisateur non-root.
- Désactiver l'accès SSH root si possible.
- Utiliser des clés SSH, pas de mot de passe.
- Appliquer les mises à jour de sécurité.

## SSH et UFW

Commandes manuelles typiques :

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Résultat attendu : seul SSH est exposé au départ.

## OpenClaw et MCP non exposés publiquement

OpenClaw Gateway et MCP doivent écouter sur `127.0.0.1` ou une interface privée.
N'ouvrez pas leurs ports sur Internet.
Si un accès temporaire est nécessaire, utilisez un tunnel SSH.

## Exemple de tunnel SSH

```bash
ssh -L 18789:127.0.0.1:18789 <utilisateur>@<ip_du_serveur>
```

Résultat attendu : le port distant reste privé, accessible localement via le tunnel.

## Permissions sur `~/.hermes` et `~/.openclaw`

```bash
chmod 700 ~/.hermes ~/.openclaw
find ~/.hermes ~/.openclaw -type f -exec chmod 600 {} \;
```

Résultat attendu : seuls les fichiers de l'utilisateur sont lisibles par lui.

## Limitation des outils MCP

- Activer seulement les outils nécessaires.
- Préférer des commandes en lecture quand c'est possible.
- Éviter les outils shell génériques.
- Journaliser les erreurs techniques, pas le contenu privé.

## Sécurité Docker si applicable

Docker est optionnel pour le MVP.
Si Docker est utilisé :

- préférer `docker compose` ;
- limiter les volumes montés ;
- éviter les conteneurs privilégiés ;
- ne pas stocker de secrets dans les images ;
- utiliser des fichiers `.env` locaux non versionnés.

## Sécurité systemd

L'unité `hermes-openclaw-loop.service` est une unité utilisateur.
Elle ne contient pas `User=` et ne contient aucun secret.
Elle pointe vers `%h/hermes-openclaw/scripts/loop.sh`.

## Sauvegardes chiffrées

Les sauvegardes peuvent contenir des secrets.
Elles ne doivent jamais être commitées.
Chiffrez avant stockage externe avec GPG ou age.

## Règles pour captures d'écran

Avant publication :

- flouter les IP ;
- flouter les tokens ;
- flouter les noms ;
- flouter les messages privés ;
- flouter les QR codes ;
- ne jamais publier une capture brute.

## Révocation token Telegram

1. Révoquer le token via BotFather.
2. Générer un nouveau token.
3. Mettre à jour uniquement le `.env` local.
4. Redémarrer `hermes-openclaw-loop.service`.
5. Vérifier l'historique Git et supprimer toute exposition publique si nécessaire.

## Révocation clés API

1. Révoquer la clé depuis le tableau de bord du fournisseur.
2. Générer une nouvelle clé.
3. Mettre à jour uniquement le `.env` local.
4. Redémarrer le service.
5. Contrôler les logs et la facturation.

## Checklist avant publication GitHub

- [ ] `git status --short` relu.
- [ ] `git diff --check` sans erreur.
- [ ] Aucun `.env` réel suivi.
- [ ] Aucun token ou clé API dans le dépôt.
- [ ] Aucun log privé.
- [ ] Aucune sauvegarde réelle.
- [ ] Aucune capture brute.
- [ ] `.env.example` contient seulement des placeholders.
