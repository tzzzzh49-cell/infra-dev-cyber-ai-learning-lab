# 05 - HTTPS et reverse proxy

Objectif : préparer l'exposition HTTPS future sans imposer de Caddy opérationnel dans cette étape.

Principes :

- terminer TLS via un reverse proxy maintenu ;
- proxy vers `127.0.0.1:8000` uniquement ;
- ajouter une authentification avant tout accès public à `/diag` ;
- ne pas documenter de domaine réel obligatoire ;
- ne pas committer de certificat, clé privée ou token DNS.

Tout exemple doit utiliser des placeholders comme `<DOMAIN>` et `<EMAIL>`.
