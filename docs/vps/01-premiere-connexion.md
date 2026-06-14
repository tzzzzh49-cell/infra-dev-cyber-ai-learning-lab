# 01 - Première connexion VPS

Objectif : préparer une connexion initiale sûre sans documenter de secret réel ni lancer de déploiement.

- Utiliser une adresse fictive comme `<VPS_IP>` dans les notes.
- Se connecter avec une clé SSH dédiée protégée par passphrase.
- Créer un utilisateur non-root dédié à l'administration.
- Vérifier l'OS, le nom d'hôte et les mises à jour disponibles avec des commandes de lecture ou de maintenance maîtrisées.
- Ne jamais coller de clé privée, token ou mot de passe dans le dépôt.
- Conserver la session initiale ouverte tant que l'accès non-root n'a pas été validé.
- Documenter hors dépôt les éventuelles actions de durcissement réellement exécutées.

Exemple documentaire non exécutable tel quel :

```bash
ssh admin@<VPS_IP>
hostnamectl
uname -a
```

Compte cible attendu :

```text
<NON_ROOT_ADMIN_USER>
```

Ne pas commiter de mot de passe, clé privée ou adresse réelle associée à ce compte.
