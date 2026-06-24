#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MTLS_DIR="${MTLS_DIR:-/etc/infra-lab/mtls}"

if [ "${MTLS_GENERATE_CONFIRM:-}" != "yes" ]; then
    echo "Erreur : cette commande crée une autorité et des clés privées mTLS dans $MTLS_DIR." >&2
    echo "Après lecture du script, relance avec MTLS_GENERATE_CONFIRM=yes." >&2
    exit 2
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Erreur : exécute ce script avec sudo pour créer des fichiers root:10001." >&2
    exit 2
fi

for command in chmod chown openssl install mktemp; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Erreur : commande manquante : $command" >&2
        exit 1
    fi
done

files=(ca.key ca.crt api.key api.crt nginx-client.key nginx-client.crt)
existing=0

if [ -L "$MTLS_DIR" ] || { [ -e "$MTLS_DIR" ] && [ ! -d "$MTLS_DIR" ]; }; then
    echo "Erreur : MTLS_DIR doit être un dossier réel, pas un fichier ni un lien symbolique." >&2
    exit 1
fi

for name in "${files[@]}"; do
    path="$MTLS_DIR/$name"
    if [ -e "$path" ] || [ -L "$path" ]; then
        existing=$((existing + 1))
    fi
done

if [ "$existing" -eq "${#files[@]}" ]; then
    MTLS_DIR="$MTLS_DIR" "$PROJECT_ROOT/scripts/check_mtls_files.sh"
    echo "Aucun fichier existant n'a été écrasé."
    exit 0
fi

if [ "$existing" -ne 0 ]; then
    echo "Erreur : état mTLS partiel ou invalide dans $MTLS_DIR ; aucun fichier n'a été écrasé." >&2
    echo "Archive le dossier complet avant de créer une nouvelle CA et de nouveaux certificats." >&2
    exit 1
fi

install -d -m 0750 "$MTLS_DIR"
umask 077
tmp_dir="$(mktemp -d "$MTLS_DIR/.generate.XXXXXX")"
cleanup() {
    rm -f -- "$tmp_dir/ca.key" "$tmp_dir/ca.crt" "$tmp_dir/ca.srl" \
        "$tmp_dir/api.key" "$tmp_dir/api.csr" "$tmp_dir/api.crt" \
        "$tmp_dir/nginx-client.key" "$tmp_dir/nginx-client.csr" \
        "$tmp_dir/nginx-client.crt"
    rmdir -- "$tmp_dir" 2>/dev/null || true
}
trap cleanup EXIT

openssl req -x509 -newkey rsa:4096 -sha256 -nodes -days 3650 \
    -subj "/CN=infra-lab-service-ca" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$tmp_dir/ca.key" -out "$tmp_dir/ca.crt" >/dev/null 2>&1

openssl req -new -newkey rsa:3072 -sha256 -nodes \
    -subj "/CN=api" \
    -addext "subjectAltName=DNS:api,DNS:localhost,IP:127.0.0.1" \
    -addext "extendedKeyUsage=serverAuth,clientAuth" \
    -keyout "$tmp_dir/api.key" -out "$tmp_dir/api.csr" >/dev/null 2>&1
openssl x509 -req -sha256 -days 365 \
    -in "$tmp_dir/api.csr" \
    -CA "$tmp_dir/ca.crt" -CAkey "$tmp_dir/ca.key" -CAcreateserial \
    -copy_extensions copy -out "$tmp_dir/api.crt" >/dev/null 2>&1

openssl req -new -newkey rsa:3072 -sha256 -nodes \
    -subj "/CN=nginx" \
    -addext "extendedKeyUsage=clientAuth" \
    -keyout "$tmp_dir/nginx-client.key" \
    -out "$tmp_dir/nginx-client.csr" >/dev/null 2>&1
openssl x509 -req -sha256 -days 365 \
    -in "$tmp_dir/nginx-client.csr" \
    -CA "$tmp_dir/ca.crt" -CAkey "$tmp_dir/ca.key" \
    -CAserial "$tmp_dir/ca.srl" -copy_extensions copy \
    -out "$tmp_dir/nginx-client.crt" >/dev/null 2>&1

openssl verify -CAfile "$tmp_dir/ca.crt" \
    "$tmp_dir/api.crt" "$tmp_dir/nginx-client.crt" >/dev/null

install -m 0600 "$tmp_dir/ca.key" "$MTLS_DIR/ca.key"
install -m 0600 "$tmp_dir/api.key" "$MTLS_DIR/api.key"
install -m 0600 "$tmp_dir/nginx-client.key" "$MTLS_DIR/nginx-client.key"
install -m 0644 "$tmp_dir/ca.crt" "$MTLS_DIR/ca.crt"
install -m 0644 "$tmp_dir/api.crt" "$MTLS_DIR/api.crt"
install -m 0644 "$tmp_dir/nginx-client.crt" "$MTLS_DIR/nginx-client.crt"

if ! chown root:10001 "$MTLS_DIR" \
    "$MTLS_DIR"/{ca.key,api.key,nginx-client.key,ca.crt,api.crt,nginx-client.crt}; then
    echo "Erreur : chown root:10001 a échoué pour les fichiers mTLS dans $MTLS_DIR." >&2
    echo "Le GID numérique 10001 ne nécessite pas de groupe dans /etc/group ; vérifie les droits root et le système de fichiers." >&2
    exit 1
fi
chmod 0750 "$MTLS_DIR"
chmod 0640 "$MTLS_DIR"/{ca.key,api.key,nginx-client.key}
chmod 0644 "$MTLS_DIR"/{ca.crt,api.crt,nginx-client.crt}

MTLS_DIR="$MTLS_DIR" "$PROJECT_ROOT/scripts/check_mtls_files.sh"
echo "Fichiers mTLS créés dans $MTLS_DIR ; ne les ajoute jamais à Git."
