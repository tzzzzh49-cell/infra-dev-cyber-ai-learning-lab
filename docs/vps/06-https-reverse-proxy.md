# 05 - HTTPS et reverse proxy

Objectif : préparer l'exposition HTTPS future avec Caddy, Nginx ou un proxy OAuth, sans imposer de déploiement réel dans cette étape.

Principes :

- terminer TLS via un reverse proxy maintenu ;
- proxy vers `127.0.0.1:8000` uniquement ;
- ajouter une authentification avant tout accès public à `/diag` et aux exports ;
- transmettre au backend un `X-Diag-Token` issu d'un secret runtime privé si le proxy termine l'authentification ;
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
- `<BASIC_AUTH_USER>` : utilisateur de l'authentification reverse proxy ;
- `<CADDY_HASHED_PASSWORD>` : hash Caddy généré hors dépôt ;
- `DIAG_ACCESS_TOKEN_HASH` : hash stocké côté application via secrets manager ;
- `DIAG_UPSTREAM_TOKEN` : token clair côté proxy si le proxy injecte `X-Diag-Token` après auth.

Points de contrôle avant exposition :

- `APP_HOST=127.0.0.1` reste actif côté Compose ;
- `APP_ENV=vps` est actif côté application ;
- `DIAG_ACCESS_TOKEN_HASH` est injecté hors Git ;
- `DIAG_PROTECTION_DISABLED=false` ;
- Caddy applique une authentification sur les routes de diagnostic ;
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

Le template réel doit récupérer `DIAG_UPSTREAM_TOKEN` depuis un gestionnaire de secrets, jamais depuis Git. Pour OAuth/OIDC, placer `oauth2-proxy` ou un mécanisme équivalent devant les locations `/diag*`, puis conserver la protection applicative par hash.
