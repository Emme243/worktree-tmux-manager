"""Tests for modules.core.config — AppConfig, ConfigError, load_config, save_config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.core.config import (
    CONFIG_PATH,
    AppConfig,
    ConfigError,
    ProjectConfig,
    load_config,
    save_config,
)

# ---------------------------------------------------------------------------
# ConfigError
# ---------------------------------------------------------------------------


class TestConfigError:
    def test_is_exception_subclass(self):
        assert issubclass(ConfigError, Exception)

    def test_preserves_message(self):
        assert str(ConfigError("boom", reason="missing_file")) == "boom"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ConfigError):
            raise ConfigError("test", reason="missing_file")

    def test_reason_attribute_stored(self):
        exc = ConfigError("msg", reason="missing_file")
        assert exc.reason == "missing_file"

    def test_reason_invalid_toml(self):
        exc = ConfigError("msg", reason="invalid_toml")
        assert exc.reason == "invalid_toml"

    def test_reason_missing_repo_path(self):
        exc = ConfigError("msg", reason="missing_repo_path")
        assert exc.reason == "missing_repo_path"


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


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    def test_file_is_written(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/some/repo")), path)
        assert path.exists()

    def test_repo_path_round_trips(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/some/repo")), path)
        cfg = load_config(path)
        assert cfg.repo_path == Path("/some/repo")

    def test_all_optional_fields_round_trip(self, tmp_path):
        path = tmp_path / "config.toml"
        original = AppConfig(
            repo_path=Path("/r"),
            linear_api_key="lin_abc",
            linear_team_id="team1",
            github_token="ghp_xyz",
            github_repo="owner/repo",
        )
        save_config(original, path)
        cfg = load_config(path)
        assert cfg.linear_api_key == "lin_abc"
        assert cfg.linear_team_id == "team1"
        assert cfg.github_token == "ghp_xyz"
        assert cfg.github_repo == "owner/repo"

    def test_none_optional_fields_are_omitted(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/r")), path)
        content = path.read_text(encoding="utf-8")
        assert "linear_api_key" not in content
        assert "github_token" not in content

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "nested" / "dirs" / "config.toml"
        save_config(AppConfig(repo_path=Path("/r")), path)
        assert path.exists()

    def test_no_tmp_file_left_on_success(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/r")), path)
        assert not path.with_name(path.name + ".tmp").exists()

    def test_uses_default_config_path(self, tmp_path):
        config_file = tmp_path / "config.toml"
        with patch("modules.core.config.CONFIG_PATH", config_file):
            save_config(AppConfig(repo_path=Path("/r")))
        assert config_file.exists()


# ---------------------------------------------------------------------------
# ProjectConfig
# ---------------------------------------------------------------------------


class TestProjectConfigDefaults:
    def test_name_defaults_to_path_basename(self):
        cfg = ProjectConfig(path=Path("/some/repo/my-project"))
        assert cfg.name == "my-project"

    def test_explicit_name_is_preserved(self):
        cfg = ProjectConfig(path=Path("/some/repo"), name="Custom Name")
        assert cfg.name == "Custom Name"

    def test_empty_string_name_derives_from_path(self):
        cfg = ProjectConfig(path=Path("/repos/alpha"), name="")
        assert cfg.name == "alpha"

    def test_path_is_path_object(self):
        cfg = ProjectConfig(path=Path("/some/repo"))
        assert isinstance(cfg.path, Path)


# ---------------------------------------------------------------------------
# load_config — migration from old repo_path format
# ---------------------------------------------------------------------------


class TestLoadConfigMigration:
    def _write(self, tmp_path, content: str) -> Path:
        p = tmp_path / "config.toml"
        p.write_text(content, encoding="utf-8")
        return p

    def test_old_format_populates_projects(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert len(cfg.projects) == 1
        assert cfg.projects[0].path == Path("/some/repo")

    def test_old_format_repo_path_still_accessible(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert cfg.repo_path == Path("/some/repo")

    def test_old_format_project_name_derived_from_path(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        cfg = load_config(path)
        assert cfg.projects[0].name == "repo"

    def test_old_format_returns_app_config(self, tmp_path):
        path = self._write(tmp_path, 'repo_path = "/some/repo"\n')
        assert isinstance(load_config(path), AppConfig)


# ---------------------------------------------------------------------------
# load_config — new [[projects]] format
# ---------------------------------------------------------------------------


class TestLoadConfigMultiProject:
    def _write(self, tmp_path, content: str) -> Path:
        p = tmp_path / "config.toml"
        p.write_text(content, encoding="utf-8")
        return p

    def test_new_format_loads_both_projects(self, tmp_path):
        content = (
            "[[projects]]\n"
            'path = "/repos/alpha"\n'
            'name = "alpha"\n'
            "\n"
            "[[projects]]\n"
            'path = "/repos/beta"\n'
            'name = "beta"\n'
        )
        path = self._write(tmp_path, content)
        cfg = load_config(path)
        assert len(cfg.projects) == 2

    def test_new_format_repo_path_is_first_project(self, tmp_path):
        content = (
            "[[projects]]\n"
            'path = "/repos/alpha"\n'
            'name = "alpha"\n'
            "\n"
            "[[projects]]\n"
            'path = "/repos/beta"\n'
            'name = "beta"\n'
        )
        path = self._write(tmp_path, content)
        cfg = load_config(path)
        assert cfg.repo_path == Path("/repos/alpha")

    def test_new_format_project_paths_are_path_objects(self, tmp_path):
        content = '[[projects]]\npath = "/repos/alpha"\nname = "alpha"\n'
        path = self._write(tmp_path, content)
        cfg = load_config(path)
        assert isinstance(cfg.projects[0].path, Path)

    def test_new_format_omitted_name_derives_from_path(self, tmp_path):
        content = '[[projects]]\npath = "/repos/my-project"\n'
        path = self._write(tmp_path, content)
        cfg = load_config(path)
        assert cfg.projects[0].name == "my-project"


# ---------------------------------------------------------------------------
# save_config — new [[projects]] format
# ---------------------------------------------------------------------------


class TestSaveConfigProjectFormat:
    def test_no_repo_path_key_in_output(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/some/repo")), path)
        content = path.read_text(encoding="utf-8")
        assert "repo_path" not in content

    def test_projects_section_written(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/some/repo")), path)
        content = path.read_text(encoding="utf-8")
        assert "projects" in content

    def test_single_project_round_trips(self, tmp_path):
        path = tmp_path / "config.toml"
        project = ProjectConfig(path=Path("/repos/alpha"), name="alpha")
        save_config(AppConfig(repo_path=Path("/repos/alpha"), projects=[project]), path)
        cfg = load_config(path)
        assert cfg.projects[0].path == Path("/repos/alpha")
        assert cfg.projects[0].name == "alpha"

    def test_multi_project_round_trips(self, tmp_path):
        path = tmp_path / "config.toml"
        projects = [
            ProjectConfig(path=Path("/repos/alpha"), name="alpha"),
            ProjectConfig(path=Path("/repos/beta"), name="beta"),
        ]
        save_config(AppConfig(repo_path=Path("/repos/alpha"), projects=projects), path)
        cfg = load_config(path)
        assert len(cfg.projects) == 2
        assert cfg.projects[1].path == Path("/repos/beta")

    def test_name_round_trips(self, tmp_path):
        path = tmp_path / "config.toml"
        project = ProjectConfig(path=Path("/repos/alpha"), name="My Alpha")
        save_config(AppConfig(repo_path=Path("/repos/alpha"), projects=[project]), path)
        cfg = load_config(path)
        assert cfg.projects[0].name == "My Alpha"

    def test_empty_projects_falls_back_to_repo_path(self, tmp_path):
        path = tmp_path / "config.toml"
        save_config(AppConfig(repo_path=Path("/repos/fallback")), path)
        cfg = load_config(path)
        assert cfg.projects[0].path == Path("/repos/fallback")


# ---------------------------------------------------------------------------
# ProjectConfig.github_repo
# ---------------------------------------------------------------------------


class TestProjectConfigGithubRepo:
    def test_github_repo_defaults_to_none(self):
        cfg = ProjectConfig(path=Path("/r"))
        assert cfg.github_repo is None

    def test_github_repo_can_be_set(self):
        cfg = ProjectConfig(path=Path("/r"), github_repo="owner/repo")
        assert cfg.github_repo == "owner/repo"


class TestProjectConfigGithubRepoRoundTrip:
    def test_github_repo_round_trips_in_projects(self, tmp_path):
        path = tmp_path / "config.toml"
        project = ProjectConfig(path=Path("/repos/alpha"), github_repo="org/proj")
        save_config(AppConfig(repo_path=Path("/repos/alpha"), projects=[project]), path)
        cfg = load_config(path)
        assert cfg.projects[0].github_repo == "org/proj"

    def test_github_repo_none_when_not_in_file(self, tmp_path):
        path = tmp_path / "config.toml"
        project = ProjectConfig(path=Path("/repos/alpha"))
        save_config(AppConfig(repo_path=Path("/repos/alpha"), projects=[project]), path)
        cfg = load_config(path)
        assert cfg.projects[0].github_repo is None

    def test_top_level_github_repo_migrated_to_first_project(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text(
            'repo_path = "/some/repo"\ngithub_repo = "org/proj"\n', encoding="utf-8"
        )
        cfg = load_config(path)
        assert cfg.projects[0].github_repo == "org/proj"

    def test_top_level_github_repo_absent_gives_none_on_project(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text('repo_path = "/some/repo"\n', encoding="utf-8")
        cfg = load_config(path)
        assert cfg.projects[0].github_repo is None
