#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="$(mktemp -d)"
trap 'rm -rf -- "$tmp_root"' EXIT
mkdir "$tmp_root/bin"

REAL_ID="$(command -v id)"
REAL_INSTALL="$(command -v install)"
REAL_STAT="$(command -v stat)"
export REAL_ID REAL_INSTALL REAL_STAT
export CHOWN_LOG="$tmp_root/chown.log"

cat >"$tmp_root/bin/id" <<'MOCK'
#!/usr/bin/env bash
if [ "${1:-}" = -u ]; then
    echo 0
    exit 0
fi
exec "$REAL_ID" "$@"
MOCK

cat >"$tmp_root/bin/install" <<'MOCK'
#!/usr/bin/env bash
set -eu
previous=""
for argument in "$@"; do
    if { [ "$previous" = -g ] && [ "$argument" = 10001 ]; } ||
        [ "$argument" = -g10001 ] || [ "$argument" = --group=10001 ]; then
        echo "install: invalid group: 10001" >&2
        exit 1
    fi
    previous="$argument"
done
exec "$REAL_INSTALL" "$@"
MOCK

cat >"$tmp_root/bin/chown" <<'MOCK'
#!/usr/bin/env bash
if [ "${1:-}" != root:10001 ]; then
    echo "chown inattendu : $*" >&2
    exit 1
fi
printf '%s\n' "$*" >>"$CHOWN_LOG"
[ "${CHOWN_FAIL:-0}" != 1 ]
MOCK

cat >"$tmp_root/bin/stat" <<'MOCK'
#!/usr/bin/env bash
if [ "${1:-}" = -c ] && [ "${2:-}" = %u:%g ]; then
    echo 0:10001
    exit 0
fi
exec "$REAL_STAT" "$@"
MOCK

cat >"$tmp_root/bin/openssl" <<'MOCK'
#!/usr/bin/env bash
set -eu
command="${1:-}"
shift || true

case "$command" in
    req|x509)
        public_key=0
        while [ "$#" -gt 0 ]; do
            case "$1" in
                -keyout|-out)
                    shift
                    printf 'contenu factice\n' >"$1"
                    ;;
                -pubkey)
                    public_key=1
                    ;;
            esac
            shift
        done
        if [ "$public_key" -eq 1 ]; then
            printf 'cle publique factice\n'
        fi
        ;;
    pkey)
        for argument in "$@"; do
            if [ "$argument" = -pubout ]; then
                printf 'cle publique factice\n'
            fi
        done
        ;;
    verify)
        ;;
    *)
        echo "commande openssl inattendue : $command" >&2
        exit 1
        ;;
esac
MOCK

chmod +x "$tmp_root/bin"/*

if MTLS_MIN_VALIDITY_DAYS=invalid MTLS_DIR="$tmp_root/missing" \
    "$PROJECT_ROOT/scripts/check_mtls_files.sh" \
    >"$tmp_root/invalid-validity.log" 2>&1; then
    echo "Erreur : le test attendait le rejet du seuil de validité." >&2
    exit 1
fi
grep -q 'MTLS_MIN_VALIDITY_DAYS doit être compris' \
    "$tmp_root/invalid-validity.log"

mtls_dir="$tmp_root/mtls"
PATH="$tmp_root/bin:$PATH" MTLS_GENERATE_CONFIRM=yes MTLS_DIR="$mtls_dir" \
    "$PROJECT_ROOT/scripts/generate_mtls_files.sh" >"$tmp_root/success.log" 2>&1

grep -q '^root:10001 ' "$CHOWN_LOG"
[ "$("$REAL_STAT" -c %a "$mtls_dir")" = 750 ]
for key in ca.key api.key nginx-client.key; do
    [ "$("$REAL_STAT" -c %a "$mtls_dir/$key")" = 640 ]
done
for certificate in ca.crt api.crt nginx-client.crt; do
    [ "$("$REAL_STAT" -c %a "$mtls_dir/$certificate")" = 644 ]
done

if PATH="$tmp_root/bin:$PATH" CHOWN_FAIL=1 MTLS_GENERATE_CONFIRM=yes \
    MTLS_DIR="$tmp_root/chown-failure" "$PROJECT_ROOT/scripts/generate_mtls_files.sh" \
    >"$tmp_root/failure.log" 2>&1; then
    echo "Erreur : le test attendait un échec de chown." >&2
    exit 1
fi
grep -q 'Erreur : chown root:10001 a échoué' "$tmp_root/failure.log"

echo "OK : génération compatible avec un GID 10001 absent de /etc/group."
