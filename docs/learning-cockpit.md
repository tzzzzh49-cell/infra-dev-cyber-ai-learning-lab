# Contrat technique du cockpit d'apprentissage

Ce document est destiné aux mainteneurs. L'apprenant commence uniquement avec
`make learn` et son fichier `learner.md`.

## Autorité et propriété

- `curriculum/active.json` désigne une seule version du guide et son SHA-256.
- Le guide actif est l'unique source d'enseignement et d'évaluation. La fiche
  France Compétences n'en fait pas partie.
- L'apprenant possède tout le contenu de `learner.md`, y compris son statut.
- Codex possède seulement `.proof/review.json` et `.proof/review.md`.
- Le cockpit produit les captures d'empreintes, `proof.json`, `ci.json` et
  l'état local `.learning/state.json` ; il ne copie pas les réponses apprenant.

Les schémas publics de l'état et de la preuve se trouvent dans
`learning/schemas/`. Toute évolution incompatible exige une migration explicite
et une nouvelle valeur de `schema_version`.

Le dépôt source est public : tout fichier, commit, issue et historique poussé
doit être considéré comme visible. Le cockpit utilise donc uniquement les alias
pseudonymes dans Git ; secrets, preuves brutes, adresses réelles, noms DNS réels
et chemins personnels restent hors du dépôt.

## État local non versionné

Le premier `make learn` crée `.learning/local.json`, ignoré par Git. Ce fichier
ne contient ni adresse réelle ni clé privée : seulement les trois alias SSH
pseudonymes, la clé publique `age` et les chemins de deux stockages chiffrés
hors dépôt. `learning/local.example.json` documente le schéma sans être utilisé
comme configuration réelle.

La progression orchestrée reste elle aussi dans `.learning/state.json`. Elle ne
salit donc pas une branche après fusion. Si ce cache disparaît, le cockpit
reconstruit la prochaine journée depuis les preuves conformes fusionnées et les
branches quotidiennes ; les preuves et le registre public restent les
enregistrements portables du parcours.

Le cockpit refuse de démarrer une preuve créditable si :

- le hash du guide diffère du manifeste ;
- la phase n'est pas auditée ;
- le dépôt GitHub n'est pas public ;
- Git, `age`, GNU tar avec `--zstd`, l'éditeur, la signature Git personnelle ou
  la configuration locale manquent.

La voie recommandée pour préparer la signature personnelle est SSH. La clé
privée et le fichier public d'autorisation restent hors du dépôt :

```bash
mkdir -p ~/.config/aegis-learning
ssh-keygen -t ed25519 -f ~/.ssh/aegis-learning-signing
printf 'aegis-learning %s\n' "$(cat ~/.ssh/aegis-learning-signing.pub)" \
  > ~/.config/aegis-learning/allowed_signers
ssh-add ~/.ssh/aegis-learning-signing
git config --local gpg.format ssh
git config --local user.signingkey ~/.ssh/aegis-learning-signing.pub
git config --local gpg.ssh.allowedSignersFile \
  ~/.config/aegis-learning/allowed_signers
```

La clé privée doit être protégée par une phrase de passe et chargée dans
`ssh-agent`. Le doctor vérifie que la clé publique configurée est celle de
l'agent et celle autorisée par `allowed_signers`. Le principal reste toujours
`aegis-learning` : lors d'une rotation, `allowed_signers` conserve sous ce même
principal les anciennes clés publiques afin de revérifier les tags de phase
historiques, tandis que seule la clé courante chargée signe le nouveau jalon.

## Cycle d'une journée

Une issue publique est créée quand la journée démarre ; elle ne contient que la
référence et l'objectif issus du guide. La branche locale est créée par le
cockpit ; les commits et le push restent déclenchés par l'apprenant. Une draft PR
est créée après le premier push. La branche doit être fusionnée sans squash afin
de conserver prévision, tentative et résultat final.

La journée suivante reste verrouillée jusqu'à la réunion de trois faits :

1. l'apprenant a écrit `Statut: Validé` ;
2. les contrôles GitHub sont `Conforme` ;
3. la revue Codex est `ready`.

La revue enregistre l'empreinte du guide et des rubriques relues. Toute
modification ultérieure la rend automatiquement périmée. Le jalon `attempt`
attend toutes les rubriques et toutes les commandes de la fiche. Son commit
inclut aussi les livrables du lab modifiés hors de `learning/days/`; le plan de
contrôle pédagogique reste protégé. Les jalons `prediction` et `final` restent
bornés aux artefacts propres à la journée ; un livrable du lab changé après la
revue ne peut donc pas entrer dans le scellement final. Les trois jalons
`prediction`, `attempt` et `final` ne sont enregistrés qu'après leur commit et
leur push. La preuve embarque
les deux premiers SHA ; le SHA final est lié par la révision source publiée, ce
qui évite toute auto-référence impossible. Leur parentage reste direct —
baseline, prévision, tentative, final — sans commit intermédiaire susceptible de
masquer une action antérieure à la prévision ou postérieure à la revue. Une
réouverture utilise exclusivement son reçu `revisions.json`, versionné dans le
premier jalon de remplacement, pour définir une nouvelle frontière autorisée.
Même après plusieurs réouvertures et une perte du cache, l'hydratation relit le
reçu propre à chaque commit et rejoue cette chaîne avant d'accepter un SHA.
La baseline reste celle du plan de la première prévision, à condition qu'elle
appartienne à l'historique autoritaire de `origin/master`; une avancée ultérieure
de `master` ne réécrit donc pas le début de la journée. Chaque reçu de
réouverture doit en outre partir d'une ancienne chaîne elle-même valide.
Avant fusion, le cockpit vérifie aussi le
worktree, la synchronisation de la branche, la cible `master`, l'identité du HEAD
de la PR et la préservation effective d'un commit de fusion à deux parents.
Après cette fusion, la journée suivante est toujours créée depuis le nouveau
`origin/master`, jamais depuis l'ancien HEAD de la branche quotidienne.

Si une correction ou une mise à jour de branche rend le jalon `final` obsolète,
l'action `reopen-final` conserve une trace minimale de l'ancien cycle. Une simple
mise à jour par commit de fusion ne garde tentative, revue et preuve brute que
si son autre parent appartient au `origin/master` vérifié et si son arbre est
exactement celui de la fusion Git déterministe attendue ; elle exige ensuite une
nouvelle CI et un nouveau `final`. Toute autre correction ou fusion invalide
tentative, CI, revue et reçu, et impose un vrai passage `À reprendre`.

À une frontière de phase, la commande de tag signé cible explicitement la
baseline fusionnée, et non le HEAD restant sur la branche quotidienne. Le
cockpit vérifie ensuite la cible et la signature cryptographique avec
`git verify-tag`, puis exige que le même objet de tag soit présent sur `origin`,
avant d'effacer le rappel local. La journée suivante reste fermée jusque-là.
Si le cache local disparaît, les jalons manquants sont reconstruits dans
l'ordre uniquement depuis les commits présents sur la branche distante et dont
le plan versionné reste valide.

Cinq reçus mécaniques minimaux rendent ces transitions durables :
`source-mode.json` conserve le choix d'une aide extérieure,
`checkpoint-plan.json` lie chaque jalon à sa baseline et à la liste de chemins
gelée avant le commit, `final-seal.json` atteste le troisième jalon,
`activation.json` lie une consolidation à sa source et à son pin, et
`resume.json` distingue une reprise explicitement préparée après perte du cache.
Ils ne recopient aucun contenu de l'apprenant.

Un échec de l'automatisation place la journée en `manual-fallback`. Le journal
reste utilisable, mais la soumission est interdite jusqu'à réconciliation de
l'issue, de la branche et de la PR.

## Preuves brutes et publication

La commande interne `tools/learn.py archive` crée une archive
`.tar.zst.age` sous un identifiant opaque, la copie vers deux stockages distincts
et conserve dans Git un reçu minimal strict, sans chemin de stockage. Juste avant
la fusion, les deux fichiers sont retrouvés hors dépôt, leurs systèmes de
fichiers doivent être distincts et leur SHA-256 est recalculé. La publication
publique ne projette que l'identifiant opaque et l'empreinte. La rétention prévue
est d'un an après la fin du parcours.

Si une aide extérieure rend la tentative non créditable, l'action
« recommencer guide-only » archive d'abord de la même manière tout le diff de la
tentative, y compris les livrables du lab hors journal, puis crée depuis sa
baseline propre une branche qui n'a pas l'essai aidé pour ancêtre. Revue, CI,
jalons et journal sont remis à zéro. Il n'existe pas de simple interrupteur
permettant de rendre l'ancien essai créditable. La validation locale et la
publication recherchent `source-mode.json` dans toute l'ascendance de la
révision candidate : supprimer ensuite ce reçu sur la même branche ne retire
jamais la marque d'entraînement. Seule la nouvelle branche issue de la baseline
antérieure au taint peut redevenir créditable.

Les artefacts Git ignorés qui ne sont ni caches d'outillage ni emplacements
locaux sensibles sont empreintés au démarrage. Un fichier ignoré nouveau ou
modifié par la tentative aidée entre lui aussi dans l'archive et le nettoyage
borné ; `.learning`, les environnements virtuels, caches et emplacements de
secrets restent explicitement hors de cette opération.

Un statut `Bloqué` reste accessible sans CI ni revue. Il active une consolidation
sur une branche créée depuis la baseline antérieure au travail bloqué. Après
fusion de cette consolidation, la reprise repart sur une nouvelle branche qui
contient la correction consolidée, restaure seulement le journal appartenant à
l'apprenant et exige de nouveaux jalons, une nouvelle CI, une nouvelle revue et
une nouvelle preuve brute. L'ancienne branche n'entre pas dans son ascendance.
Le nom borné de la branche de consolidation et son reçu d'activation versionné
permettent de reconstruire cette transition même si le cache local disparaît.

Le générateur `tools/learning_publish.py` applique une liste blanche. Il vérifie
aussi `curriculum/active.json`, l'empreinte réelle du guide, le rapport d'audit
de la phase, l'activation des consolidations, la révision Git source et
l'ascendance des deux jalons. Le reçu minimal `.proof/raw-evidence.json` doit
confirmer deux copies, la politique de rétention et l'identifiant projeté dans
`proof.json` ; il n'est jamais recopié dans le dépôt de preuves. Le générateur
n'accepte que les résumés publics approuvés, assertions, erreur significative
corrigée, progression et
empreintes. Sa sortie doit être publiée dans un dépôt GitHub Pages séparé ;
guide, sources, journaux complets et preuves brutes sont interdits. Le registre
refuse également toute adresse IPv4/IPv6 et tout nom DNS : les résumés publics
ne mentionnent que des alias pseudonymes sans point. Il refuse aussi une
journée principale hors ordre, une consolidation de blocage
dont la journée déclencheuse est déjà publiée, et une consolidation finale tant
que J370 n'est pas publiée.

Le workflow réaffirme que le dépôt source et la cible sont publics mais
distincts, puis transmet le SHA du checkout source à la preuve publique. Cette
séparation conserve un registre de preuves minimal et immuable sans dupliquer
le guide, le code, les journaux complets ni les preuves brutes. Le champ source
lie la publication à la révision fusionnée sans tenter d'inscrire dans un
commit sa propre empreinte, opération intrinsèquement circulaire. Avant de
signer, il exige également une exécution réussie de `ci.yml` pour ce SHA et
refuse une exécution lancée depuis une autre branche que `master`.

Le workflow `publish-learning.yml` demande quatre variables GitHub :
`PUBLIC_PROOF_REPOSITORY` au format `propriétaire/dépôt`, les identifiants
numériques `PUBLIC_PROOF_BRANCH_RULESET_ID` et `PUBLIC_PROOF_TAG_RULESET_ID`,
ainsi que le SHA-256 attendu de la clé publique dans
`PUBLIC_PROOF_SIGNER_SHA256`. Cette clé doit être `ssh-ed25519` : SSHSIG produit
alors pour un même manifeste des octets déterministes, propriété nécessaire pour
reconstruire exactement le tree lors d'une reprise. Le premier ruleset cible
sans exclusion la branche publique par défaut et contient `deletion` et
`non_fast_forward`. Le second
cible exactement, sans exclusion, `refs/tags/aegis-proof-v1-*` et contient
`deletion` et `update` : la création du prochain tag reste permise, mais aucun
acteur ne peut ensuite le déplacer ou le supprimer. Tous deux doivent être
`active` et ne déclarer aucun `bypass_actor`. Le workflow vérifie aussi les
règles effectives renvoyées par GitHub pour la branche. L'API REST ne fournit
pas d'évaluation équivalente pour un tag ; son applicabilité est donc contrôlée
en mode fermé par l'identifiant du ruleset, sa cible `tag`, son motif unique
exact, l'absence d'exclusion et ses règles. Un ruleset en mode `evaluate` ne
suffit pas. Les releases immuables doivent être activées ; toute réponse API
requise absente ou ambiguë provoque un refus fermé.

La publication emploie quatre jobs et donc quatre runners GitHub hébergés
distincts. `build` ne reçoit aucun secret cible : il vérifie les SHA-256
littéraux de `learning_publish.py`, de sa dépendance `learn.py` et du gabarit
`site/public-proof.html`. Il copie ces trois entrées vérifiées en lecture seule
dans un répertoire isolé, passe explicitement le gabarit au publisher, puis
exécute celui-ci avec un environnement vide et Python en mode isolé. Il ne
transmet au job suivant qu'un artefact à liste blanche constitué de données et
d'un reçu portant les trois empreintes ; aucun script, dépôt `.git` ou
exécutable ne traverse cette frontière. Toute évolution d'une de ces trois
entrées exige donc une mise à jour relue de son empreinte dans le workflow.
Pour une consolidation, le publisher exige aussi le reçu versionné
`activation.json`, son égalité exacte avec l'activation de `proof.json` et sa
présence à la révision source. Une consolidation `blocked-day` est refusée si la
phase de sa journée déclencheuse n'est pas auditée pour la version du guide.

Le runner `sign` télécharge seulement cet artefact de données, le revalide avant
d'injecter `PUBLIC_PROOF_SIGNING_KEY`, contrôle la clé publique contre
`PUBLIC_PROOF_SIGNER_SHA256`, puis signe `manifest.json`. Le runner `policy`
possède seulement `PUBLIC_PROOF_POLICY_TOKEN`, jeton fin limité au dépôt public
avec `Administration: read`. Enfin, le runner `publish` ne checkout que le SHA
exact du dépôt public validé par `policy`, retélécharge l'artefact signé et le
traite uniquement comme des données. Il désactive explicitement les hooks Git
avant de créer le commit. Seule sa dernière étape reçoit
`PUBLIC_PROOF_TOKEN`, limité à `Contents: write`, pour créer le tag et la
release puis effectuer le fast-forward. Les deux jetons sont refusés si leurs
SHA-256 sont identiques. Les checkouts utilisent
`persist-credentials: false`.

Cette séparation de runners est une propriété de sécurité, pas seulement une
présentation du workflow. Deux étapes d'un même job partagent le même système :
un programme lancé plus tôt pourrait préparer `GITHUB_ENV`, `GITHUB_PATH` ou
`BASH_ENV`, installer un hook Git ou laisser un processus de fond qui observera
les secrets d'une étape ultérieure. Aucun code du dépôt source ne s'exécute sur
les runners qui détiennent la clé de signature ou les jetons du dépôt public.

Chaque ligne N du registre possède une ancre `aegis-proof-v1-NNNNNN`. Son tag
pointe vers le SHA exact du commit public. Le corps JSON de la release relie la
séquence, ce SHA, l'ancre précédente et les SHA-256 de `ledger.jsonl`,
`manifest.json`, `manifest.json.sig` et `signer.pub`. Ces quatre fichiers sont
aussi les quatre assets exacts de la release. Le workflow contrôle les digests
calculés par GitHub, retélécharge les assets, revérifie leurs octets et la
signature SSH, puis compare leurs blobs au commit tagué. Une séquence manquante,
dupliquée, future ou modifiable est refusée.

La transaction pousse d'abord le commit sous ce tag déterministe, prépare la
release en brouillon avec ses quatre assets, la publie et exige ensuite
`immutable: true`. La branche publique n'avance qu'après ces vérifications, par
un push fast-forward sans force. Après que la release est devenue immuable, le
workflow relit le ref de tag depuis GitHub dans un nouveau ref local et exige
que son objet puis son commit soient identiques à ceux contrôlés avant la
release. Il répète ce CAS immédiatement avant et après l'avance de branche. Si
l'exécution s'arrête après la publication de la release mais avant ce dernier
push, la relance accepte uniquement l'ancre N immuable dont le commit a
exactement la branche N−1 comme parent, le même tree que la preuve reconstruite
et les mêmes assets ; elle avance alors la branche vers ce commit déjà ancré. Un
brouillon incomplet n'est repris que si son tag, son parent et son tree sont ceux
attendus. Cette politique doit être en place dès la première ligne : un registre
public préexistant sans releases N=1…N n'est pas adopté silencieusement.

La signature du manifeste authentifie son contenu, mais ne prouve pas à elle
seule qu'il s'agit de l'état le plus récent. La garantie anti-rollback repose
donc explicitement sur GitHub comme racine de confiance : runners hébergés neufs
pour chaque job secret, service d'artefacts, maintien des deux rulesets sans
bypass, sémantique des releases immuables et contrôle d'accès aux comptes
administrateurs. Il reste une courte fenêtre entre la lecture de la politique
et la mutation ; un administrateur GitHub capable de désactiver puis réactiver
ces protections se trouve hors de cette garantie. Les permissions minimales des
jetons sont elles aussi une configuration protégée, car l'API ne fournit pas de
preuve négative fiable qu'un jeton `Contents: write` ne possède aucune autre
permission. Le principal portant `PUBLIC_PROOF_TOKEN` doit être l'unique
écrivain `Contents: write` de la cible : un autre écrivain pourrait courir sur
la branche ou publier le brouillon avant sa vérification, rendant la séquence N
irrécupérable. Il ne pourrait pas forger la signature, mais cette disponibilité
est hors de la garantie. Une preuve indépendante de GitHub exigerait en plus un
moniteur ou un stockage WORM externe conservant la dernière ancre. Les règles
de protection du dépôt source doivent elles aussi être configurées séparément.

## Évolution du guide

`v1.0.0` reste immuable et non créditable. Une correction du guide actif suit
SemVer, actualise le manifeste et régénère `learning/roadmap.md`. Chaque version
créditable gèle sa propre liste de phases et ses propres empreintes de rapports
d'audit ; une activation ultérieure ne réécrit donc pas la validité des preuves
historiques. Une phase future n'est ajoutée qu'après sa revue complète. Le
professeur peut préparer un correctif ; l'apprenant le relit et crée le commit
correspondant.
