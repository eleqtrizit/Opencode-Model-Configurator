"""Tests for CLI functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from opencode_model_configurator.cli import (add_model, add_provider, change_model, create_parser, delete_model,
                                             delete_provider, list_models, main, show_config, update_models)
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
def config_manager(temp_config_file: Path) -> ConfigManager:
    """
    Create a ConfigManager instance with a temporary config file.

    :param temp_config_file: Temporary config file path
    :type temp_config_file: Path
    :return: ConfigManager instance
    :rtype: ConfigManager
    """
    return ConfigManager(temp_config_file)


class TestListModels:
    """Tests for list_models function."""

    @patch("opencode_model_configurator.cli.console")
    def test_list_models_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test listing models successfully."""
        list_models(config_manager)
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert hasattr(call_args, "title")
        assert call_args.title == "Available Models"

    @patch("opencode_model_configurator.cli.console")
    def test_list_models_empty(self, mock_console: MagicMock) -> None:
        """Test listing models when no providers exist."""
        empty_config = Path(tempfile.mktemp(suffix=".json"))
        try:
            with open(empty_config, "w") as f:
                json.dump({}, f)
            manager = ConfigManager(empty_config)
            list_models(manager)
            assert mock_console.print.called
        finally:
            empty_config.unlink(missing_ok=True)


class TestShowConfig:
    """Tests for show_config function."""

    @patch("opencode_model_configurator.cli.console")
    def test_show_config_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test showing config successfully."""
        show_config(config_manager)
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert hasattr(call_args, "title")
        assert call_args.title == "Current Model Configuration"

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_show_config_empty(self, mock_sys: MagicMock, mock_console: MagicMock) -> None:
        """Test showing config when model field is empty."""
        empty_config = Path(tempfile.mktemp(suffix=".json"))
        try:
            with open(empty_config, "w") as f:
                json.dump({}, f)
            manager = ConfigManager(empty_config)
            show_config(manager)
            mock_console.print.assert_called_with("[yellow]No model configuration found[/yellow]")
        finally:
            empty_config.unlink(missing_ok=True)

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_show_config_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test showing config when file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        show_config(manager)
        mock_console.print.assert_called()
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestChangeModel:
    """Tests for change_model function."""

    @patch("opencode_model_configurator.cli.console")
    def test_change_model_success(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing model successfully."""
        change_model(config_manager, "provider1/model2")
        model = config_manager.get_model()
        assert model == "provider1/model2"
        mock_console.print.assert_called_with("[green]Updated model to: provider1/model2[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_change_model_invalid_format(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing model with invalid format (no slash)."""
        mock_sys.exit.side_effect = SystemExit(1)
        with pytest.raises(SystemExit):
            change_model(config_manager, "invalid_format")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_change_model_invalid_provider_model(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing model with invalid provider/model combination."""
        change_model(config_manager, "provider1/invalid_model")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestAddProvider:
    """Tests for add_provider function."""

    @patch("httpx.Client")
    @patch("opencode_model_configurator.cli.update_models")
    @patch("opencode_model_configurator.cli.console")
    def test_add_provider_success(
        self, mock_console: MagicMock, mock_update_models: MagicMock,
        mock_httpx: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test adding a provider successfully."""
        mock_client = MagicMock()
        mock_httpx.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value.raise_for_status.return_value = None

        add_provider(
            config_manager,
            "provider3",
            "@ai-sdk/openai-compatible",
            "Provider 3",
            "http://example3.com"
        )
        providers = config_manager.get_providers()
        assert len(providers) == 3
        assert "provider3" in providers
        assert providers["provider3"]["name"] == "Provider 3"
        mock_update_models.assert_called_once_with(config_manager, "provider3")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_add_provider_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test adding provider when config file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        add_provider(manager, "provider1", "@ai-sdk/openai-compatible", "Provider", "http://example.com")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestAddModel:
    """Tests for add_model function."""

    @patch("opencode_model_configurator.cli.console")
    def test_add_model_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test adding a model successfully."""
        add_model(config_manager, "provider1", "model3", "Model 3")
        providers = config_manager.get_providers()
        assert "model3" in providers["provider1"]["models"]
        mock_console.print.assert_called_with("[green]Added model 'model3' to provider 'provider1'[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_add_model_provider_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test adding model to non-existent provider."""
        add_model(config_manager, "nonexistent", "model1", "Model 1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_add_model_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test adding model when config file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        add_model(manager, "provider1", "model1", "Model 1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestDeleteProvider:
    """Tests for delete_provider function."""

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.input")
    def test_delete_provider_success(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a provider successfully with confirmation."""
        mock_input.return_value = "y"
        delete_provider(config_manager, "provider1")
        providers = config_manager.get_providers()
        assert len(providers) == 1
        assert "provider2" in providers
        mock_console.print.assert_called_with("[green]Deleted provider: provider1[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.input")
    def test_delete_provider_cancelled(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test cancelling provider deletion."""
        mock_input.return_value = "n"
        original_count = len(config_manager.get_providers())
        delete_provider(config_manager, "provider1")
        providers = config_manager.get_providers()
        assert len(providers) == original_count
        mock_console.print.assert_called_with("[yellow]Deletion cancelled[/yellow]")

    @patch("opencode_model_configurator.cli.console")
    def test_delete_provider_auto_confirm(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting provider with auto-confirm."""
        delete_provider(config_manager, "provider1", auto_confirm=True)
        providers = config_manager.get_providers()
        assert len(providers) == 1
        mock_console.print.assert_called_with("[green]Deleted provider: provider1[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_delete_provider_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting non-existent provider."""
        delete_provider(config_manager, "nonexistent", auto_confirm=True)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestDeleteModel:
    """Tests for delete_model function."""

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.input")
    def test_delete_model_success(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a model successfully with confirmation."""
        mock_input.return_value = "y"
        delete_model(config_manager, "model2")
        models_by_provider = config_manager.get_all_models()
        assert "model2" not in models_by_provider["provider1"]
        assert "model2" not in models_by_provider["provider2"]
        mock_console.print.assert_called_with("[green]Deleted model: model2[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.input")
    def test_delete_model_cancelled(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test cancelling model deletion."""
        mock_input.return_value = "n"
        original_models = config_manager.get_all_models()
        delete_model(config_manager, "model2")
        current_models = config_manager.get_all_models()
        assert current_models == original_models
        mock_console.print.assert_called_with("[yellow]Deletion cancelled[/yellow]")

    @patch("opencode_model_configurator.cli.console")
    def test_delete_model_auto_confirm(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting model with auto-confirm."""
        delete_model(config_manager, "model1", auto_confirm=True)
        models_by_provider = config_manager.get_all_models()
        assert "model1" not in models_by_provider["provider1"]
        mock_console.print.assert_called_with("[green]Deleted model: model1[/green]")

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_delete_model_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting non-existent model."""
        delete_model(config_manager, "nonexistent", auto_confirm=True)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestCreateParser:
    """Tests for create_parser function."""

    def test_create_parser_returns_parser(self) -> None:
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert parser.prog == "ocs"
        assert parser.description == "Open Code Model Configurator"

    def test_create_parser_has_subcommands(self) -> None:
        """Test that parser has expected subcommands."""
        parser = create_parser()
        args = parser.parse_args(["ls"])
        assert args.command == "ls"

        args = parser.parse_args(["show"])
        assert args.command == "show"

        args = parser.parse_args(["change", "provider1/model1"])
        assert args.command == "change"
        assert args.model_value == "provider1/model1"

        args = parser.parse_args(["add", "provider", "--npm", "@ai-sdk/test",
                                  "--name", "Test", "--base-url", "http://test.com"])
        assert args.command == "add"
        assert args.add_type == "provider"
        assert args.npm_package == "@ai-sdk/test"
        assert args.name == "Test"

        args = parser.parse_args(["add", "model", "provider1", "model1", "Model 1"])
        assert args.command == "add"
        assert args.add_type == "model"
        assert args.provider_id == "provider1"
        assert args.model_id == "model1"
        assert args.model_name == "Model 1"

        args = parser.parse_args(["delete", "provider", "provider1"])
        assert args.command == "delete"
        assert args.delete_type == "provider"
        assert args.provider_id == "provider1"

        args = parser.parse_args(["delete", "model", "model1"])
        assert args.command == "delete"
        assert args.delete_type == "model"
        assert args.model_id == "model1"

        args = parser.parse_args(["update", "all"])
        assert args.command == "update"
        assert args.provider == "all"

        args = parser.parse_args(["update", "provider1"])
        assert args.command == "update"
        assert args.provider == "provider1"


class TestUpdateModels:
    """Tests for update_models function."""

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.config_manager.ConfigManager.fetch_provider_models")
    def test_update_models_all_providers(
        self, mock_fetch: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test updating all providers."""
        mock_fetch.return_value = ["model1", "model2"]
        update_models(config_manager, "all")
        assert mock_fetch.call_count == 2
        assert mock_console.print.called

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.config_manager.ConfigManager.fetch_provider_models")
    def test_update_models_single_provider(
        self, mock_fetch: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test updating a single provider."""
        mock_fetch.return_value = ["model1", "model2"]
        update_models(config_manager, "provider1")
        assert mock_fetch.call_count == 1
        assert mock_console.print.called

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.cli.sys")
    def test_update_models_invalid_provider(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test updating with invalid provider name."""
        update_models(config_manager, "nonexistent")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("opencode_model_configurator.cli.console")
    @patch("opencode_model_configurator.config_manager.ConfigManager.fetch_provider_models")
    def test_update_models_case_insensitive_all(
        self, mock_fetch: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test that 'ALL' works case-insensitively."""
        mock_fetch.return_value = ["model1", "model2"]
        update_models(config_manager, "ALL")
        assert mock_fetch.call_count == 2


class TestMain:
    """Tests for main function."""

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "ls"])
    @patch("opencode_model_configurator.cli.list_models")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_ls_command(self, mock_config_manager_class: MagicMock, mock_list_models: MagicMock) -> None:
        """Test main function with ls command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_list_models.assert_called_once_with(mock_manager)

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "show"])
    @patch("opencode_model_configurator.cli.show_config")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_show_command(self, mock_config_manager_class: MagicMock, mock_show_config: MagicMock) -> None:
        """Test main function with show command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_show_config.assert_called_once_with(mock_manager)

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "change", "provider1/model1"])
    @patch("opencode_model_configurator.cli.change_model")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_change_command(
        self, mock_config_manager_class: MagicMock, mock_change_model: MagicMock
    ) -> None:
        """Test main function with change command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_change_model.assert_called_once_with(mock_manager, "provider1/model1")

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "add", "provider",
           "--npm", "@ai-sdk/test", "--name", "Test", "--base-url", "http://test.com"])
    @patch("opencode_model_configurator.cli.add_provider")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_add_provider_command(
        self, mock_config_manager_class: MagicMock, mock_add_provider: MagicMock
    ) -> None:
        """Test main function with add provider command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        assert mock_add_provider.called
        call_args = mock_add_provider.call_args[0]
        assert call_args[0] == mock_manager
        assert call_args[2] == "@ai-sdk/test"
        assert call_args[3] == "Test"
        assert call_args[4] == "http://test.com"

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "add", "model", "provider1", "model1", "Model 1"])
    @patch("opencode_model_configurator.cli.add_model")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_add_model_command(
        self, mock_config_manager_class: MagicMock, mock_add_model: MagicMock
    ) -> None:
        """Test main function with add model command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_add_model.assert_called_once_with(mock_manager, "provider1", "model1", "Model 1")

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "delete", "provider", "provider1"])
    @patch("opencode_model_configurator.cli.delete_provider")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_delete_provider_command(
        self, mock_config_manager_class: MagicMock, mock_delete_provider: MagicMock
    ) -> None:
        """Test main function with delete provider command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_provider.assert_called_once_with(mock_manager, "provider1", False)

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "delete", "provider", "provider1", "-y"])
    @patch("opencode_model_configurator.cli.delete_provider")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_delete_provider_with_yes(
        self, mock_config_manager_class: MagicMock, mock_delete_provider: MagicMock
    ) -> None:
        """Test main function with delete provider command and -y flag."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_provider.assert_called_once_with(mock_manager, "provider1", True)

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs", "delete", "model", "model1"])
    @patch("opencode_model_configurator.cli.delete_model")
    @patch("opencode_model_configurator.cli.ConfigManager")
    def test_main_delete_model_command(
        self, mock_config_manager_class: MagicMock, mock_delete_model: MagicMock
    ) -> None:
        """Test main function with delete model command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_model.assert_called_once_with(mock_manager, "model1", False)

    @patch("opencode_model_configurator.cli.sys.argv", ["ocs"])
    @patch("opencode_model_configurator.cli.sys.exit")
    def test_main_no_command(self, mock_exit: MagicMock) -> None:
        """Test main function with no command prints help and exits."""
        with patch("opencode_model_configurator.cli.create_parser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = MagicMock(command=None)
            mock_parser_class.return_value = mock_parser
            main()
            mock_parser.print_help.assert_called_once()
            mock_exit.assert_called_once_with(1)
