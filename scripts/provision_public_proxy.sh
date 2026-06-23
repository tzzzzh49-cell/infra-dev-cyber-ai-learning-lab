#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MTLS_DIR="${MTLS_DIR:-/etc/infra-lab/mtls}"
OAUTH2_SOCKET_DIR="${OAUTH2_SOCKET_DIR:-/var/lib/infra-lab/oauth2-proxy}"
PUBLIC_TLS_DIR="${PUBLIC_TLS_DIR:-/etc/infra-lab/public-tls}"
UNIT_NAME="infra-lab-public-proxy.service"
UNIT_TEMPLATE="$PROJECT_ROOT/systemd/$UNIT_NAME.in"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"
SERVICE_GROUP="${SERVICE_GROUP:-$(id -gn "$SERVICE_USER" 2>/dev/null || true)}"

if [ "${APPLY_CONFIRM:-}" != "yes" ]; then
    cat >&2 <<'EOF'
Erreur : ce script crée une autorité mTLS locale, installe une unité systemd
et réinitialise UFW pour n'autoriser en entrée que 22/tcp, 80/tcp et 443/tcp.

Garde une session SSH de secours, relis le script, puis lance :
  APPLY_CONFIRM=yes ./scripts/provision_public_proxy.sh

Le certificat HTTPS public reste externe au dépôt. Utilise <LAB_DOMAIN> et
<ADMIN_EMAIL> avec ton client ACME, puis configure PUBLIC_TLS_CERT_FILE et
PUBLIC_TLS_KEY_FILE hors Git.
EOF
    exit 2
fi

if [ "$SERVICE_USER" = "root" ] || [ -z "$SERVICE_GROUP" ]; then
    echo "Erreur : SERVICE_USER doit désigner un utilisateur non-root existant." >&2
    exit 2
fi

case "$SERVICE_USER:$SERVICE_GROUP" in
    *[!A-Za-z0-9_.:-]*)
        echo "Erreur : nom d'utilisateur ou de groupe invalide." >&2
        exit 2
        ;;
esac

for command in docker openssl sed sudo systemctl ufw usermod; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Erreur : commande manquante : $command" >&2
        exit 1
    fi
done

if ! docker compose version >/dev/null 2>&1; then
    echo "Erreur : le plugin Docker Compose est introuvable." >&2
    exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "Erreur : utilisateur introuvable : $SERVICE_USER" >&2
    exit 1
fi

echo "==> Validation des privilèges sudo"
sudo -v

echo "==> Création des certificats mTLS internes"
sudo install -d -o root -g 10001 -m 0750 "$MTLS_DIR"

certificates=(ca.key ca.crt api.key api.crt nginx-client.key nginx-client.crt)
existing=0
for certificate in "${certificates[@]}"; do
    if sudo test -e "$MTLS_DIR/$certificate"; then
        existing=$((existing + 1))
    fi
done

if [ "$existing" -ne 0 ] && [ "$existing" -ne "${#certificates[@]}" ]; then
    echo "Erreur : état mTLS partiel dans $MTLS_DIR ; aucune clé n'a été écrasée." >&2
    exit 1
fi

if [ "$existing" -eq 0 ]; then
    sudo openssl req -x509 -newkey rsa:4096 -sha256 -nodes -days 3650 \
        -subj "/CN=infra-lab-service-ca" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" \
        -keyout "$MTLS_DIR/ca.key" -out "$MTLS_DIR/ca.crt"

    sudo openssl req -new -newkey rsa:3072 -sha256 -nodes \
        -subj "/CN=api" \
        -addext "subjectAltName=DNS:api,DNS:localhost,IP:127.0.0.1" \
        -addext "extendedKeyUsage=serverAuth,clientAuth" \
        -keyout "$MTLS_DIR/api.key" -out "$MTLS_DIR/api.csr"
    sudo openssl x509 -req -sha256 -days 365 \
        -in "$MTLS_DIR/api.csr" \
        -CA "$MTLS_DIR/ca.crt" -CAkey "$MTLS_DIR/ca.key" -CAcreateserial \
        -copy_extensions copy -out "$MTLS_DIR/api.crt"

    sudo openssl req -new -newkey rsa:3072 -sha256 -nodes \
        -subj "/CN=nginx" \
        -addext "extendedKeyUsage=clientAuth" \
        -keyout "$MTLS_DIR/nginx-client.key" \
        -out "$MTLS_DIR/nginx-client.csr"
    sudo openssl x509 -req -sha256 -days 365 \
        -in "$MTLS_DIR/nginx-client.csr" \
        -CA "$MTLS_DIR/ca.crt" -CAkey "$MTLS_DIR/ca.key" \
        -CAserial "$MTLS_DIR/ca.srl" -copy_extensions copy \
        -out "$MTLS_DIR/nginx-client.crt"

    sudo rm -f "$MTLS_DIR/api.csr" "$MTLS_DIR/nginx-client.csr"
fi

sudo chown root:root "$MTLS_DIR/ca.key"
sudo chown root:10001 "$MTLS_DIR/api.key" "$MTLS_DIR/nginx-client.key"
sudo chmod 0600 "$MTLS_DIR/ca.key"
sudo chmod 0440 "$MTLS_DIR/api.key" "$MTLS_DIR/nginx-client.key"
sudo chmod 0444 "$MTLS_DIR/ca.crt" "$MTLS_DIR/api.crt" "$MTLS_DIR/nginx-client.crt"
sudo openssl verify -CAfile "$MTLS_DIR/ca.crt" \
    "$MTLS_DIR/api.crt" "$MTLS_DIR/nginx-client.crt"

echo "==> Préparation du socket privé OAuth2 Proxy"
sudo install -d -o 65532 -g 10001 -m 2770 "$OAUTH2_SOCKET_DIR"
sudo install -d -o root -g 10001 -m 0750 "$PUBLIC_TLS_DIR"

echo "==> Installation du service systemd non-root"
sudo usermod -aG docker "$SERVICE_USER"
unit_tmp="$(mktemp)"
trap 'rm -f "$unit_tmp"' EXIT
sed \
    -e "s|<SERVICE_USER>|$SERVICE_USER|g" \
    -e "s|<SERVICE_GROUP>|$SERVICE_GROUP|g" \
    -e "s|<PROJECT_ROOT>|$PROJECT_ROOT|g" \
    "$UNIT_TEMPLATE" >"$unit_tmp"
sudo install -o root -g root -m 0644 "$unit_tmp" "/etc/systemd/system/$UNIT_NAME"
sudo systemctl daemon-reload
sudo systemctl enable "$UNIT_NAME"

echo "==> Application du pare-feu UFW"
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment SSH
sudo ufw allow 80/tcp comment HTTP
sudo ufw allow 443/tcp comment HTTPS
sudo ufw --force enable
sudo ufw status verbose

cat <<EOF

Provisionnement terminé sans démarrer les services.
Vérifie d'abord les certificats HTTPS publics et les paramètres OIDC hors Git.
Installe fullchain.pem (0444) et privkey.pem (root:10001, 0440) dans $PUBLIC_TLS_DIR.
Puis démarre explicitement avec : sudo systemctl start $UNIT_NAME
EOF
