# 02 - Sécurisation SSH

Objectif : documenter les contrôles à prévoir avant le déploiement applicatif.

- Utiliser l'authentification par clé.
- Désactiver l'authentification par mot de passe uniquement après validation d'un accès de secours.
- Désactiver la connexion root directe si une procédure d'administration alternative est validée.
- Limiter les utilisateurs autorisés.
- Conserver une session ouverte pendant les changements SSH pour éviter tout verrouillage.

Ne pas stocker de clé privée ni de configuration contenant des secrets dans ce dépôt.
