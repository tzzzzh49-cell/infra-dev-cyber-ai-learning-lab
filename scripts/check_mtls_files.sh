#!/usr/bin/env bash
set -euo pipefail

MTLS_DIR="${MTLS_DIR:-/etc/infra-lab/mtls}"
MTLS_MIN_VALIDITY_DAYS="${MTLS_MIN_VALIDITY_DAYS:-30}"
files=(ca.key ca.crt api.key api.crt nginx-client.key nginx-client.crt)
keys=(ca.key api.key nginx-client.key)
certificates=(ca.crt api.crt nginx-client.crt)

if [ "$#" -ne 0 ]; then
    echo "Usage : MTLS_DIR=/chemin $0" >&2
    exit 2
fi

if [[ ! "$MTLS_MIN_VALIDITY_DAYS" =~ ^[0-9]{1,4}$ ]] ||
    ((10#$MTLS_MIN_VALIDITY_DAYS > 3650)); then
    echo "Erreur : MTLS_MIN_VALIDITY_DAYS doit être compris entre 0 et 3650." >&2
    exit 2
fi
min_validity_seconds=$((10#$MTLS_MIN_VALIDITY_DAYS * 86400))

invalid=0
for name in "${files[@]}"; do
    path="$MTLS_DIR/$name"
    if [ -L "$path" ] || [ ! -f "$path" ]; then
        echo "Erreur : fichier mTLS absent, non régulier ou symbolique : $path" >&2
        invalid=1
    elif [ ! -s "$path" ]; then
        echo "Erreur : fichier mTLS vide : $path" >&2
        invalid=1
    fi
done

if [ "$invalid" -ne 0 ]; then
    exit 1
fi

for command in cmp openssl stat; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Erreur : commande requise introuvable : $command" >&2
        exit 1
    fi
done

for key in "${keys[@]}"; do
    mode="$(stat -c '%a' "$MTLS_DIR/$key")"
    owner="$(stat -c '%u:%g' "$MTLS_DIR/$key")"
    if [ "$owner" != 0:10001 ] || [ "$mode" != 640 ]; then
        echo "Erreur : propriétaire, groupe ou permissions incorrects sur $MTLS_DIR/$key ($owner, $mode)." >&2
        echo "Attendu : root:10001 0640." >&2
        exit 1
    fi
    if ! openssl pkey -in "$MTLS_DIR/$key" -passin pass: -noout >/dev/null 2>&1; then
        echo "Erreur : clé privée invalide, chiffrée ou illisible : $MTLS_DIR/$key" >&2
        exit 1
    fi
done

for certificate in "${certificates[@]}"; do
    mode="$(stat -c '%a' "$MTLS_DIR/$certificate")"
    owner="$(stat -c '%u:%g' "$MTLS_DIR/$certificate")"
    if [ "$owner" != 0:10001 ] || [ "$mode" != 644 ]; then
        echo "Erreur : propriétaire, groupe ou permissions incorrects sur $MTLS_DIR/$certificate ($owner, $mode)." >&2
        echo "Attendu : root:10001 0644." >&2
        exit 1
    fi
    if ! openssl x509 -in "$MTLS_DIR/$certificate" -noout \
        -checkend "$min_validity_seconds" >/dev/null 2>&1; then
        echo "Erreur : certificat X.509 invalide ou expirant dans moins de $MTLS_MIN_VALIDITY_DAYS jours : $MTLS_DIR/$certificate" >&2
        exit 1
    fi
done

if ! openssl verify -check_ss_sig -CAfile "$MTLS_DIR/ca.crt" \
    "$MTLS_DIR/ca.crt" >/dev/null 2>&1; then
    echo "Erreur : la CA est invalide, non auto-signée ou hors période de validité." >&2
    exit 1
fi

if ! openssl verify -purpose sslserver -CAfile "$MTLS_DIR/ca.crt" \
    "$MTLS_DIR/api.crt" >/dev/null 2>&1; then
    echo "Erreur : api.crt n'est pas un certificat serveur valide signé par la CA." >&2
    exit 1
fi

if ! openssl verify -purpose sslclient -CAfile "$MTLS_DIR/ca.crt" \
    "$MTLS_DIR/nginx-client.crt" >/dev/null 2>&1; then
    echo "Erreur : nginx-client.crt n'est pas un certificat client valide signé par la CA." >&2
    exit 1
fi

for pair in "ca:ca" "api:api" "nginx-client:nginx-client"; do
    certificate="${pair%%:*}"
    key="${pair##*:}"
    if ! cmp -s \
        <(openssl x509 -in "$MTLS_DIR/$certificate.crt" -pubkey -noout 2>/dev/null) \
        <(openssl pkey -in "$MTLS_DIR/$key.key" -passin pass: -pubout 2>/dev/null); then
        echo "Erreur : $certificate.crt et $key.key ne correspondent pas." >&2
        exit 1
    fi
done

if ! openssl x509 -in "$MTLS_DIR/api.crt" -noout -checkhost api >/dev/null 2>&1; then
    echo "Erreur : api.crt ne contient pas le SAN DNS:api requis par Compose." >&2
    exit 1
fi

echo "OK : les six fichiers mTLS sont présents, non vides, valides et cohérents."
