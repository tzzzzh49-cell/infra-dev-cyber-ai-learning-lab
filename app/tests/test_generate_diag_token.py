import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "generate_diag_token.py"
)
SPEC = importlib.util.spec_from_file_location("generate_diag_token", SCRIPT_PATH)
assert SPEC is not None
generate_diag_token = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generate_diag_token)


def test_sha256_hash_returns_prefixed_digest():
    digest = hashlib.sha256(b"test-token").hexdigest()

    assert generate_diag_token.sha256_hash("test-token") == f"sha256:{digest}"


def test_generate_token_rejects_weak_byte_count():
    try:
        generate_diag_token.generate_token(8)
    except ValueError as exc:
        assert "at least 16" in str(exc)
    else:
        raise AssertionError("generate_token accepted an unsafe byte count")


def test_cli_rejects_plaintext_token_argument():
    with pytest.raises(SystemExit):
        generate_diag_token.build_parser().parse_args(["--token", "placeholder"])


def test_cli_generates_token_without_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        generate_diag_token,
        "generate_token",
        lambda _byte_count: "generated-client-token",
    )

    exit_code = generate_diag_token.main([])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "generated-client-token" in output
    assert "DIAG_ACCESS_TOKEN_HASH" in output
    assert "sha256:" in output
    assert list(tmp_path.iterdir()) == []
