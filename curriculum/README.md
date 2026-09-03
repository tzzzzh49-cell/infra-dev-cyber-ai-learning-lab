# Cursus versionné

Ce dossier contient la source pédagogique officielle. Il ne contient ni la
progression quotidienne, ni les sorties du lab.

## Source de vérité

[`active.json`](active.json) désigne la version active du guide, son empreinte
SHA-256 et les phases auditées. Le cockpit lit ce manifeste automatiquement.

Les dossiers `v1.0.0/`, `v2.0.0/` et `v2.1.0/` sont des versions complètes du
guide :

- la version marquée `active` dans le manifeste est la seule créditable ;
- les versions historiques ou remplacées restent immuables ;
- une évolution suit la politique SemVer décrite dans `active.json`.

Les comptes rendus de contrôle des phases vivent dans `audits/`.

Pour suivre le parcours, utiliser [`../learning/README.md`](../learning/README.md)
ou lancer `make learn` depuis la racine.
