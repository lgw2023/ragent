from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import ragent.runtime_env as runtime_env


def test_local_bootstrap_reloads_when_repo_root_changes(monkeypatch, tmp_path: Path):
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_a.mkdir()
    repo_b.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAGENT_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("RAGENT_TEST_RUNTIME_VALUE", raising=False)
    monkeypatch.delenv("RAGENT_TEST_ONLY_REPO_A", raising=False)
    monkeypatch.delenv("RAGENT_TEST_ONLY_REPO_B", raising=False)

    (repo_a / ".env").write_text(
        "RAGENT_TEST_RUNTIME_VALUE=repo_a\nRAGENT_TEST_ONLY_REPO_A=yes\n",
        encoding="utf-8",
    )
    (repo_b / ".env").write_text(
        "RAGENT_TEST_RUNTIME_VALUE=repo_b\nRAGENT_TEST_ONLY_REPO_B=yes\n",
        encoding="utf-8",
    )

    runtime_env.bootstrap_runtime_environment(repo_root=repo_a, force=True)
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") == "repo_a"
    assert runtime_env.os.getenv("RAGENT_TEST_ONLY_REPO_A") == "yes"

    state = runtime_env.bootstrap_runtime_environment(repo_root=repo_b, force=True)

    assert state.runtime_env == "local"
    assert state.dotenv_path == str((repo_b / ".env").resolve())
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") == "repo_b"
    assert runtime_env.os.getenv("RAGENT_TEST_ONLY_REPO_A") is None
    assert runtime_env.os.getenv("RAGENT_TEST_ONLY_REPO_B") == "yes"


def test_local_runtime_bootstrap_loads_dotenv(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAGENT_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("RAGENT_TEST_RUNTIME_VALUE", raising=False)

    (tmp_path / ".env").write_text("RAGENT_TEST_RUNTIME_VALUE=loaded\n", encoding="utf-8")

    state = runtime_env.bootstrap_runtime_environment(repo_root=tmp_path, force=True)

    assert state.runtime_env == "local"
    assert state.dotenv_loaded is True
    assert state.dotenv_path == str((tmp_path / ".env").resolve())
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") == "loaded"


def test_mep_runtime_bootstrap_skips_dotenv(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    monkeypatch.delenv("RAGENT_TEST_RUNTIME_VALUE", raising=False)
    (tmp_path / ".env").write_text("RAGENT_TEST_RUNTIME_VALUE=loaded\n", encoding="utf-8")

    state = runtime_env.bootstrap_runtime_environment(repo_root=tmp_path, force=True)

    assert state.runtime_env == "mep"
    assert state.dotenv_loaded is False
    assert state.dotenv_path is None
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") is None


def test_importing_runtime_env_does_not_import_ragent_or_litellm():
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root)}
    script = "\n".join(
        [
            "import sys",
            "from ragent.runtime_env import bootstrap_runtime_environment",
            "bootstrap_runtime_environment(explicit_runtime_env='mep')",
            "blocked = ['litellm', 'ragent.llm.openai', 'ragent.operate', 'ragent.ragent']",
            "print({name: name in sys.modules for name in blocked})",
            "raise SystemExit(any(name in sys.modules for name in blocked))",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_bootstrap_switching_local_to_mep_clears_dotenv_values(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAGENT_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("RAGENT_TEST_RUNTIME_VALUE", raising=False)

    (repo_root / ".env").write_text("RAGENT_TEST_RUNTIME_VALUE=loaded\n", encoding="utf-8")

    runtime_env.bootstrap_runtime_environment(repo_root=repo_root, force=True)
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") == "loaded"

    state = runtime_env.bootstrap_runtime_environment(
        explicit_runtime_env="mep",
        repo_root=repo_root,
        force=True,
    )

    assert state.runtime_env == "mep"
    assert state.dotenv_loaded is False
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") is None


def test_bootstrap_switching_mep_to_local_loads_dotenv(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAGENT_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("RAGENT_TEST_RUNTIME_VALUE", raising=False)

    (repo_root / ".env").write_text("RAGENT_TEST_RUNTIME_VALUE=loaded\n", encoding="utf-8")

    runtime_env.bootstrap_runtime_environment(
        explicit_runtime_env="mep",
        repo_root=repo_root,
        force=True,
    )
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") is None

    state = runtime_env.bootstrap_runtime_environment(
        explicit_runtime_env="local",
        repo_root=repo_root,
        force=True,
    )

    assert state.runtime_env == "local"
    assert state.dotenv_loaded is True
    assert state.dotenv_path == str((repo_root / ".env").resolve())
    assert runtime_env.os.getenv("RAGENT_TEST_RUNTIME_VALUE") == "loaded"
