# Sauvegarde et restauration

## Quoi sauvegarder

Sauvegarder prudemment :

- `~/.openclaw` si le dossier existe ;
- `~/.hermes` si le dossier existe ;
- le dépôt local `~/hermes-openclaw` ;
- le fichier `.env` local ;
- l'unité systemd utilisateur
  `~/.config/systemd/user/hermes-openclaw-loop.service`.

## Quoi ne jamais mettre dans Git

Ne jamais commiter : `.env`, tokens, clés API, sessions WhatsApp, clés SSH
privées, logs privés, bases locales, archives, checksums de sauvegardes réelles,
fichiers `.gpg` ou `.age`.

## Fréquence recommandée

- Après chaque changement de configuration : sauvegarde manuelle.
- Chaque semaine : sauvegarde planifiée.
- Avant migration VPS : sauvegarde complète et test de restauration.
- Après rotation de token : nouvelle sauvegarde chiffrée.

## Sauvegarde OpenClaw CLI si disponible

Si OpenClaw fournit une commande officielle d'export ou de backup, la préférer.
Vérifier la documentation officielle et ne pas publier le résultat dans Git.

Commande conceptuelle à adapter :

```bash
openclaw backup --help
```

Résultat attendu : confirmer si une méthode officielle existe avant de l'utiliser.

## Script de sauvegarde complet

Le script exemple est fourni dans `scripts/backup-example.sh`.
Il crée une archive locale dans `~/backups`, inclut seulement les chemins
existants, génère un checksum SHA-256 et applique `chmod 600`.

Commande manuelle :

```bash
scripts/backup-example.sh
```

Résultat attendu : une archive `.tar.gz` et un fichier `.sha256` sont créés
localement. Ils ne sont pas transférés automatiquement.

## Checksum SHA-256

Vérifier une archive :

```bash
sha256sum -c ~/backups/<archive>.sha256
```

Résultat attendu : le checksum est `OK`.

## Permissions strictes

```bash
chmod 700 ~/backups
chmod 600 ~/backups/*.tar.gz ~/backups/*.sha256
```

Résultat attendu : seul l'utilisateur courant peut lire les sauvegardes.

## Chiffrement GPG ou age

Exemple GPG :

```bash
gpg --symmetric --cipher-algo AES256 ~/backups/<archive>.tar.gz
```

Exemple age :

```bash
age -r <votre_cle> -o ~/backups/<archive>.tar.gz.age ~/backups/<archive>.tar.gz
```

Résultat attendu : une archive chiffrée existe avant tout stockage hors VPS.

## Stockage hors VPS

Stocker uniquement une archive chiffrée sur un support externe ou un coffre-fort.
Ne jamais envoyer une archive brute par messagerie ou vers un dépôt Git.

## Procédure de restauration prudente

1. Restaurer sur un VPS de test si possible.
2. Vérifier le checksum.
3. Déchiffrer localement.
4. Extraire dans un dossier temporaire.
5. Inspecter les fichiers avant remplacement.
6. Restaurer `~/.openclaw`, `~/.hermes`, `.env` et l'unité systemd.
7. Appliquer `chmod 700` sur dossiers et `chmod 600` sur fichiers sensibles.
8. Redémarrer le service utilisateur.

## Test de restauration

```bash
mkdir -p /tmp/hermes-openclaw-restore-test
tar -tzf ~/backups/<archive>.tar.gz | head
```

Résultat attendu : l'archive est lisible et contient les chemins attendus.
Ne pas afficher de secrets dans un terminal partagé.

## Exemple cron

```cron
30 3 * * 0 /home/<utilisateur>/hermes-openclaw/scripts/backup-example.sh >/dev/null 2>&1
```

Résultat attendu : une sauvegarde locale hebdomadaire est produite. Ajouter un
chiffrement avant tout stockage externe.

## Exemple systemd timer

Service utilisateur conceptuel :

```ini
[Unit]
Description=Sauvegarde Hermes OpenClaw

[Service]
Type=oneshot
ExecStart=%h/hermes-openclaw/scripts/backup-example.sh
```

Timer utilisateur conceptuel :

```ini
[Unit]
Description=Planification sauvegarde Hermes OpenClaw

[Timer]
OnCalendar=Sun 03:30
Persistent=true

[Install]
WantedBy=timers.target
```

Résultat attendu : systemd lance le script selon le calendrier après installation
manuelle par l'utilisateur.
