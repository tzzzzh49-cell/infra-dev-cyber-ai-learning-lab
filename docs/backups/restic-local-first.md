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
