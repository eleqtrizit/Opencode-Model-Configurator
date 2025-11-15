"""Tests for ConfigManager class."""

import json
import tempfile
from pathlib import Path

import pytest

from opencode_model_configurator.config_manager import ConfigManager


@pytest.fixture
def temp_config_file() -> Path:
    """
    Create a temporary config file for testing.

    :return: Path to temporary config file
    :rtype: Path
    """
    config_data = {
        "model": "provider1/model1",
        "provider": {
            "provider1": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Provider 1",
                "options": {"baseURL": "http://example.com"},
                "models": {
                    "model1": {"name": "Model 1"},
                    "model2": {"name": "Model 2"},
                },
            },
            "provider2": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Provider 2",
                "options": {"baseURL": "http://example2.com"},
                "models": {
                    "model2": {"name": "Model 2 Alternate"},
                    "model3": {"name": "Model 3"},
                },
            },
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def empty_config_file() -> Path:
    """
    Create an empty config file for testing.

    :return: Path to temporary empty config file
    :rtype: Path
    """
    config_data = {}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def config_manager(temp_config_file: Path) -> ConfigManager:
    """
    Create a ConfigManager instance with a temporary config file.

    :param temp_config_file: Temporary config file path
    :type temp_config_file: Path
    :return: ConfigManager instance
    :rtype: ConfigManager
    """
    return ConfigManager(temp_config_file)


class TestConfigManagerInit:
    """Tests for ConfigManager.__init__."""

    def test_init_with_path(self, temp_config_file: Path) -> None:
        """Test initialization with explicit config path."""
        manager = ConfigManager(temp_config_file)
        assert manager.config_path == temp_config_file

    def test_init_without_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization without config path uses current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            manager = ConfigManager()
            expected_path = Path(tmpdir) / "config.json"
            assert manager.config_path.resolve() == expected_path.resolve()

    def test_init_with_none_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with None path uses current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            manager = ConfigManager(None)
            expected_path = Path(tmpdir) / "config.json"
            assert manager.config_path.resolve() == expected_path.resolve()


class TestConfigManagerLoadConfig:
    """Tests for ConfigManager.load_config."""

    def test_load_config_success(self, config_manager: ConfigManager) -> None:
        """Test loading config from existing file."""
        config = config_manager.load_config()
        assert isinstance(config, dict)
        assert "model" in config
        assert "provider" in config

    def test_load_config_file_not_found(self) -> None:
        """Test loading config from non-existent file raises FileNotFoundError."""
        non_existent = Path("/nonexistent/path/config.json")
        manager = ConfigManager(non_existent)
        with pytest.raises(FileNotFoundError):
            manager.load_config()

    def test_load_config_invalid_json(self) -> None:
        """Test loading invalid JSON raises JSONDecodeError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = Path(f.name)
        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(json.JSONDecodeError):
                manager.load_config()
        finally:
            temp_path.unlink(missing_ok=True)


class TestConfigManagerSaveConfig:
    """Tests for ConfigManager.save_config."""

    def test_save_config_success(self, config_manager: ConfigManager) -> None:
        """Test saving config to file."""
        new_config = {"test": "value", "model": "test/model"}
        config_manager.save_config(new_config)
        loaded = config_manager.load_config()
        assert loaded == new_config

    def test_save_config_creates_directory(self, tmp_path: Path) -> None:
        """Test saving config creates parent directory if it doesn't exist."""
        config_path = tmp_path / "nested" / "dir" / "config.json"
        manager = ConfigManager(config_path)
        config = {"test": "value"}
        manager.save_config(config)
        assert config_path.exists()
        loaded = manager.load_config()
        assert loaded == config


class TestConfigManagerGetModel:
    """Tests for ConfigManager.get_model."""

    def test_get_model_success(self, config_manager: ConfigManager) -> None:
        """Test getting model."""
        model = config_manager.get_model()
        assert model == "provider1/model1"

    def test_get_model_empty(self, empty_config_file: Path) -> None:
        """Test getting model when model field doesn't exist."""
        manager = ConfigManager(empty_config_file)
        model = manager.get_model()
        assert model == ""


class TestConfigManagerUpdateModel:
    """Tests for ConfigManager.update_model."""

    def test_update_model_success(self, config_manager: ConfigManager) -> None:
        """Test updating model."""
        new_model = "provider2/model3"
        config_manager.update_model(new_model)
        loaded = config_manager.get_model()
        assert loaded == new_model

    def test_update_model_preserves_other_sections(
        self, config_manager: ConfigManager
    ) -> None:
        """Test updating model preserves other config sections."""
        original_config = config_manager.load_config()
        new_model = "provider2/model3"
        config_manager.update_model(new_model)
        updated_config = config_manager.load_config()
        assert updated_config["model"] == new_model
        assert "provider" in updated_config
        assert updated_config["provider"] == original_config["provider"]


class TestConfigManagerGetProviders:
    """Tests for ConfigManager.get_providers."""

    def test_get_providers_success(self, config_manager: ConfigManager) -> None:
        """Test getting providers dictionary."""
        providers = config_manager.get_providers()
        assert len(providers) == 2
        assert "provider1" in providers
        assert "provider2" in providers

    def test_get_providers_empty(self, empty_config_file: Path) -> None:
        """Test getting providers when provider section doesn't exist."""
        manager = ConfigManager(empty_config_file)
        providers = manager.get_providers()
        assert providers == {}


class TestConfigManagerAddProvider:
    """Tests for ConfigManager.add_provider."""

    def test_add_provider_success(self, config_manager: ConfigManager) -> None:
        """Test adding a new provider."""
        new_provider_config = {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Provider 3",
            "options": {"baseURL": "http://example3.com"},
            "models": {},
        }
        config_manager.add_provider("provider3", new_provider_config)
        providers = config_manager.get_providers()
        assert len(providers) == 3
        assert providers["provider3"] == new_provider_config

    def test_add_provider_to_empty_config(self, empty_config_file: Path) -> None:
        """Test adding provider to empty config."""
        manager = ConfigManager(empty_config_file)
        new_provider_config = {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Provider 1",
            "options": {"baseURL": "http://example.com"},
            "models": {},
        }
        manager.add_provider("provider1", new_provider_config)
        providers = manager.get_providers()
        assert len(providers) == 1
        assert providers["provider1"] == new_provider_config


class TestConfigManagerAddModelToProvider:
    """Tests for ConfigManager.add_model_to_provider."""

    def test_add_model_to_provider_success(self, config_manager: ConfigManager) -> None:
        """Test adding a model to an existing provider."""
        model_config = {"name": "Model 3"}
        config_manager.add_model_to_provider("provider1", "model3", model_config)
        providers = config_manager.get_providers()
        assert "model3" in providers["provider1"]["models"]
        assert providers["provider1"]["models"]["model3"] == model_config

    def test_add_model_to_provider_not_found(self, config_manager: ConfigManager) -> None:
        """Test adding model to non-existent provider raises ValueError."""
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            config_manager.add_model_to_provider("nonexistent", "model1", {"name": "Model"})


class TestConfigManagerGetAllModels:
    """Tests for ConfigManager.get_all_models."""

    def test_get_all_models_success(self, config_manager: ConfigManager) -> None:
        """Test getting all models grouped by provider."""
        models_by_provider = config_manager.get_all_models()
        assert "provider1" in models_by_provider
        assert "provider2" in models_by_provider
        assert models_by_provider["provider1"] == ["model1", "model2"]
        assert models_by_provider["provider2"] == ["model2", "model3"]

    def test_get_all_models_empty(self, empty_config_file: Path) -> None:
        """Test getting all models from empty config."""
        manager = ConfigManager(empty_config_file)
        models_by_provider = manager.get_all_models()
        assert models_by_provider == {}


class TestConfigManagerFindProvidersForModel:
    """Tests for ConfigManager.find_providers_for_model."""

    def test_find_providers_for_model_single_match(self, config_manager: ConfigManager) -> None:
        """Test finding providers for model with single match."""
        providers = config_manager.find_providers_for_model("model1")
        assert providers == ["provider1"]

    def test_find_providers_for_model_multiple_matches(
        self, config_manager: ConfigManager
    ) -> None:
        """Test finding providers for model with multiple matches."""
        providers = config_manager.find_providers_for_model("model2")
        assert set(providers) == {"provider1", "provider2"}

    def test_find_providers_for_model_not_found(self, config_manager: ConfigManager) -> None:
        """Test finding providers for non-existent model."""
        providers = config_manager.find_providers_for_model("nonexistent")
        assert providers == []


class TestConfigManagerValidateProviderModel:
    """Tests for ConfigManager.validate_provider_model."""

    def test_validate_provider_model_valid(self, config_manager: ConfigManager) -> None:
        """Test validating valid provider-model combination."""
        assert config_manager.validate_provider_model("provider1", "model1") is True

    def test_validate_provider_model_invalid_provider(
        self, config_manager: ConfigManager
    ) -> None:
        """Test validating with non-existent provider."""
        assert config_manager.validate_provider_model("nonexistent", "model1") is False

    def test_validate_provider_model_invalid_model(self, config_manager: ConfigManager) -> None:
        """Test validating with non-existent model."""
        assert config_manager.validate_provider_model("provider1", "nonexistent") is False


class TestConfigManagerDeleteProvider:
    """Tests for ConfigManager.delete_provider."""

    def test_delete_provider_success(self, config_manager: ConfigManager) -> None:
        """Test deleting an existing provider."""
        config_manager.delete_provider("provider1")
        providers = config_manager.get_providers()
        assert len(providers) == 1
        assert "provider2" in providers

    def test_delete_provider_not_found(self, config_manager: ConfigManager) -> None:
        """Test deleting non-existent provider raises ValueError."""
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            config_manager.delete_provider("nonexistent")


class TestConfigManagerDeleteModel:
    """Tests for ConfigManager.delete_model."""

    def test_delete_model_success(self, config_manager: ConfigManager) -> None:
        """Test deleting a model from all providers."""
        config_manager.delete_model("model2")
        models_by_provider = config_manager.get_all_models()
        assert "model2" not in models_by_provider["provider1"]
        assert "model2" not in models_by_provider["provider2"]

    def test_delete_model_not_found(self, config_manager: ConfigManager) -> None:
        """Test deleting non-existent model raises ValueError."""
        with pytest.raises(ValueError, match="Model 'nonexistent' not found"):
            config_manager.delete_model("nonexistent")
