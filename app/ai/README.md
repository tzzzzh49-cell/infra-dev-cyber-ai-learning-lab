# app/ai

Emplacement réservé pour une future intégration OpenAI API en lecture seule.

Contraintes :

- pas d'appel OpenAI obligatoire ;
- pas de clé API dans le code ;
- pas de dépendance SDK ajoutée à cette étape ;
- pas d'exécution de commandes ;
- pas de modification système, réseau ou Docker ;
- entrée limitée à des rapports Markdown/JSON déjà générés et revus.

Flux prévu :

```text
report -> summary -> risks -> human checklist
```

Tout futur code dans ce dossier devra rester désactivé par défaut et couvert par des tests dédiés.
