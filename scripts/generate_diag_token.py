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


def bcrypt_hash(token: str, rounds: int) -> str:
    """Return the bcrypt storage format accepted by the API."""
    try:
        import bcrypt
    except ImportError as exc:
        raise RuntimeError(
            "bcrypt is not installed. Install app requirements or use --format sha256."
        ) from exc

    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(token.encode("utf-8"), salt).decode("utf-8")
    return f"bcrypt:{hashed}"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Generate a /diag bearer token and its hash for secrets storage.",
    )
    parser.add_argument(
        "--format",
        choices=("sha256", "bcrypt"),
        default="sha256",
        help="Hash format to generate. Defaults to sha256.",
    )
    parser.add_argument(
        "--token",
        help="Hash an existing token instead of generating a new one.",
    )
    parser.add_argument(
        "--bytes",
        type=int,
        default=32,
        help="Random byte count for generated tokens. Defaults to 32.",
    )
    parser.add_argument(
        "--bcrypt-rounds",
        type=int,
        default=12,
        help="bcrypt cost factor when --format bcrypt is used. Defaults to 12.",
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
        token = args.token or generate_token(args.bytes)
        if args.format == "sha256":
            stored_hash = sha256_hash(token)
        else:
            stored_hash = bcrypt_hash(token, args.bcrypt_rounds)
    except (RuntimeError, ValueError) as exc:
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
