#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
. /etc/os-release

if [ "${ID:-}" != "fedora" ] || [ "${VERSION_ID:-}" != "44" ]; then
    echo "Erreur : ce script cible Fedora 44 Workstation VM uniquement." >&2
    echo "Distribution détectée : ${PRETTY_NAME:-inconnue}" >&2
    exit 1
fi

if [ "${BOOTSTRAP_CONFIRM:-}" != "yes" ]; then
    echo "Erreur : ce script modifie le système avec sudo." >&2
    echo "Relance après revue avec : BOOTSTRAP_CONFIRM=yes $0" >&2
    exit 2
fi

echo "==> Mise à jour de Fedora"
sudo dnf -y update

echo "==> Installation des outils de base"
sudo dnf -y install   git   curl   wget   vim   nano   tree   jq   make   python3   python3-pip   python3-virtualenv   ansible   ShellCheck   dnf-plugins-core

echo "==> Suppression éventuelle d'anciens paquets Docker conflictuels"
sudo dnf -y remove   docker   docker-client   docker-client-latest   docker-common   docker-latest   docker-latest-logrotate   docker-logrotate   docker-selinux   docker-engine-selinux   docker-engine || true

echo "==> Ajout du dépôt Docker officiel"
sudo dnf config-manager addrepo --from-repofile https://download.docker.com/linux/fedora/docker-ce.repo

echo "==> Installation Docker Engine + Compose plugin"
sudo dnf -y install   docker-ce   docker-ce-cli   containerd.io   docker-buildx-plugin   docker-compose-plugin

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
