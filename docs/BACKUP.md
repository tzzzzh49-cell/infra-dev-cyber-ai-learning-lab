# Sauvegardes Hermes + OpenClaw Gateway

## Quoi sauvegarder

- `~/.openclaw` si le dossier existe.
- `~/.hermes` si le dossier existe.
- Le dépôt local `~/hermes-openclaw`.
- Le fichier `.env` local.
- L'unité systemd utilisateur `~/.config/systemd/user/hermes-openclaw-loop.service`.

## Quoi ne jamais mettre dans Git

- `.env` réel.
- Sessions WhatsApp.
- Tokens Telegram.
- Clés API.
- Clés SSH privées.
- Archives de sauvegarde.
- Logs contenant des messages privés.

## Fréquence recommandée

- Après chaque changement de configuration important.
- Avant une mise à jour OpenClaw ou Hermes.
- Une fois par semaine pour un MVP actif.
- Avant tout test WhatsApp.

## Sauvegarde OpenClaw CLI si disponible

Si OpenClaw fournit une commande officielle de sauvegarde, l'utiliser en priorité après lecture de sa documentation :

```bash
# Exemple indicatif à vérifier selon version officielle.
openclaw backup create
```

Résultat attendu : export local contrôlé, à chiffrer avant stockage externe.

## Script de sauvegarde complet

Le dépôt fournit :

```bash
./scripts/backup-example.sh
```

Résultat attendu : archive `.tar.gz` dans `~/backups`, checksum SHA-256 et permissions strictes. Le script n'effectue aucun transfert automatique.

## Checksum SHA-256

```bash
sha256sum ~/backups/hermes-openclaw-*.tar.gz
sha256sum -c ~/backups/hermes-openclaw-*.sha256
```

Résultat attendu : checksum valide avant chiffrement et restauration.

## chmod strict

```bash
chmod 600 ~/backups/hermes-openclaw-*.tar.gz
chmod 600 ~/backups/hermes-openclaw-*.sha256
```

Résultat attendu : archive et checksum non lisibles par les autres utilisateurs.

## Chiffrement GPG ou age

Exemple GPG :

```bash
gpg --symmetric --cipher-algo AES256 ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz
chmod 600 ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.gpg
```

Exemple age :

```bash
age -r <votre_cle> -o ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.age ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz
chmod 600 ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.age
```

Résultat attendu : seule l'archive chiffrée sort du VPS.

## Stockage hors VPS

- Stocker uniquement des archives chiffrées.
- Utiliser un emplacement distinct du VPS.
- Conserver plusieurs versions.
- Tester la restauration périodiquement.

## Restauration prudente

1. Créer un snapshot ou une copie de l'état actuel.
2. Arrêter le service utilisateur.
3. Déchiffrer l'archive localement sur le VPS.
4. Vérifier le checksum.
5. Restaurer dans un dossier temporaire.
6. Comparer les fichiers.
7. Copier uniquement les éléments nécessaires.
8. Redémarrer le service.

```bash
systemctl --user stop hermes-openclaw-loop.service
mkdir -p ~/restore-test
tar -tzf ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz | head
```

Résultat attendu : aucun écrasement accidentel.

## Test de restauration

```bash
mkdir -p ~/restore-test
tar -xzf ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz -C ~/restore-test
find ~/restore-test -maxdepth 3 -type f | sort | head -50
```

Résultat attendu : les fichiers attendus sont présents dans un dossier temporaire.

## Exemple cron

```cron
# Exemple manuel à installer avec crontab -e.
# Sauvegarde chaque dimanche à 03:30.
30 3 * * 0 /home/<utilisateur>/hermes-openclaw/scripts/backup-example.sh
```

## Exemple systemd timer

`~/.config/systemd/user/hermes-openclaw-backup.service` :

```ini
[Unit]
Description=Sauvegarde Hermes OpenClaw

[Service]
Type=oneshot
ExecStart=%h/hermes-openclaw/scripts/backup-example.sh
```

`~/.config/systemd/user/hermes-openclaw-backup.timer` :

```ini
[Unit]
Description=Planifie la sauvegarde Hermes OpenClaw

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

Activation manuelle :

```bash
systemctl --user daemon-reload
systemctl --user enable --now hermes-openclaw-backup.timer
systemctl --user list-timers
```
