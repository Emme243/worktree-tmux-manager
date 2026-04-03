"""Tests for modules.core.config — AppConfig, ConfigError, load_config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.core.config import CONFIG_PATH, AppConfig, ConfigError, load_config

# ---------------------------------------------------------------------------
# ConfigError
# ---------------------------------------------------------------------------


class TestConfigError:
    def test_is_exception_subclass(self):
        assert issubclass(ConfigError, Exception)

    def test_preserves_message(self):
        assert str(ConfigError("boom")) == "boom"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ConfigError):
            raise ConfigError("test")


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class TestAppConfigDefaults:
    def test_required_field_repo_path(self):
        cfg = AppConfig(repo_path=Path("/x"))
        assert cfg.repo_path == Path("/x")

    def test_optional_fields_default_to_none(self):
        cfg = AppConfig(repo_path=Path("/x"))
        assert cfg.linear_api_key is None
        assert cfg.linear_team_id is None
        assert cfg.github_token is None
        assert cfg.github_repo is None

    def test_all_fields_stored(self):
        cfg = AppConfig(
            repo_path=Path("/x"),
            linear_api_key="lin_abc",
            linear_team_id="team1",
            github_token="ghp_xyz",
            github_repo="owner/repo",
        )
        assert cfg.linear_api_key == "lin_abc"
        assert cfg.linear_team_id == "team1"
        assert cfg.github_token == "ghp_xyz"
        assert cfg.github_repo == "owner/repo"

    def test_repo_path_is_path_object(self):
        cfg = AppConfig(repo_path=Path("/x"))
        assert isinstance(cfg.repo_path, Path)


# ---------------------------------------------------------------------------
# CONFIG_PATH constant
# ---------------------------------------------------------------------------


class TestConfigPath:
    def test_default_config_path_is_correct(self):
        assert Path.home() / ".config" / "tt-tmux" / "config.toml" == CONFIG_PATH


# ---------------------------------------------------------------------------
# load_config — file missing
# ---------------------------------------------------------------------------


class TestLoadConfigFileMissing:
    def test_raises_config_error(self, tmp_path):
        with pytest.raises(ConfigError):
            load_config(tmp_path / "no.toml")

    def test_error_message_contains_path(self, tmp_path):
        missing = tmp_path / "no.toml"
        with pytest.raises(ConfigError, match=str(missing)):
            load_config(missing)

    def test_error_message_contains_hint(self, tmp_path):
        with pytest.raises(ConfigError, match="Create"):
            load_config(tmp_path / "no.toml")


# ---------------------------------------------------------------------------
# load_config — invalid TOML
# ---------------------------------------------------------------------------


class TestLoadConfigInvalidToml:
    def _write(self, tmp_path, content: str) -> Path:
        p = tmp_path / "config.toml"
        p.write_text(content, encoding="utf-8")
        return p

    def test_raises_config_error(self, tmp_path):
        path = self._write(tmp_path, "not valid toml [[[")
        with pytest.raises(ConfigError):
            load_config(path)

    def test_error_message_contains_not_valid_toml(self, tmp_path):
        path = self._write(tmp_path, "not valid toml [[[")
        with pytest.raises(ConfigError, match="not valid TOML"):
            load_config(path)

    def test_error_message_contains_path(self, tmp_path):
        path = self._write(tmp_path, "not valid toml [[[")
        with pytest.raises(ConfigError, match=str(path)):
            load_config(path)


# ---------------------------------------------------------------------------
# load_config — missing repo_path key
# ---------------------------------------------------------------------------


class TestLoadConfigMissingRepoPath:
    def _write(self, tmp_path, content: str) -> Path:
        p = tmp_path / "config.toml"
        p.write_text(content, encoding="utf-8")
        return p

    def test_raises_config_error(self, tmp_path):
        path = self._write(tmp_path, 'linear_api_key = "abc"\n')
        with pytest.raises(ConfigError):
            load_config(path)

    def test_error_message_names_missing_key(self, tmp_path):
        path = self._write(tmp_path, 'linear_api_key = "abc"\n')
        with pytest.raises(ConfigError, match="repo_path"):
            load_config(path)


# ---------------------------------------------------------------------------
# load_config — success
# ---------------------------------------------------------------------------


class TestLoadConfigSuccess:
    def _write(self, tmp_path, content: str) -> Path:
        p = tmp_path / "config.toml"
        p.write_text(content, encoding="utf-8")
        return p

    def test_minimal_config_returns_app_config(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert isinstance(cfg, AppConfig)

    def test_repo_path_is_expanded(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "~/projects/foo"\n')
        cfg = load_config(path)
        assert cfg.repo_path == Path("~/projects/foo").expanduser()

    def test_repo_path_is_path_object(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert isinstance(cfg.repo_path, Path)

    def test_optional_fields_none_when_absent(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert cfg.linear_api_key is None
        assert cfg.linear_team_id is None
        assert cfg.github_token is None
        assert cfg.github_repo is None

    def test_all_optional_fields_loaded(self, tmp_path):
        content = (
            'repo_path = "/some/repo"\n'
            'linear_api_key = "lin_abc"\n'
            'linear_team_id = "team1"\n'
            'github_token = "ghp_xyz"\n'
            'github_repo = "owner/repo"\n'
        )
        path = self._write(tmp_path, content)
        cfg = load_config(path)
        assert cfg.linear_api_key == "lin_abc"
        assert cfg.linear_team_id == "team1"
        assert cfg.github_token == "ghp_xyz"
        assert cfg.github_repo == "owner/repo"

    def test_linear_api_key_stored(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/r"\nlinear_api_key = "lin_key"\n')
        assert load_config(path).linear_api_key == "lin_key"

    def test_github_repo_stored(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/r"\ngithub_repo = "org/proj"\n')
        assert load_config(path).github_repo == "org/proj"


# ---------------------------------------------------------------------------
# load_config — default path wiring
# ---------------------------------------------------------------------------


class TestLoadConfigDefaultPath:
    def test_default_path_used_when_no_arg(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('repo_path = "/default/repo"\n', encoding="utf-8")
        with patch("modules.core.config.CONFIG_PATH", config_file):
            cfg = load_config()
        assert cfg.repo_path == Path("/default/repo")
