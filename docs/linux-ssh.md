# Linux et SSH

## Objectif du document

Ce document regroupe mes notes sur Linux et SSH.

Le but est de comprendre comment observer, contrôler et administrer une machine Linux, localement ou à distance.

SSH est une base importante pour le DevOps, l’administration système, l’automatisation et le Network Automation.

Avant d’automatiser une machine, je dois être capable de m’y connecter, de l’observer et de comprendre son état.

---

## Définition simple de Linux

Linux est un système d’exploitation.

Il permet de gérer :

- les fichiers ;
- les utilisateurs ;
- les permissions ;
- les processus ;
- les services ;
- le réseau ;
- les logs ;
- les logiciels installés.

Dans mon projet, Linux sert de base pour faire tourner les outils comme Git, Python, Docker, Ansible, Codex CLI et plus tard OpenClaw.

---

## Définition simple de SSH

SSH signifie Secure Shell.

C’est un moyen sécurisé de se connecter à une machine distante en ligne de commande.

Exemple :

ssh utilisateur@adresse_ip

Cela veut dire :

Je veux ouvrir une session sur une machine distante, avec un utilisateur précis, en utilisant le protocole SSH.

---

## Exemple de commande SSH

ssh thomas@192.168.1.50

Explication :

ssh  
Programme utilisé pour se connecter à distance.

thomas  
Nom d’utilisateur sur la machine distante.

@  
Sépare le nom d’utilisateur et l’adresse de la machine.

192.168.1.50  
Adresse IP de la machine distante.

---

## Différence entre local et distant

### Machine locale

La machine locale est l’ordinateur sur lequel je suis directement.

Exemple :

hostname

Cette commande affiche le nom de la machine actuelle.

### Machine distante

La machine distante est une autre machine à laquelle je me connecte avec SSH.

Exemple :

ssh thomas@192.168.1.50

Puis :

hostname

Dans ce cas, la commande `hostname` s’exécute sur la machine distante, pas sur mon ordinateur local.

---

## Pourquoi SSH est important dans mon projet

SSH est important parce qu’il permet de :

- se connecter à un serveur ;
- administrer une machine sans interface graphique ;
- lancer des commandes à distance ;
- copier des fichiers ;
- vérifier l’état d’un système ;
- préparer l’automatisation avec Ansible ;
- comprendre la différence entre mon poste local, un serveur distant et un futur VPS.

Dans mon projet, SSH sera utile pour contrôler un lab local ou un VPS.

---

## Commandes Linux de base

### Savoir où je suis

pwd

Cette commande affiche le dossier dans lequel je me trouve.

Exemple de résultat :

/home/thomas/labs/infra-dev-cyber-ai-learning-lab

---

### Lister les fichiers

ls

Affiche les fichiers du dossier actuel.

ls -l

Affiche les fichiers avec plus de détails.

ls -la

Affiche aussi les fichiers cachés.

Explication :

-l  
Affichage détaillé.

-a  
Affiche tous les fichiers, y compris les fichiers cachés.

---

### Changer de dossier

cd nom_du_dossier

Permet d’entrer dans un dossier.

cd ..

Permet de revenir au dossier parent.

cd ~

Permet de revenir dans le dossier personnel de l’utilisateur.

---

### Créer un dossier

mkdir docs

Crée un dossier nommé `docs`.

mkdir -p dossier/sous-dossier

Crée aussi les dossiers parents si nécessaire.

---

### Créer un fichier vide

touch fichier.txt

Cette commande crée un fichier vide si le fichier n’existe pas déjà.

---

### Lire un fichier

cat fichier.txt

Affiche tout le contenu du fichier directement dans le terminal.

less fichier.txt

Permet de lire le fichier page par page.

Différence :

`cat` est pratique pour les petits fichiers.

`less` est plus pratique pour les fichiers longs.

---

### Modifier un fichier

nano fichier.txt

Ouvre le fichier avec l’éditeur Nano.

Commandes utiles dans Nano :

Ctrl + O  
Enregistrer.

Entrée  
Confirmer le nom du fichier.

Ctrl + X  
Quitter.

---

## Commandes système utiles

### Voir le nom de la machine

hostname

Affiche le nom court de la machine.

hostnamectl

Affiche plus d’informations sur le système.

---

### Voir la version du noyau Linux

uname -a

Cette commande affiche des informations sur le noyau Linux.

Elle permet de savoir sur quel type de système je travaille.

---

### Voir l’espace disque

df -h

Explication :

df  
Affiche l’espace disque.

-h  
Affiche les tailles dans un format lisible par un humain.

Cette commande permet de vérifier si le disque est presque plein.

---

### Voir la mémoire

free -h

Cette commande affiche l’utilisation de la mémoire RAM.

---

### Voir les processus

ps aux

Cette commande affiche les processus en cours d’exécution.

Un processus est un programme en train de tourner sur la machine.

---

## Commandes réseau utiles

### Voir les interfaces réseau

ip a

Cette commande affiche les interfaces réseau de la machine.

Elle permet de voir :

- les cartes réseau ;
- les adresses IP ;
- l’état des interfaces ;
- les interfaces actives ou inactives.

Une interface réseau peut être vue comme une porte réseau de la machine.

---

### Voir les routes réseau

ip route

Cette commande affiche les routes utilisées par la machine.

Une route indique par où les paquets réseau doivent passer.

La route par défaut indique le chemin utilisé quand la machine veut aller vers Internet ou vers un réseau non directement connu.

---

### Tester la connectivité

ping 8.8.8.8

Teste si la machine peut joindre l’adresse IP 8.8.8.8.

ping google.com

Teste si la machine peut joindre `google.com`.

Différence importante :

ping 8.8.8.8  
Teste surtout la connectivité IP.

ping google.com  
Teste aussi la résolution DNS, car le nom doit être transformé en adresse IP.

---

### Voir les ports ouverts

ss -tulpn

Cette commande affiche les ports en écoute sur la machine.

Explication :

ss  
Outil qui affiche les sockets réseau.

-t  
Affiche le TCP.

-u  
Affiche l’UDP.

-l  
Affiche seulement les ports en écoute.

-p  
Affiche le processus lié au port.

-n  
Affiche les numéros au lieu des noms.

Cette commande est très importante pour comprendre quels services sont disponibles sur une machine.

---

## Différence entre service, processus et port

### Processus

Un processus est un programme en cours d’exécution.

Exemple :

python

docker

ssh

nginx

### Service

Un service est un programme géré par le système, souvent avec systemd.

Exemple :

ssh.service

docker.service

nginx.service

### Port

Un port est un point d’entrée réseau utilisé par un service.

Exemple :

Port 22  
Souvent utilisé pour SSH.

Port 80  
Souvent utilisé pour HTTP.

Port 443  
Souvent utilisé pour HTTPS.

Port 8000  
Souvent utilisé pour une application web de test ou une API locale.

---

## Services Linux avec systemd

### Voir l’état d’un service

systemctl status nom_du_service

Exemple :

systemctl status ssh

Cette commande permet de savoir si le service SSH fonctionne.

---

### Voir les services en échec

systemctl --failed

Cette commande affiche les services qui ont rencontré un problème.

---

### Démarrer un service

sudo systemctl start nom_du_service

Exemple :

sudo systemctl start ssh

---

### Arrêter un service

sudo systemctl stop nom_du_service

Exemple :

sudo systemctl stop ssh

Attention : arrêter SSH sur une machine distante peut me déconnecter ou m’empêcher de revenir.

---

### Redémarrer un service

sudo systemctl restart nom_du_service

Exemple :

sudo systemctl restart ssh

Attention : redémarrer SSH à distance doit être fait prudemment.

---

### Activer un service au démarrage

sudo systemctl enable nom_du_service

Cette commande permet à un service de démarrer automatiquement au démarrage de la machine.

---

## Lire les logs

### Voir les derniers logs du système

journalctl -n 100

Affiche les 100 dernières lignes de logs.

### Voir les logs d’un service précis

journalctl -u ssh -n 100

Affiche les 100 dernières lignes de logs du service SSH.

Explication :

journalctl  
Outil pour lire les logs systemd.

-u  
Filtre par service.

-n 100  
Affiche les 100 dernières lignes.

Les logs sont importants parce qu’ils permettent de comprendre ce qui s’est passé sur la machine.

---

## Les utilisateurs et les permissions

Linux fonctionne avec des utilisateurs et des droits.

Chaque fichier appartient à un utilisateur et souvent à un groupe.

### Voir qui je suis

whoami

Cette commande affiche le nom de l’utilisateur actuel.

---

### Voir les droits d’un fichier

ls -l

Exemple de résultat :

-rw-r--r-- 1 thomas thomas 1200 mai 15 10:30 fichier.txt

La première partie indique les permissions.

---

### Comprendre les permissions simplement

r  
read : droit de lire.

w  
write : droit d’écrire ou modifier.

x  
execute : droit d’exécuter.

Exemple :

rwx  
Lire, écrire et exécuter.

r--  
Lire seulement.

---

### Rendre un script exécutable

chmod +x scripts/diagnostic_local.sh

Cette commande ajoute le droit d’exécution au script.

Ensuite, je peux lancer le script avec :

./scripts/diagnostic_local.sh

---

## sudo

sudo permet d’exécuter une commande avec des droits administrateur.

Exemple :

sudo systemctl status ssh

Attention : sudo donne plus de pouvoir. Il faut comprendre la commande avant de l’utiliser.

Dans mon projet, je dois éviter les commandes sudo générales si je ne comprends pas précisément leur effet.

---

## Clé SSH

Une clé SSH permet de se connecter plus proprement qu’avec un mot de passe.

Elle fonctionne avec deux fichiers :

clé privée  
Elle reste sur mon ordinateur. Elle ne doit jamais être partagée.

clé publique  
Elle peut être copiée sur la machine distante.

---

## Générer une clé SSH

ssh-keygen

Cette commande génère une paire de clés SSH.

Les fichiers sont généralement créés dans :

~/.ssh/

Exemples :

~/.ssh/id_ed25519  
Clé privée.

~/.ssh/id_ed25519.pub  
Clé publique.

La clé privée ne doit jamais être envoyée, copiée dans Git ou partagée.

---

## Copier une clé SSH sur une machine distante

ssh-copy-id utilisateur@adresse_ip

Exemple :

ssh-copy-id thomas@192.168.1.50

Après cette commande, je peux souvent me connecter sans taper le mot de passe de l’utilisateur distant.

---

## Copier un fichier avec SCP

SCP permet de copier des fichiers entre deux machines en utilisant SSH.

### Copier un fichier local vers une machine distante

scp fichier.txt thomas@192.168.1.50:/home/thomas/

### Copier un fichier distant vers ma machine locale

scp thomas@192.168.1.50:/home/thomas/fichier.txt .

Le point final signifie :

Copie le fichier dans le dossier actuel.

---

## Sécurité SSH

Règles importantes :

- ne jamais partager ma clé privée ;
- ne jamais mettre une clé privée dans Git ;
- éviter la connexion directe en root ;
- garder une deuxième session ouverte avant de modifier SSH ;
- vérifier les ports ouverts ;
- documenter les changements ;
- ne pas modifier une configuration SSH que je ne comprends pas.

Si je casse SSH sur une machine distante, je peux perdre l’accès à cette machine.

---

## Exercice 1 — Observer ma machine Linux

Objectif :

Comprendre l’état de base de ma machine.

Commandes à lancer :

hostnamectl

uname -a

whoami

pwd

df -h

free -h

ip a

ip route

ss -tulpn

systemctl --failed

Questions à me poser :

- Quel est le nom de ma machine ?
- Quel utilisateur suis-je ?
- Quelle est mon adresse IP ?
- Quelle est ma route par défaut ?
- Quels ports sont ouverts ?
- Y a-t-il des services en échec ?
- Le disque est-il presque plein ?
- La mémoire semble-t-elle suffisante ?

---

## Exercice 2 — Comprendre local et distant

Objectif :

Savoir si une commande s’exécute sur ma machine locale ou sur une machine distante.

Étapes :

1. Sur ma machine locale, lancer :

hostname

2. Me connecter en SSH à une machine distante :

ssh utilisateur@adresse_ip

3. Sur la machine distante, lancer :

hostname

4. Comparer les résultats.

5. Quitter la session distante avec :

exit

Ce que je dois comprendre :

Quand je suis connecté en SSH, les commandes s’exécutent sur la machine distante.

---

## Exercice 3 — Créer une note de diagnostic

Créer un fichier :

docs/diagnostic-linux.md

Y noter :

Nom de la machine :

Utilisateur :

Adresse IP :

Route par défaut :

Ports ouverts :

Services en échec :

Espace disque :

Mémoire disponible :

Commentaires :

Objectif :

M’habituer à transformer des commandes terminal en documentation claire.

---

## Exercice 4 — Tester SSH proprement

Objectif :

Comprendre une connexion SSH simple.

Commande :

ssh utilisateur@adresse_ip

Puis lancer :

whoami

hostname

ip a

exit

Ce que je dois vérifier :

- Est-ce que je me connecte avec le bon utilisateur ?
- Est-ce que je suis sur la bonne machine ?
- Est-ce que je sais quitter la session SSH ?
- Est-ce que je comprends ce que j’ai fait ?

---

## Exercice 5 — Vérifier les ports ouverts

Objectif :

Comprendre quels services écoutent sur la machine.

Commande :

ss -tulpn

À observer :

- les ports TCP ;
- les ports UDP ;
- les services en écoute ;
- les adresses d’écoute ;
- les processus associés.

Questions :

- Est-ce que SSH écoute ?
- Sur quel port ?
- Y a-t-il un service web ?
- Est-ce qu’un service écoute sur toutes les interfaces ?
- Est-ce qu’un service écoute seulement en local ?

---

## Ce que je dois savoir expliquer

À la fin de cette partie, je dois être capable d’expliquer simplement :

- ce qu’est Linux ;
- ce qu’est SSH ;
- ce qu’est une machine locale ;
- ce qu’est une machine distante ;
- ce qu’est une adresse IP ;
- ce qu’est une interface réseau ;
- ce qu’est une route ;
- ce qu’est un port ouvert ;
- ce qu’est un processus ;
- ce qu’est un service ;
- ce que fait systemd ;
- ce que sont les logs ;
- pourquoi une clé privée doit rester secrète ;
- pourquoi SSH est important pour le DevOps ;
- pourquoi il faut observer avant d’automatiser.

---

## Résumé personnel

Linux est la base technique de mon projet.

SSH me permet de contrôler une machine à distance de façon sécurisée.

Avant de faire du DevOps, de l’automatisation ou du Network Automation avancé, je dois savoir observer une machine, comprendre ses services, ses ports, ses logs et son réseau.

Mon objectif n’est pas seulement de lancer des commandes.

Mon objectif est de comprendre ce que chaque commande m’apprend sur l’état du système.
