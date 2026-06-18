# Exemples d'appels API protégés

> Langues : Français

Ces exemples gardent le jeton client dans la session shell et exportent seulement
son hash côté application. Ne pas copier de jeton réel dans Git, dans une issue ou
dans un rapport.

## Sommaire

- [Générer un jeton](#generer-un-jeton)
- [Configurer l'application](#configurer-lapplication)
- [Appeler les endpoints](#appeler-les-endpoints)
- [Limites](#limites)

## Générer un jeton

```bash
python3 scripts/generate_diag_token.py --format sha256
export DIAG_CLIENT_TOKEN='<JETON_AFFICHE_PAR_LE_SCRIPT>'
export DIAG_ACCESS_TOKEN_HASH='<HASH_AFFICHE_PAR_LE_SCRIPT>'
```

`DIAG_CLIENT_TOKEN` sert uniquement au client `curl`. `DIAG_ACCESS_TOKEN_HASH`
est la valeur à fournir à l'application. Le script ne crée aucun fichier.

## Configurer l'application

```bash
export APP_ENV=vps
export APP_HOST=127.0.0.1
export APP_PORT=8000
export DIAG_COMMAND_TIMEOUT=3
export DIAG_ACCESS_TOKEN_HASH
```

En local, `APP_ENV=lab` reste possible. Pour vérifier la protection avant toute
exposition, tester avec `APP_ENV=vps`.

## Appeler les endpoints

Avec l'en-tête standard `Authorization` :

```bash
curl -fsS \
  -H "Authorization: Bearer $DIAG_CLIENT_TOKEN" \
  http://127.0.0.1:8000/diag

curl -fsS \
  -H "Authorization: Bearer $DIAG_CLIENT_TOKEN" \
  -X POST \
  http://127.0.0.1:8000/diag/export/json

curl -fsS \
  -H "Authorization: Bearer $DIAG_CLIENT_TOKEN" \
  -X POST \
  http://127.0.0.1:8000/diag/export/markdown
```

Avec l'en-tête interne `X-Diag-Token`, utile derrière un reverse proxy contrôlé :

```bash
curl -fsS \
  -H "X-Diag-Token: $DIAG_CLIENT_TOKEN" \
  http://127.0.0.1:8000/diag
```

## Limites

- `DIAG_COMMAND_TIMEOUT` vaut `3` secondes par défaut et reste plafonné côté code.
- `DIAG_COMMAND_RETRIES` vaut `0` par défaut et doit rester bas pour éviter des
  diagnostics longs ou bruyants.
- `/diag` et les exports peuvent contenir des informations système locales.
