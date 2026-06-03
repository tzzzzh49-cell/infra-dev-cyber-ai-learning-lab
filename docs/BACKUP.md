# Sauvegardes

## Quoi sauvegarder

- `~/.openclaw` si présent ;
- `~/.hermes` si présent ;
- dépôt local `~/hermes-openclaw` ;
- `.env` local ;
- unité systemd utilisateur `~/.config/systemd/user/hermes-openclaw-loop.service`.

## Quoi ne jamais mettre dans Git

- archives de sauvegarde ;
- checksums de sauvegardes privées ;
- `.env` réel ;
- sessions WhatsApp ;
- tokens ;
- clés API ;
- clés SSH privées ;
- logs privés.

## Fréquence recommandée

- Avant changement majeur : sauvegarde manuelle.
- Chaque semaine : sauvegarde locale.
- Chaque mois : test de restauration.
- Avant stockage externe : chiffrement obligatoire.

## Sauvegarde OpenClaw CLI si disponible

Si la version installée d'OpenClaw fournit une commande d'export, l'utiliser manuellement après vérification officielle.
Exemple indicatif :

```bash
openclaw backup --help
```

Résultat attendu : comprendre les options avant d'exécuter un export réel.

## Script de sauvegarde complet

Le dépôt fournit :

```bash
scripts/backup-example.sh
```

Le script :

- crée une archive `.tar.gz` dans `~/backups` ;
- inclut seulement les chemins existants ;
- ajoute un checksum SHA-256 ;
- applique `chmod 600` ;
- ne transfère rien automatiquement ;
- rappelle que le chiffrement est requis avant stockage externe.

## Checksum SHA-256

Vérifier une archive :

```bash
cd ~/backups
sha256sum -c hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.sha256
```

Résultat attendu : `OK`.

## chmod strict

```bash
chmod 600 ~/backups/*.tar.gz ~/backups/*.sha256
chmod 700 ~/backups
```

Résultat attendu : sauvegardes lisibles uniquement par l'utilisateur courant.

## Chiffrement GPG ou age

Exemples manuels :

```bash
gpg --symmetric --cipher-algo AES256 ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz
age -p -o ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.age ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz
```

Résultat attendu : un fichier chiffré est créé avant copie hors VPS.

## Stockage hors VPS

Stocker uniquement une archive chiffrée.
Ne jamais transférer automatiquement une archive non chiffrée.
Documenter l'emplacement externe dans un gestionnaire privé, pas dans Git.

## Restauration prudente

1. Restaurer sur une machine de test si possible.
2. Vérifier le checksum.
3. Déchiffrer localement.
4. Extraire dans un dossier temporaire.
5. Comparer les fichiers.
6. Copier seulement les chemins nécessaires.
7. Appliquer les permissions strictes.
8. Redémarrer le service utilisateur.

Exemple :

```bash
mkdir -p ~/restore-test
tar -xzf ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz -C ~/restore-test
```

Résultat attendu : contenu restauré dans `~/restore-test`, sans écraser la production.

## Test de restauration

À réaliser mensuellement :

```bash
sha256sum -c ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz.sha256
mkdir -p ~/restore-test
tar -tzf ~/backups/hermes-openclaw-YYYYMMDD-HHMMSS.tar.gz | head
```

Résultat attendu : checksum valide et archive lisible.

## Exemple cron

```cron
30 3 * * 0 /home/<utilisateur>/hermes-openclaw/scripts/backup-example.sh >> /home/<utilisateur>/backups/backup.log 2>&1
```

Note : ne pas commiter `backup.log`.

## Exemple systemd timer

Service utilisateur indicatif :

```ini
[Unit]
Description=Backup Hermes OpenClaw

[Service]
Type=oneshot
ExecStart=%h/hermes-openclaw/scripts/backup-example.sh
```

Timer utilisateur indicatif :

```ini
[Unit]
Description=Weekly backup Hermes OpenClaw

[Timer]
OnCalendar=Sun 03:30
Persistent=true

[Install]
WantedBy=timers.target
```

Résultat attendu : sauvegarde locale planifiée, à chiffrer avant stockage externe.
