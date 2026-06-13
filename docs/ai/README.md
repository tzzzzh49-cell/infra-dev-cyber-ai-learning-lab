# Placeholders OpenAI et OpenClaw

Objectif : préparer les futures étapes IA sans intégrer d'appel API réel, sans secret et sans exécution automatique de commandes.

## Statut

- Aucun client OpenAI n'est ajouté.
- Aucune dépendance OpenAI n'est ajoutée.
- Aucune variable `OPENAI_API_KEY` n'est requise pour utiliser le lab.
- Aucune intégration OpenClaw active n'est ajoutée.
- Aucun agent IA ne doit exécuter automatiquement de commande système.

## OpenAI - usage futur autorisé

Les usages futurs devront rester limités à l'analyse de contenus déjà générés :

- résumé de rapports de diagnostic ;
- extraction de risques ;
- génération de checklist ;
- reformulation d'erreurs ou de constats.

Usages interdits :

- exécution de commandes ;
- décision autonome de modification système ;
- modification réseau ;
- action Docker destructive ;
- lecture ou stockage de secrets.

## OpenClaw - usage futur autorisé

OpenClaw devra rester encadré par :

- une allowlist explicite ;
- des runbooks lecture seule ;
- une validation humaine avant toute action ;
- un refus par défaut de toute commande non listée ;
- une journalisation des décisions.

Les fichiers dans `openclaw/` sont des placeholders documentaires. Ils ne constituent pas une intégration active.

## Données et secrets

Ne jamais ajouter au dépôt :

- clé API OpenAI réelle ;
- token OpenClaw ;
- secret Cloudflare ;
- mot de passe ;
- clé privée ;
- rapport contenant des informations sensibles non revues.
