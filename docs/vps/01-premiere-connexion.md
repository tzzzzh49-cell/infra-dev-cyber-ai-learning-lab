# 01 - Première connexion VPS

Objectif : préparer une connexion initiale sûre sans documenter de secret réel.

- Utiliser une adresse fictive comme `<VPS_IP>` dans les notes.
- Se connecter avec une clé SSH dédiée protégée par passphrase.
- Créer un utilisateur non-root dédié à l'administration.
- Vérifier l'OS, le nom d'hôte et les mises à jour disponibles avec des commandes de lecture ou de maintenance maîtrisées.
- Ne jamais coller de clé privée, token ou mot de passe dans le dépôt.

Exemple documentaire non exécutable tel quel :

```bash
ssh admin@<VPS_IP>
hostnamectl
uname -a
```
