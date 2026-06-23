# Exemples d'appels API protégés en local

> Langues : Français

Ces exemples concernent uniquement `APP_ENV=lab`. En VPS, utiliser le flux OIDC
documenté dans [`vps/08-authentification-oidc.md`](vps/08-authentification-oidc.md).
Ne pas copier de jeton réel dans Git, dans une issue ou dans un rapport.

## Sommaire

- [Générer un jeton](#generer-un-jeton)
- [Configurer l'application](#configurer-lapplication)
- [Appeler les endpoints](#appeler-les-endpoints)
- [Limites](#limites)

## Générer un jeton

```bash
python3 scripts/generate_diag_token.py
export DIAG_CLIENT_TOKEN='<JETON_AFFICHE_PAR_LE_SCRIPT>'
export DIAG_ACCESS_TOKEN_HASH='<HASH_AFFICHE_PAR_LE_SCRIPT>'
```

`DIAG_CLIENT_TOKEN` sert uniquement au client `curl`. `DIAG_ACCESS_TOKEN_HASH`
est la valeur à fournir à l'application. Le script ne crée aucun fichier.

## Configurer l'application

```bash
export APP_ENV=lab
export APP_PORT=8000
export DIAG_COMMAND_TIMEOUT=3
export DIAG_ACCESS_TOKEN_HASH
```

Le jeton partagé est refusé lorsque `APP_ENV=vps`.

## Appeler les endpoints

Avec l'en-tête standard `Authorization`, transmis à `curl` par son entrée standard
plutôt que dans ses arguments visibles par les autres processus :

```bash
printf 'header = "Authorization: Bearer %s"\n' "$DIAG_CLIENT_TOKEN" \
  | curl --config - -fsS http://127.0.0.1:8000/diag

printf 'header = "Authorization: Bearer %s"\n' "$DIAG_CLIENT_TOKEN" \
  | curl --config - -fsS -X POST http://127.0.0.1:8000/diag/export/json

printf 'header = "Authorization: Bearer %s"\n' "$DIAG_CLIENT_TOKEN" \
  | curl --config - -fsS -X POST http://127.0.0.1:8000/diag/export/markdown
```

Avec l'en-tête local historique `X-Diag-Token` :

```bash
printf 'header = "X-Diag-Token: %s"\n' "$DIAG_CLIENT_TOKEN" \
  | curl --config - -fsS http://127.0.0.1:8000/diag
```

## Limites

- `/diag` retourne un état minimisé sans hostname, adresse IP, suffixe DNS,
  processus, nom de conteneur ni sortie brute de commande.
- Les exports complets restent locaux ; l'API retourne seulement `report_id`.
- Chaque identité ou adresse IP est limitée à 5 diagnostics par minute.
- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut et reste plafonné côté code.
- `DIAG_COMMAND_RETRIES` vaut `0` par défaut et doit rester bas pour éviter des
  diagnostics longs ou bruyants.
- `/diag` et les exports peuvent contenir des informations système locales.
