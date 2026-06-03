# Sécurité

## Données sensibles du projet

Sont sensibles :

- clés API IA ;
- token Telegram ;
- sessions WhatsApp et QR codes ;
- fichier `.env` réel ;
- clés SSH privées ;
- sauvegardes ;
- logs contenant messages privés ;
- captures non floutées ;
- configuration locale `~/.openclaw` et `~/.hermes`.

## Règles secrets

Ne jamais commiter :

- une valeur réelle de `OPENAI_API_KEY` ou `OPENROUTER_API_KEY` ;
- un `TELEGRAM_BOT_TOKEN` réel ;
- un fichier `.env` réel ;
- une session OpenClaw ou WhatsApp ;
- une clé privée ;
- une archive de sauvegarde ;
- un log privé.

Utiliser uniquement les placeholders `<votre_token>`, `<votre_cle>`,
`<ip_du_serveur>`, `<utilisateur>` et `<URL_DU_DEPOT_GITHUB>` dans la
documentation publique.

## `.env` local et `.env.example`

`.env.example` reste versionnable et contient seulement des placeholders.
Le fichier `.env` local doit être ignoré par Git et protégé :

```bash
cp .env.example .env
chmod 600 .env
```

Résultat attendu : seul l'utilisateur courant peut lire le fichier local.

## Sécurité VPS

- Utiliser un utilisateur non-root.
- Désactiver les accès inutiles.
- Mettre à jour le système régulièrement.
- Limiter les ports ouverts avec UFW.
- Ne pas exposer OpenClaw, Hermes ou MCP sur Internet.

## SSH et UFW

Commandes manuelles indicatives :

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Résultat attendu : SSH est autorisé, aucun port applicatif sensible n'est ouvert
publiquement.

## OpenClaw et MCP non exposés publiquement

OpenClaw Gateway et MCP doivent écouter en local, par exemple sur `127.0.0.1`.
Si un accès distant temporaire est nécessaire, utiliser un tunnel SSH.

Exemple de tunnel SSH :

```bash
ssh -L 18789:127.0.0.1:18789 <utilisateur>@<ip_du_serveur>
```

Résultat attendu : le port distant reste privé et accessible seulement depuis la
machine qui ouvre le tunnel.

## Permissions sur `~/.hermes` et `~/.openclaw`

```bash
chmod 700 ~/.hermes ~/.openclaw
find ~/.hermes ~/.openclaw -type f -exec chmod 600 {} \;
```

Résultat attendu : configurations et sessions locales lisibles uniquement par
l'utilisateur.

## Limitation des outils MCP

- Exposer uniquement les outils nécessaires à la lecture d'événements et à
  l'envoi de réponses.
- Interdire les outils shell génériques sauf besoin explicitement validé.
- Préférer des commandes idempotentes et non destructives.
- Journaliser des erreurs techniques, jamais le contenu privé.

## Sécurité Docker si applicable

Docker Compose v2 est optionnel pour le MVP.
S'il est utilisé :

- éviter les conteneurs privilégiés ;
- éviter le montage de `/` ;
- limiter les volumes aux données nécessaires ;
- ne pas stocker de secrets dans l'image ;
- utiliser `docker compose`, pas `docker-compose`.

## Sécurité systemd

L'unité fournie est une unité utilisateur.
Elle ne contient pas `User=` et ne contient aucun secret.
Les secrets restent dans l'environnement local ou dans un fichier non versionné
protégé.

## Sauvegardes chiffrées

Toute archive contenant `~/.openclaw`, `~/.hermes` ou `.env` doit être chiffrée
avant stockage externe avec GPG ou age. Une archive brute ne doit pas quitter le
VPS.

## Règles pour captures d'écran

Avant publication, flouter :

- IP ;
- tokens ;
- noms ;
- messages privés ;
- QR codes.

Ne jamais publier une capture brute.

## Révocation token Telegram

En cas de fuite :

1. Révoquer immédiatement le token via BotFather.
2. Générer un nouveau token.
3. Mettre à jour uniquement le `.env` local.
4. Redémarrer le service utilisateur.
5. Vérifier l'historique Git et les logs.

## Révocation clés API

En cas de fuite :

1. Révoquer la clé chez le fournisseur IA.
2. Créer une nouvelle clé avec le périmètre minimal.
3. Mettre à jour le `.env` local.
4. Surveiller la facturation et les usages.
5. Documenter l'incident sans secret dans `docs/incidents/`.

## Checklist avant publication GitHub

- [ ] `git status --short` ne montre pas de fichier secret.
- [ ] `.env` est absent du suivi Git.
- [ ] `.env.example` contient seulement des placeholders.
- [ ] Aucun token, clé ou QR code dans les captures.
- [ ] Aucun log privé dans le dépôt.
- [ ] Aucune archive de sauvegarde brute dans le dépôt.
- [ ] Les ports OpenClaw/MCP ne sont pas documentés comme publics.
- [ ] Le grep de secrets ne retourne rien de sensible.
