# Restic S3-compatible

Objectif : préparer une sauvegarde distante S3-compatible sans configurer de backend réel dans le dépôt.

Cette page est documentaire. Les endpoints, buckets, access keys, secret keys et passphrases doivent rester hors Git.

## Variables attendues

Créer un fichier privé non commité à partir de `.env.backup.example`, puis remplacer uniquement hors dépôt :

```dotenv
RESTIC_REPOSITORY=s3:<S3_ENDPOINT>/<S3_BUCKET>/<S3_PREFIX>
RESTIC_PASSWORD_FILE=<CHEMIN_ABSOLU_VERS_UN_FICHIER_PRIVE>
RESTIC_EXCLUDE_FILE=backup/restic-excludes.txt
AWS_ACCESS_KEY_ID=<ACCESS_KEY_HORS_GIT>
AWS_SECRET_ACCESS_KEY=<SECRET_KEY_HORS_GIT>
AWS_DEFAULT_REGION=<REGION_PLACEHOLDER>
```

Ne jamais commiter le fichier privé réel ni le fichier de passphrase.

## Ce qui est sauvegardé

Par défaut, les scripts locaux sélectionnent une base prudente :

- `README.md`, `ROADMAP.md`, `AGENTS.md` et `Makefile` ;
- `compose.yaml` et exemples `.env*.example` ;
- `ansible/`, `app/`, `backup/`, `docs/`, `openclaw/` et `scripts/` quand ces chemins existent.

Les rapports dans `outputs/reports/` sont exclus par défaut. Les inclure seulement après revue manuelle et choix explicite hors dépôt.

## Ce qui est exclu

Le fichier `backup/restic-excludes.txt` exclut notamment :

- `.git`, `.venv`, `.runtime` et caches ;
- `.env`, `.env.local`, `.env.vps`, `.env.backup`, `.env.ai` et variantes locales ;
- clés privées, tokens et fichiers de passphrase ;
- `outputs/raw`, `outputs/rendered`, `outputs/backups` et `outputs/reports`.

## Init distant

Après export des variables privées, initialiser le dépôt distant hors Git :

```bash
restic init
```

Résultat attendu :

- dépôt distant initialisé ;
- aucun secret écrit dans le dépôt Git ;
- configuration reproductible documentée avec placeholders.

## Backup distant

Après revue des chemins et exclusions :

```bash
restic backup --exclude-file "$RESTIC_EXCLUDE_FILE" README.md ROADMAP.md AGENTS.md Makefile compose.yaml ansible app backup docs openclaw scripts
```

Adapter la liste hors dépôt si certains chemins n'existent pas ou si des rapports revus doivent être inclus.

## Check distant

Vérifier l'intégrité du dépôt :

```bash
restic check
```

Résultat attendu :

- index et snapshots vérifiés ;
- aucune sortie contenant de secret n'est copiée dans le dépôt.

## Restore drill distant

Tester la restauration dans `/tmp` pour ne pas écraser le dépôt courant :

```bash
RESTIC_RESTORE_TARGET=/tmp/infra-dev-cyber-ai-learning-lab-restic-s3-restore-drill
restic restore latest --target "$RESTIC_RESTORE_TARGET"
```

Points de contrôle :

- fichiers attendus présents dans le dossier de test ;
- absence de secrets restaurés depuis les chemins exclus ;
- procédure de restauration documentée hors dépôt après revue.

## Limites

- Aucun backend S3 réel n'est fourni.
- Aucun secret cloud n'est requis pour utiliser le lab local.
- Les scripts `backup/*.sh` restent volontairement local-first et refusent les repositories distants.
