# 05 - HTTPS et reverse proxy

Objectif : préparer l'exposition HTTPS future avec Caddy, Nginx ou un proxy OAuth, sans imposer de déploiement réel dans cette étape.

Principes :

- terminer TLS via un reverse proxy maintenu ;
- proxy vers `127.0.0.1:8000` uniquement ;
- placer OAuth2 Proxy devant `/diag*` avec le flux Authorization Code et PKCE S256 ;
- transmettre au backend un JWT OIDC dans `Authorization: Bearer`, puis le
  revalider et l'autoriser dans l'API ;
- ne pas documenter de domaine réel obligatoire ;
- ne pas committer de certificat, clé privée ou token DNS.

Fichier exemple :

```text
docs/vps/Caddyfile.example
docs/vps/nginx.reverse-proxy.example.conf
```

Placeholders à remplacer hors dépôt :

- `<LAB_DOMAIN>` : domaine de lab, jamais un domaine réel dans l'exemple commité ;
- `<ADMIN_EMAIL>` : email utilisé pour ACME ;
- `OIDC_ISSUER_URL`, `OIDC_JWKS_URL`, `OIDC_CLIENT_ID` et `OIDC_AUDIENCE` ;
- `OIDC_CLIENT_SECRET_FILE` et `OIDC_COOKIE_SECRET_FILE`, montés hors Git.

Points de contrôle avant exposition :

- le binding API Compose reste forcé sur `127.0.0.1` ;
- `APP_ENV=vps` est actif côté application ;
- `DIAG_PROTECTION_DISABLED=false` ;
- Caddy envoie `/diag*` vers OAuth2 Proxy ;
- Swagger, ReDoc et OpenAPI sont désactivés en mode VPS ;
- l'API valide issuer, audience, signature, expiration, durée et rôles du JWT ;
- aucun domaine, token DNS, certificat ou mot de passe réel n'est commité.
- les routes publiques non sensibles ne transmettent pas de token inutilement.

Tout exemple doit utiliser des placeholders comme `<LAB_DOMAIN>` et `<ADMIN_EMAIL>`.

## Exemple Ansible indicatif

Extrait non actif à adapter dans un rôle relu avant usage réel :

```yaml
- name: Déployer le reverse proxy de diagnostic
  hosts: vps
  become: true
  vars:
    lab_domain: "<LAB_DOMAIN>"
    nginx_site_path: /etc/nginx/sites-available/infra-dev-cyber-ai-learning-lab
  tasks:
    - name: Installer la configuration Nginx relue
      ansible.builtin.template:
        src: nginx.reverse-proxy.example.conf.j2
        dest: "{{ nginx_site_path }}"
        mode: "0644"
      notify: Reload nginx
      tags:
        - reverse-proxy
        - tls

  handlers:
    - name: Reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
```

La configuration OIDC complète est décrite dans
[`08-authentification-oidc.md`](08-authentification-oidc.md). Le secret client et
la clé de cookie restent dans des fichiers privés montés au runtime.
