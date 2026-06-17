import hashlib
import importlib.util
import io
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "generate_diag_token.py"
)
SPEC = importlib.util.spec_from_file_location("generate_diag_token", SCRIPT_PATH)
assert SPEC is not None
generate_diag_token = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generate_diag_token)


def test_hash_token_returns_sha256_hex_digest():
    assert generate_diag_token.hash_token("test-token") == hashlib.sha256(
        b"test-token"
    ).hexdigest()


def test_cli_hash_stdin_does_not_echo_clear_token():
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = generate_diag_token.main(
        ["--stdin", "--hash-only"],
        stdin=io.StringIO("secret-client-token"),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert "secret-client-token" not in stdout.getvalue()
    assert stdout.getvalue().strip() == hashlib.sha256(
        b"secret-client-token"
    ).hexdigest()
    assert stderr.getvalue() == ""


def test_cli_token_only_prints_generated_token_without_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stdout = io.StringIO()

    exit_code = generate_diag_token.main(["--token-only"], stdout=stdout)

    assert exit_code == 0
    assert len(stdout.getvalue().strip()) >= 22
    assert list(tmp_path.iterdir()) == []
