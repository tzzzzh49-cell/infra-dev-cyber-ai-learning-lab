# Audit d'activation de la phase 0

- Édition auditée : `2.0.0`
- Périmètre : J001 à J010
- Décision : phase 0 activée ; phases 1 à 13 maintenues inactives
- Guide actif SHA-256 : `2684cc3bb270c69e8a8c9513f4bac25b5a267609f46327977bed049fb77782ea`
- Copie historique SHA-256 : `f38dbd6b9d97ed6ccab21f15619789559792565bed8b5d733155299b1d36b77d`

## Autorité pédagogique

L'audit utilise exclusivement le contenu du guide historique importé et de son
édition lab. La fiche du site France Compétences et toute autre source
d'apprentissage externe ont été exclues. Les intitulés historiques présents
dans le guide sont conservés comme éléments du guide, sans vérification ni
enrichissement externe.

## Contrôles réalisés

- l'identité octet pour octet de la copie historique `v1.0.0` a été vérifiée ;
- le contrat global de l'édition lab a été relu avant l'activation ;
- les dix fiches J001 à J010 ont été relues avec leur objectif, garde-fou,
  commandes, résultat attendu, preuve et critère de passage ;
- la cartographie vers les chemins réels du dépôt a été vérifiée dans
  `learning/lab-map.yml`, sans inventer les composants encore absents ;
- les cas positif, refus attendu et rollback de la phase ont été classés
  explicitement ;
- l'empreinte du guide actif a été recalculée après les corrections.

## Corrections intégrées

- le contrat de chemins fait de `learning/days/JNNN/learner.md` le journal
  canonique et réserve `.proof/` aux faits mécaniques ;
- J004 reste une observation en lecture seule et n'injecte aucune panne ;
- J006 utilise le scénario fil rouge cohérent de 80 personnes ;
- J008 valide réellement le CSV et ne masque plus un code retour non nul.

Les corrections repérées hors du périmètre actif (J181, J278 et J312) sont
présentes dans l'édition lab, mais ne valent ni audit ni activation de leurs
phases respectives.

## Limites et décision

Cette activation atteste uniquement que la phase 0 est prête à être utilisée
par le cockpit. Elle ne crédite aucune journée et ne valide aucun acquis de
l'apprenant. Les alias du lab, le dépôt GitHub privé, la clé publique de
chiffrement et les deux emplacements de preuve hors Git restent des
préconditions locales contrôlées au premier lancement.

Une phase ultérieure ne pourra être activée qu'après une revue dédiée de toutes
ses fiches, la correction des écarts observés, une nouvelle empreinte du guide
et la mise à jour explicite de `curriculum/active.json`.
