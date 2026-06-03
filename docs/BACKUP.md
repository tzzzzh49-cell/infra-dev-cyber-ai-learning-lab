# Sauvegardes

## Quoi sauvegarder

- `~/.openclaw` si le répertoire existe.
- `~/.hermes` si le répertoire existe.
- Le dépôt local `~/hermes-openclaw`.
- `.env` local, car il contient la configuration réelle.
- L'unité systemd utilisateur `~/.config/systemd/user/hermes-openclaw-loop.service`.

## Quoi ne jamais mettre dans Git

- Archives de sauvegarde.
- `.env` réel.
- Tokens.
- Clés API.
- Sessions WhatsApp.
- Logs privés.
- Exports de base de données.

## Fréquence recommandée

- Sauvegarde locale avant chaque changement important.
- Sauvegarde chiffrée hebdomadaire hors VPS.
- Test de restauration mensuel.

## Sauvegarde OpenClaw CLI si disponible

Si OpenClaw fournit une commande officielle de sauvegarde, utilisez-la en priorité après lecture de sa documentation :

```bash
openclaw backup --help
```

Résultat attendu : la commande documente les chemins et options de sauvegarde.
Ne transférez pas automatiquement les fichiers générés.

## Script de sauvegarde complet

Le script `scripts/backup-example.sh` crée une archive locale dans `~/backups` en incluant seulement les chemins existants.
Il génère aussi un checksum SHA-256 et applique `chmod 600`.

```bash
scripts/backup-example.sh
```

Résultat attendu : une archive `.tar.gz` et un fichier `.sha256` sont créés localement.

## Checksum SHA-256

Vérification :

```bash
sha256sum -c ~/backups/<archive>.tar.gz.sha256
```

Résultat attendu : le checksum est valide.

## Chmod strict

```bash
chmod 600 ~/backups/<archive>.tar.gz ~/backups/<archive>.tar.gz.sha256
```

Résultat attendu : seuls les fichiers de sauvegarde de l'utilisateur courant sont lisibles par lui.

## Chiffrement GPG ou age

Exemple GPG :

```bash
gpg --symmetric --cipher-algo AES256 ~/backups/<archive>.tar.gz
```

Exemple age :

```bash
age -r <votre_cle> -o ~/backups/<archive>.tar.gz.age ~/backups/<archive>.tar.gz
```

Résultat attendu : une archive chiffrée est produite avant tout stockage externe.

## Stockage hors VPS

Stockez uniquement l'archive chiffrée hors VPS.
Ne stockez jamais une archive brute sur un service externe.

## Restauration prudente

1. Restaurer sur une machine de test si possible.
2. Vérifier le checksum.
3. Déchiffrer localement.
4. Extraire dans un répertoire temporaire.
5. Comparer les fichiers avant écrasement.
6. Restaurer les permissions.
7. Redémarrer le service utilisateur.

## Test de restauration

```bash
mkdir -p /tmp/hermes-openclaw-restore-test
tar -tzf ~/backups/<archive>.tar.gz | head
tar -xzf ~/backups/<archive>.tar.gz -C /tmp/hermes-openclaw-restore-test
```

Résultat attendu : l'archive est lisible et extractible sans toucher aux chemins de production.

## Exemple cron

```cron
15 3 * * 0 /home/<utilisateur>/hermes-openclaw/scripts/backup-example.sh
```

Résultat attendu : une sauvegarde locale hebdomadaire est créée.
Chiffrez avant stockage externe.

## Exemple systemd timer

Service utilisateur :

```ini
[Unit]
Description=Sauvegarde Hermes OpenClaw

[Service]
Type=oneshot
ExecStart=%h/hermes-openclaw/scripts/backup-example.sh
```

Timer utilisateur :

```ini
[Unit]
Description=Timer sauvegarde Hermes OpenClaw

[Timer]
OnCalendar=Sun *-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

Résultat attendu : systemd déclenche une sauvegarde locale hebdomadaire.
