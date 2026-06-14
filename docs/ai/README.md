# OpenAI API read-only

Objectif : préparer une future intégration OpenAI API sans appel réel obligatoire, sans secret et sans exécution automatique de commandes.

## Statut

- Aucun client OpenAI n'est ajouté.
- Aucune dépendance OpenAI n'est ajoutée.
- Aucune variable `OPENAI_API_KEY` n'est requise pour utiliser le lab.
- Aucun endpoint applicatif AI actif n'est ajouté.
- Aucun agent IA ne doit exécuter automatiquement de commande système.

## Modèle de sécurité

Usage autorisé :

- résumer un rapport Markdown ou JSON déjà généré ;
- extraire des risques depuis un rapport ;
- proposer une checklist de vérification ;
- reformuler des erreurs observées.

Usage interdit :

- exécuter des commandes ;
- modifier le système, Docker, le réseau ou le firewall ;
- lire volontairement des secrets ;
- stocker des prompts ou réponses contenant des secrets ;
- décider seule d'une action corrective.

## Variables préparatoires

Le fichier `.env.ai.example` documente les variables attendues sans secret réel.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_MAX_INPUT_CHARS=12000
OPENAI_MAX_OUTPUT_TOKENS=800
AI_READ_ONLY=true
```

La clé réelle doit rester uniquement dans une variable d'environnement ou un fichier privé non commité.

## Flux prévu

```text
Rapport Markdown/JSON
  -> normalisation du contenu revu
  -> résumé court
  -> extraction des risques
  -> checklist humaine
  -> aucune commande exécutée automatiquement
```

## Exemple de sortie attendue

Un futur module read-only pourra produire :

- résumé en quelques lignes ;
- risques classés par gravité ;
- éléments manquants ou ambigus ;
- checklist d'actions manuelles à valider humainement.

## Structure préparatoire

- `docs/ai/README.md` : règles et flux attendus ;
- `app/ai/README.md` : emplacement réservé pour un futur module applicatif read-only ;
- `.env.ai.example` : variables sans secret.

## Limites

- Pas d'appel OpenAI dans cette étape.
- Pas de dépendance SDK.
- Pas d'exécution automatique de commandes.
- Pas de modification applicative des endpoints existants.
