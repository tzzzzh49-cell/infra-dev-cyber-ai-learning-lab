# Restic local-first

Objectif : préparer une approche de sauvegarde Restic prudente, sans secret réel.

Principes :

- commencer par un dépôt local de test ;
- utiliser une passphrase forte hors dépôt ;
- vérifier les restaurations, pas seulement les sauvegardes ;
- exclure les caches, environnements virtuels et secrets ;
- chiffrer systématiquement les sauvegardes ;
- documenter les chemins avec des placeholders.

Exemples de chemins à considérer :

- `outputs/reports/` après revue ;
- fichiers Compose et documentation ;
- scripts d'exploitation non secrets.

Ne jamais stocker la passphrase Restic dans Git.

## Configuration locale

Créer un fichier privé non commité à partir de `.env.backup.example`, puis définir au minimum :

```dotenv
RESTIC_REPOSITORY=outputs/backups/restic-local
RESTIC_PASSWORD_FILE=<CHEMIN_ABSOLU_VERS_UN_FICHIER_PRIVE>
RESTIC_EXCLUDE_FILE=backup/restic-excludes.txt
```

Le fichier pointé par `RESTIC_PASSWORD_FILE` doit rester hors dépôt et avoir le
mode `0400` ou `0600`.

## Exclusions par défaut

Le fichier `backup/restic-excludes.txt` exclut notamment :

- caches Python et outils ;
- `.venv` ;
- `.runtime` ;
- `.env`, `.env.local`, `.env.backup` ;
- clés, tokens et fichiers de passphrase courants ;
- `outputs/raw`, `outputs/rendered`, `outputs/backups` et `outputs/reports`.

Les rapports dans `outputs/reports` sont exclus tant qu'ils ne sont pas revus explicitement.

## Drill local

Exemple de séquence locale, après avoir exporté les variables privées :

```bash
backup/init-local.sh
backup/backup-local.sh
restic snapshots
restic check
backup/restore-test-local.sh
```

Résultat attendu :

- le dépôt Restic local est initialisé dans `outputs/backups/restic-local` ;
- un snapshot est créé avec la sélection prudente du dépôt ;
- `restic snapshots` liste les points de restauration disponibles sans afficher de secret ;
- `restic check` vérifie l'intégrité du dépôt avec les variables privées exportées ;
- le dernier snapshot est restauré dans un dossier `/tmp/infra-dev-cyber-ai-learning-lab-restic-restore-test-*` ;
- les fichiers restaurés sont inspectables sans écraser le dépôt courant.

## Restauration partielle

Restaurer un seul chemin dans `/tmp` permet de vérifier un fichier sans écraser
le dépôt courant :

```bash
RESTIC_RESTORE_TARGET=/tmp/infra-dev-cyber-ai-learning-lab-restic-partial
restic restore latest --target "$RESTIC_RESTORE_TARGET" --include README.md
```

Points de contrôle :

- le fichier restauré se trouve sous `$RESTIC_RESTORE_TARGET` ;
- aucun fichier local du dépôt courant n'est remplacé ;
- les secrets restent exclus par `backup/restic-excludes.txt`.

## Limites

- Aucun S3 réel n'est configuré dans cette étape.
- Aucun identifiant cloud ne doit être ajouté.
- Le test de restauration local ne supprime pas automatiquement le dossier restauré ; le nettoyer manuellement après revue si nécessaire.
