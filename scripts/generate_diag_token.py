#!/usr/bin/env python3
"""Generate a diagnostic access token and its storable hash."""

from __future__ import annotations

import argparse
import hashlib
import secrets
import sys


def sha256_hash(token: str) -> str:
    """Return the SHA-256 storage format accepted by the API."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Generate a /diag bearer token and its hash for secrets storage.",
    )
    parser.add_argument(
        "--bytes",
        type=int,
        default=32,
        help="Random byte count for generated tokens. Defaults to 32.",
    )
    return parser


def generate_token(byte_count: int) -> str:
    """Generate a URL-safe diagnostic token."""
    if byte_count < 16:
        raise ValueError("--bytes must be at least 16 for diagnostic tokens.")
    return secrets.token_urlsafe(byte_count)


def main(argv: list[str] | None = None) -> int:
    """Run the token generator CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        token = generate_token(args.bytes)
        stored_hash = sha256_hash(token)
    except ValueError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

    print("Jeton a fournir au client HTTP :")
    print(token)
    print()
    print("Hash a stocker dans DIAG_ACCESS_TOKEN_HASH :")
    print(stored_hash)
    print()
    print("Ne pas commiter le jeton ni le hash dans le depot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
