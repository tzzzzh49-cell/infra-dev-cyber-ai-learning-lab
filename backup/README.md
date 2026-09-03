# Sauvegardes Restic

Ce dossier contient les **scripts versionnés** de sauvegarde et de restauration.
Les archives produites ne vivent pas ici : elles vont dans
`outputs/backups/`, qui reste hors Git.

| Fichier | Rôle |
| --- | --- |
| `init-local.sh` | initialiser le dépôt Restic local |
| `backup-local.sh` | créer une sauvegarde locale |
| `restore-test-local.sh` | tester une restauration isolée |
| `restic-excludes.txt` | exclure secrets, caches et sorties récursives |

La procédure se trouve dans
[`docs/backups/restic-local-first.md`](../docs/backups/restic-local-first.md).
