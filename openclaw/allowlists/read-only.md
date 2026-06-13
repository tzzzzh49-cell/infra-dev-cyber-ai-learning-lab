# Allowlist OpenClaw — mode read-only

## Principe

Statut : proposition documentaire non active.

Par défaut, tout est interdit.

Seules les commandes explicitement listées ici pourront être autorisées plus tard.

OpenClaw ne doit pas exécuter de commande shell libre.
OpenClaw ne doit pas accepter de commande destructive.
OpenClaw ne doit pas modifier le réseau au début du projet.
OpenClaw ne doit pas exécuter automatiquement une commande sans validation humaine explicite.

## Commandes autorisées au départ

### Diagnostic local

Commande utilisateur :

diagnostic lab

Commande proposée pour revue humaine :

./scripts/diagnostic_local.sh

Niveau de risque :

faible

Raison :

lecture d’état uniquement + génération d’un rapport Markdown, après validation humaine.

## Commandes éventuellement autorisées plus tard

### Vérification API locale

curl -fsS http://127.0.0.1:8000/health

Niveau de risque :

faible

Raison :

vérifie seulement que l’API locale répond.

### Diagnostic Ansible en mode contrôle

ansible-playbook -i ansible/inventory.yml ansible/playbooks/diagnostic.yml --check

Niveau de risque :

faible à moyen

Raison :

mode contrôle, sans application volontaire de changement.

À autoriser seulement après test manuel.

## Interdits permanents au début

Interdit :

rm
rm -rf
sudo
sudo su
bash
sh
curl | bash
wget | bash
chmod -R 777
chown -R
ip link set
ip route add
ip route del
iptables
nft
firewall-cmd
docker stop
docker rm
docker system prune
terraform apply
terraform destroy
kubectl delete
kubectl apply

## Règle simple

Si une commande modifie l’état du système, du réseau, de Docker, de Terraform, de Kubernetes ou d’Ansible, elle est interdite au début.
