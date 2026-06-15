#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
. /etc/os-release

if [ "${ID:-}" != "ubuntu" ] || [ "${VERSION_ID:-}" != "26.04" ]; then
    echo "Erreur : ce script cible Ubuntu 26.04 LTS Server uniquement." >&2
    echo "Distribution détectée : ${PRETTY_NAME:-inconnue}" >&2
    exit 1
fi

echo "==> Mise à jour de l'index APT"
sudo apt-get update

echo "==> Installation des outils de base"
sudo apt-get install -y   ca-certificates   curl   git   jq   make   python3   python3-pip   python3-venv   ansible   shellcheck

echo "==> Suppression éventuelle d'anciens paquets Docker conflictuels"
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
  sudo apt-get remove -y "$pkg" || true
done

echo "==> Ajout du dépôt Docker officiel"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable"   | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

echo "==> Installation Docker Engine + Compose plugin"
sudo apt-get update
sudo apt-get install -y   docker-ce   docker-ce-cli   containerd.io   docker-buildx-plugin   docker-compose-plugin

echo "==> Activation de Docker"
sudo systemctl enable --now docker

echo "==> Ajout de l'utilisateur courant au groupe docker"
sudo usermod -aG docker "$USER"

echo
echo "Installation terminée."
echo "IMPORTANT : déconnecte-toi/reconnecte-toi dans la VM."
echo
echo "Puis vérifie :"
echo "  docker --version"
echo "  docker compose version"
echo "  ansible --version"
echo "  make check"
