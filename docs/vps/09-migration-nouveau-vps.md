# 09 - Migration vers un nouveau VPS

Objectif : préparer une migration prudente vers un nouveau VPS avec le même OS,
sans mettre de secret dans Git et sans supprimer l'ancien serveur avant
validation.

## Termes simples

- **Ancien VPS** : serveur actuel, encore utilisé.
- **Nouveau VPS** : serveur cible, à préparer puis tester.
- **Secret** : mot de passe, token, clé privée, fichier `.env` réel ou secret
  OIDC. Un secret ne doit jamais être copié dans Git.
- **Rollback** : retour arrière si la migration échoue. Ici, cela veut dire
  garder l'ancien VPS prêt et remettre le DNS vers lui si besoin.
- **DNS** : réglage qui fait pointer un domaine vers une adresse IP.

## Principe de migration

- Le code applicatif migre par Git : clone du dépôt puis checkout d'un commit ou
  tag validé.
- Les secrets migrent hors Git : fichiers privés, permissions strictes, jamais
  affichés dans les logs.
- Les données générées migrent par sauvegarde/restauration après revue.
- Les conteneurs Docker et les images locales ne sont pas à copier : ils se
  reconstruisent depuis le dépôt.
- La bascule DNS arrive seulement après tests locaux et tests HTTPS.

## Analyse avant modification

Sur l'ancien VPS, relever sans afficher de secret :

```bash
git branch --show-current
git rev-parse --short HEAD
make migration-check
```

Si le mode public est déjà utilisé, charger les variables privées dans le shell
hors dépôt, puis lancer :

```bash
make migration-check-public
```

À migrer si utilisé :

- commit ou tag Git validé ;
- fichier `.env` privé réel, hors dépôt ;
- fichiers secrets OIDC : client secret et cookie secret ;
- certificats mTLS dans `/etc/infra-lab/mtls` ou nouveau jeu mTLS régénéré ;
- certificat HTTPS public et clé privée associée ;
- rapports revus dans `outputs/reports/` si utiles ;
- configuration DNS chez le fournisseur DNS.

À ne pas migrer tel quel :

- `.venv/`, caches Python, caches Docker ;
- conteneurs Docker arrêtés ou images locales ;
- `outputs/raw/`, `outputs/rendered/`, `outputs/backups/` sans revue ;
- clés privées SSH, tokens cloud, fichiers `.env` réels dans Git ;
- volume Postgres sauf si le profil `future-persistence` a été activé
  volontairement.

## Préparer le nouveau VPS

Suivre les documents dans l'ordre :

1. [Première connexion](01-premiere-connexion.md)
2. [Sécurisation SSH](02-securisation-ssh.md)
3. [Firewall](03-firewall.md)
4. [Installation Docker](04-install-docker.md)

Cloner ensuite le dépôt avec un commit validé :

```bash
git clone <URL_DU_DEPOT> infra-dev-cyber-ai-learning-lab
cd infra-dev-cyber-ai-learning-lab
git checkout <COMMIT_OU_TAG_VALIDE>
make migration-check
```

Si cette commande échoue, corriger d'abord le prérequis indiqué. Elle ne démarre
pas de service.

## Préparer les fichiers privés

Créer ou restaurer les fichiers privés hors dépôt. Les chemins attendus par les
exemples sont :

```text
/etc/infra-lab/mtls/
/etc/infra-lab/public-tls/
/var/lib/infra-lab/oauth2-proxy/
<CHEMIN_PRIVE_ENV_VPS>
<CHEMIN_PRIVE_OIDC_CLIENT_SECRET>
<CHEMIN_PRIVE_OIDC_COOKIE_SECRET>
```

Actions privilégiées : relire chaque commande avant exécution, garder une session
SSH ouverte, puis confirmer manuellement. Ne jamais coller le contenu des secrets
dans un ticket, un commit ou une sortie de terminal partagée.

Pour mTLS, deux options :

- régénérer un nouveau jeu mTLS avec `MTLS_GENERATE_CONFIRM=yes` si aucune
  compatibilité avec l'ancien jeu n'est nécessaire ;
- copier le jeu existant par un canal sûr si la continuité exacte est requise.

Vérification attendue :

```bash
MTLS_DIR=/etc/infra-lab/mtls make mtls-check
```

## Restaurer les données utiles

Pour ce dépôt, les données applicatives importantes sont surtout les rapports
revus. Les logs sont optionnels et peuvent contenir des informations sensibles.

Méthode recommandée :

1. créer une sauvegarde Restic vérifiée sur l'ancien VPS ;
2. lancer `restic snapshots` et `restic check` ;
3. restaurer d'abord dans `/tmp` sur le nouveau VPS ;
4. copier seulement les fichiers revus vers `outputs/reports/`.

Ne pas restaurer directement par-dessus le dépôt courant.

Si le profil Compose `future-persistence` a été activé, traiter Postgres comme
une migration séparée : dump sur l'ancien VPS, restauration sur le nouveau VPS,
puis test applicatif. Par défaut, ce profil n'est pas actif.

## Tester avant la bascule DNS

Sur le nouveau VPS :

```bash
make migration-check
```

Pour le mode public, charger les variables privées hors dépôt puis vérifier :

```bash
make migration-check-public
make public-config
PUBLIC_URL='https://<LAB_DOMAIN>' make public-health
```

`public-health` suppose que le service public a été démarré après revue
manuelle, par exemple via `make public-up` ou l'unité systemd préparée. Le
démarrage réel modifie l'état du VPS : le confirmer explicitement avant action.

Contrôles attendus :

- `/health` répond en HTTPS ;
- `/version` répond avec la version attendue ;
- `/diag` sans authentification n'est pas public ;
- `/diag` avec OIDC respecte les rôles attendus ;
- le port FastAPI 8000 reste local au serveur ;
- aucun secret réel n'apparaît dans Git ou dans les logs partagés.

## Bascule

Ne pas éteindre l'ancien VPS avant validation du nouveau.

Ordre conseillé :

1. réduire le TTL DNS à l'avance si le fournisseur DNS le permet ;
2. démarrer le nouveau service ;
3. vérifier `https://<LAB_DOMAIN>/health` ;
4. modifier le DNS vers l'IP du nouveau VPS ;
5. re-tester depuis un réseau extérieur ;
6. garder l'ancien VPS disponible pendant la période d'observation.

Rollback simple :

1. remettre le DNS vers l'ancien VPS ;
2. vérifier `https://<LAB_DOMAIN>/health` côté ancien VPS ;
3. analyser le problème sur le nouveau VPS sans supprimer les données.

## Vérification finale

Checklist minimale :

- `make migration-check` passe sur le nouveau VPS ;
- `make migration-check-public` passe si le mode public est utilisé ;
- DNS pointe vers le nouveau VPS ;
- HTTPS fonctionne ;
- `/diag` reste protégé ;
- les rapports utiles sont présents ;
- une sauvegarde post-migration existe ;
- l'ancien VPS n'est supprimé qu'après validation manuelle.
