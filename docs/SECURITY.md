# Sécurité Hermes + OpenClaw Gateway

## Données sensibles du projet

Sont sensibles : clés API, token Telegram, sessions WhatsApp, configuration `.env` réelle, clés SSH privées, sauvegardes, logs contenant des messages privés, QR codes et captures non floutées.

## Règles secrets

- Aucun secret réel dans Git.
- Utiliser uniquement des placeholders : `<votre_token>`, `<votre_cle>`, `<ip_du_serveur>`, `<utilisateur>`, `<URL_DU_DEPOT_GITHUB>`.
- Ne jamais publier de fichier `.env` réel.
- Ne jamais publier de session WhatsApp.
- Ne jamais publier de backup brut.

## `.env` local et `.env.example`

`.env.example` est versionnable car il contient seulement des placeholders. Le fichier `.env` local doit rester sur le VPS et être protégé :

```bash
chmod 600 .env
```

Résultat attendu : seul l'utilisateur applicatif lit le fichier local.

## Sécurité VPS

- Exploiter avec un utilisateur non-root.
- Garder le système à jour via une procédure de maintenance manuelle.
- Désactiver les accès inutiles.
- Limiter les ports ouverts.
- Surveiller disque, mémoire et journaux.

## SSH et UFW

```bash
# Commandes manuelles sur VPS.
ufw allow OpenSSH
ufw enable
ufw status verbose
```

Résultat attendu : SSH autorisé, autres ports fermés sauf besoin explicite.

## OpenClaw/MCP non exposés publiquement

OpenClaw Gateway et MCP doivent rester liés à `127.0.0.1` ou accessibles seulement via tunnel sécurisé. Ne pas exposer l'interface MCP sur Internet.

## Exemple de tunnel SSH

```bash
ssh -L 18789:127.0.0.1:18789 <utilisateur>@<ip_du_serveur>
```

Résultat attendu : accès local temporaire au gateway sans ouvrir de port public.

## Permissions sur `~/.hermes` et `~/.openclaw`

```bash
chmod 700 ~/.hermes ~/.openclaw
find ~/.hermes ~/.openclaw -type f -exec chmod 600 {} +
```

Résultat attendu : configurations et sessions lisibles uniquement par l'utilisateur.

## Limitation des outils MCP

- Autoriser seulement les outils nécessaires.
- Préférer la lecture d'événements et l'envoi de réponse.
- Refuser les outils shell dangereux.
- Éviter les outils donnant accès au système de fichiers entier.
- Auditer les allowlists avant mise en production.

## Sécurité Docker si applicable

Docker Compose est optionnel pour le MVP. Si Docker est utilisé :

- utiliser `docker compose` ;
- éviter les conteneurs privilégiés ;
- ne pas monter `/` ;
- limiter les volumes ;
- ne pas stocker de secrets dans les images ;
- vérifier les logs avant partage.

## Sécurité systemd

L'unité est une unité utilisateur. Elle ne contient pas `User=` et ne contient aucun secret. Les variables sensibles restent dans `.env` local ou dans l'environnement utilisateur.

## Sauvegardes chiffrées

Toute archive contenant `~/.openclaw`, `~/.hermes` ou `.env` doit être chiffrée avant stockage externe avec GPG ou age. Les archives brutes restent locales, temporaires et protégées par `chmod 600`.

## Règles pour captures d'écran

Avant publication :

- flouter IP ;
- flouter tokens ;
- flouter noms ;
- flouter messages privés ;
- flouter QR codes ;
- ne jamais publier une capture brute.

## Révocation token Telegram

1. Révoquer le token via l'interface BotFather.
2. Générer un nouveau token.
3. Mettre à jour uniquement le `.env` local.
4. Redémarrer le service utilisateur.
5. Vérifier les logs sans exposer le token.

## Révocation clés API

1. Révoquer la clé dans le portail du fournisseur IA.
2. Créer une nouvelle clé.
3. Mettre à jour le `.env` local.
4. Redémarrer `hermes-openclaw-loop.service`.
5. Vérifier la facturation et les quotas.

## Checklist avant publication GitHub

- [ ] `git status --short` compris.
- [ ] `git diff --check` sans erreur.
- [ ] Aucun `.env` réel suivi par Git.
- [ ] Aucun token Telegram.
- [ ] Aucune clé API.
- [ ] Aucune clé SSH privée.
- [ ] Aucune session WhatsApp.
- [ ] Aucune archive de sauvegarde.
- [ ] Aucun log privé.
- [ ] Captures floutées ou absentes.
- [ ] Grep de secrets exécuté.
