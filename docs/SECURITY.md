# Sécurité

## Données sensibles du projet

Sont sensibles :

- tokens Telegram ;
- sessions WhatsApp ;
- clés API IA ;
- fichiers `.env` réels ;
- clés SSH privées ;
- sauvegardes ;
- logs contenant des messages privés ;
- QR codes ;
- captures non floutées ;
- URL internes si elles révèlent l'infrastructure.

## Règles secrets

Ne jamais commiter de secret réel.
Utiliser uniquement les placeholders : `<votre_token>`, `<votre_cle>`, `<ip_du_serveur>`, `<utilisateur>`, `<URL_DU_DEPOT_GITHUB>`.

## `.env` local et `.env.example`

- `.env.example` est versionné et ne contient que des placeholders.
- `.env` est local, privé et ignoré par Git.
- Permissions recommandées :

```bash
chmod 600 .env
```

Résultat attendu : seul l'utilisateur courant peut lire le fichier.

## Sécurité VPS

- Utiliser un utilisateur non-root.
- Désactiver l'authentification SSH par mot de passe si possible.
- Utiliser UFW ou un firewall équivalent.
- Garder le système à jour.
- Ne pas exposer OpenClaw ou MCP publiquement.

## SSH et UFW

Exemples manuels :

```bash
ssh <utilisateur>@<ip_du_serveur>
ufw status verbose
```

Résultat attendu : SSH est autorisé, les services internes ne sont pas publics.

## OpenClaw et MCP non exposés publiquement

OpenClaw Gateway et MCP doivent écouter sur `127.0.0.1` ou un réseau privé contrôlé.
Éviter toute règle firewall publique vers ces ports.

## Exemple de tunnel SSH

Pour déboguer un service local du VPS sans l'exposer :

```bash
ssh -L 18789:127.0.0.1:18789 <utilisateur>@<ip_du_serveur>
```

Résultat attendu : le port distant reste privé et accessible seulement via le tunnel local.

## Permissions sur `~/.hermes` et `~/.openclaw`

```bash
chmod 700 ~/.hermes ~/.openclaw
find ~/.hermes ~/.openclaw -type f -exec chmod 600 {} \;
```

Résultat attendu : dossiers privés et fichiers non lisibles par d'autres utilisateurs.

## Limitation des outils MCP

- Autoriser seulement les actions nécessaires.
- Refuser les commandes système destructives.
- Éviter l'accès large au shell.
- Journaliser les erreurs techniques sans contenu privé.
- Revoir les allowlists avant chaque mise en production.

## Sécurité Docker si applicable

Docker Compose est optionnel pour le MVP.
Si utilisé :

- préférer `docker compose` ;
- éviter les conteneurs privilégiés ;
- monter seulement les volumes nécessaires ;
- ne pas stocker de secrets dans l'image ;
- ne pas commiter de volumes ou bases locales.

## Sécurité systemd

L'unité `hermes-openclaw-loop.service` est une unité utilisateur.
Elle ne contient pas de secrets.
Elle n'utilise pas `User=`.
Les secrets restent dans `.env` local ou dans le gestionnaire de secrets choisi plus tard.

## Sauvegardes chiffrées

Une sauvegarde peut contenir des secrets.
Elle doit être chiffrée avant stockage externe avec GPG ou age.
Ne jamais commiter `*.tar.gz`, `*.gpg`, `*.age` ou `backups/`.

## Règles pour captures d'écran

Avant publication :

- flouter IP ;
- flouter tokens ;
- flouter noms ;
- flouter messages privés ;
- flouter QR codes ;
- ne jamais publier une capture brute.

## Révocation token Telegram

Si un token Telegram fuit :

1. ouvrir BotFather ;
2. révoquer le token du bot concerné ;
3. générer un nouveau token ;
4. mettre à jour uniquement le `.env` local ;
5. redémarrer le service ;
6. vérifier l'historique Git et les logs ;
7. documenter l'incident dans `docs/incidents/` sans secret.

## Révocation clés API IA

Si une clé API fuit :

1. désactiver la clé dans le tableau de bord fournisseur ;
2. créer une nouvelle clé avec le minimum de droits ;
3. mettre à jour uniquement le `.env` local ;
4. redémarrer le service ;
5. vérifier la facturation et les usages ;
6. documenter l'incident sans divulguer la clé.

## Checklist avant publication GitHub

- [ ] `git status --short` relu.
- [ ] `git diff --check` sans erreur.
- [ ] Aucun `.env` réel suivi.
- [ ] Aucun token ou clé dans le diff.
- [ ] Aucune session WhatsApp.
- [ ] Aucune clé SSH privée.
- [ ] Aucune sauvegarde réelle.
- [ ] Aucun log privé.
- [ ] Captures floutées uniquement.
- [ ] README et docs cohérents avec `hermes-openclaw-loop.service`.
