# Backups

Cette section prépare la stratégie de sauvegarde pour v0.4.0 VPS.

À sauvegarder :

- configuration validée et non secrète ;
- rapports utiles après revue ;
- scripts de déploiement documentés ;
- métadonnées nécessaires à la restauration.

À ne jamais sauvegarder en clair dans le dépôt :

- clés privées SSH ;
- tokens API ;
- mots de passe ;
- fichiers `.env` contenant des secrets ;
- exports contenant des données sensibles non revues.

Voir aussi [Restic local-first](restic-local-first.md).

Scripts préparatoires :

- `backup/init-local.sh` : initialise un dépôt Restic local ;
- `backup/backup-local.sh` : sauvegarde une sélection prudente du dépôt ;
- `backup/restore-test-local.sh` : restaure le dernier snapshot dans `/tmp` pour vérifier la récupérabilité.

Ces scripts n'utilisent aucun backend S3 et exigent une passphrase hors dépôt via `RESTIC_PASSWORD_FILE`.
