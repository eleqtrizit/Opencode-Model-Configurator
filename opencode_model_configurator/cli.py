"""CLI interface for the configuration switcher."""

import argparse
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from opencode_model_configurator.config_manager import ConfigManager

console = Console()


class HelpOnErrorParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser that prints full help when arguments are missing.

    :param args: Positional arguments for ArgumentParser
    :param kwargs: Keyword arguments for ArgumentParser
    """

    def error(self, message: str) -> None:
        """
        Override error to print full help instead of short usage.

        :param message: Error message from argparse
        :type message: str
        """
        self.print_help(sys.stderr)
        self.exit(2, f"\n{self.prog}: error: {message}\n")


def list_models(config_manager: ConfigManager) -> None:
    """
    List all models grouped by provider.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    """
    models_by_provider = config_manager.get_all_models()
    if not models_by_provider:
        console.print("[yellow]No providers or models found in config[/yellow]")
        return

    table = Table(title="Available Models")
    table.add_column("Provider", style="cyan")
    table.add_column("Models", style="green")

    for provider, models in models_by_provider.items():
        models_str = ", ".join(models) if models else "[red]No models[/red]"
        table.add_row(provider, models_str)

    console.print(table)


def show_config(config_manager: ConfigManager) -> None:
    """
    Show current model configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    """
    try:
        model = config_manager.get_model()
        if not model:
            console.print("[yellow]No model configuration found[/yellow]")
            return

        table = Table(title="Current Model Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("model", model)

        console.print(table)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def change_model(config_manager: ConfigManager, model_value: str) -> None:
    """
    Change the model configuration value.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param model_value: Model value in format <provider_id>/<model_id>
    :type model_value: str
    """
    try:
        # Expect format: provider_id/model_id
        if "/" not in model_value:
            console.print(
                "[red]Error: Model value must be in format provider_id/model_id[/red]\n"
                "[yellow]Example: lmstudio_mac/qwen3-32b[/yellow]"
            )
            console.print("\n[yellow]Available models:[/yellow]")
            list_models(config_manager)
            sys.exit(1)

        parts = model_value.split("/", 1)
        provider_id = parts[0].strip()
        model_id = parts[1].strip()

        # Validate provider/model combination
        if not config_manager.validate_provider_model(provider_id, model_id):
            console.print(
                f"[red]Error: Model '{model_id}' not found in provider '{provider_id}'[/red]"
            )
            console.print("\n[yellow]Available models:[/yellow]")
            list_models(config_manager)
            sys.exit(1)

        final_value = f"{provider_id}/{model_id}"
        config_manager.update_model(final_value)
        console.print(f"[green]Updated model to: {final_value}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def add_provider(
    config_manager: ConfigManager, provider_id: str, npm_package: str, name: str, base_url: str
) -> None:
    """
    Add a new provider to the configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param provider_id: Unique provider identifier
    :type provider_id: str
    :param npm_package: NPM package for the provider
    :type npm_package: str
    :param name: Provider display name
    :type name: str
    :param base_url: API base URL
    :type base_url: str
    """
    provider_config = {
        "npm": npm_package,
        "name": name,
        "options": {"baseURL": base_url},
        "models": {},
    }

    try:
        config_manager.add_provider(provider_id, provider_config)
        console.print(f"[green]Added provider: {provider_id} ({name})[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def add_model(config_manager: ConfigManager, provider_id: str, model_id: str, model_name: str) -> None:
    """
    Add a model to an existing provider.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param provider_id: Provider ID
    :type provider_id: str
    :param model_id: Model ID
    :type model_id: str
    :param model_name: Model display name
    :type model_name: str
    """
    try:
        model_config = {"name": model_name}
        config_manager.add_model_to_provider(provider_id, model_id, model_config)
        console.print(f"[green]Added model '{model_id}' to provider '{provider_id}'[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def delete_provider(config_manager: ConfigManager, provider_id: str, auto_confirm: bool = False) -> None:
    """
    Delete a provider from the configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param provider_id: ID of the provider to delete
    :type provider_id: str
    :param auto_confirm: Skip confirmation prompt if True
    :type auto_confirm: bool
    """
    if not auto_confirm:
        response = input("ARE YOU SURE?! [y/N]: ").strip().lower()
        if response != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        config_manager.delete_provider(provider_id)
        console.print(f"[green]Deleted provider: {provider_id}[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def delete_model(config_manager: ConfigManager, model_id: str, auto_confirm: bool = False) -> None:
    """
    Delete a model from all providers that contain it.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param model_id: ID of the model to delete
    :type model_id: str
    :param auto_confirm: Skip confirmation prompt if True
    :type auto_confirm: bool
    """
    if not auto_confirm:
        response = input("ARE YOU SURE?! [y/N]: ").strip().lower()
        if response != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        config_manager.delete_model(model_id)
        console.print(f"[green]Deleted model: {model_id}[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def update_models(config_manager: ConfigManager) -> None:
    """
    Update models for all providers by querying their /v1/models endpoints.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    """
    try:
        providers = config_manager.get_providers()
        if not providers:
            console.print("[yellow]No providers found in config[/yellow]")
            return

        table = Table(title="Model Update Results")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Added", style="green")
        table.add_column("Removed", style="red")
        table.add_column("Preserved", style="yellow")

        for provider_id, provider_config in providers.items():
            base_url = provider_config.get("options", {}).get("baseURL")
            if not base_url:
                table.add_row(provider_id, "[yellow]No baseURL[/yellow]", "-", "-", "-")
                continue

            try:
                model_ids = config_manager.fetch_provider_models(base_url)
                result = config_manager.update_provider_models(provider_id, model_ids)

                table.add_row(
                    provider_id,
                    "[green]Success[/green]",
                    str(result["added"]),
                    str(result["removed"]),
                    str(result["preserved"])
                )
            except httpx.HTTPError as e:
                table.add_row(provider_id, f"[red]HTTP Error: {e}[/red]", "-", "-", "-")
            except Exception as e:
                table.add_row(provider_id, f"[red]Error: {e}[/red]", "-", "-", "-")

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    :return: Configured argument parser
    :rtype: argparse.ArgumentParser
    """
    parser = HelpOnErrorParser(
        prog="ocs",
        description="Open Code Model Configurator",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: ~/.config/opencode/config.json)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", parser_class=HelpOnErrorParser)

    # ls command
    subparsers.add_parser("ls", help="List all models grouped by provider")

    # show command
    subparsers.add_parser("show", help="Show current model configuration")

    # update command
    subparsers.add_parser("update", help="Update models by querying provider /v1/models endpoints")

    # change command
    change_parser = subparsers.add_parser(
        "change", help="Change the model configuration value"
    )
    change_parser.add_argument(
        "model_value",
        help="Model value in format <provider_id>/<model_id> (e.g., lmstudio_mac/qwen3-32b)",
    )

    # add command with subcommands
    add_parser = subparsers.add_parser("add", help="Add provider or model")
    add_subparsers = add_parser.add_subparsers(dest="add_type", help="What to add", parser_class=HelpOnErrorParser)

    # add provider subcommand
    add_provider_parser = add_subparsers.add_parser(
        "provider", help="Add a new provider"
    )
    add_provider_parser.add_argument(
        "--npm", required=True, help="NPM package", dest="npm_package", default="@ai-sdk/openai-compatible")
    add_provider_parser.add_argument("--name", required=True, help="Provider display name")
    add_provider_parser.add_argument(
        "--base-url", required=True, help="API base URL", dest="base_url"
    )

    # add model subcommand
    add_model_parser = add_subparsers.add_parser(
        "model", help="Add a model to a provider"
    )
    add_model_parser.add_argument("provider_id", help="Provider ID")
    add_model_parser.add_argument("model_id", help="Model ID")
    add_model_parser.add_argument("model_name", help="Model display name")

    # delete command with subcommands
    delete_parser = subparsers.add_parser("delete", help="Delete provider or model")
    delete_subparsers = delete_parser.add_subparsers(
        dest="delete_type", help="What to delete", parser_class=HelpOnErrorParser)

    # delete provider subcommand
    delete_provider_parser = delete_subparsers.add_parser(
        "provider", help="Delete a provider"
    )
    delete_provider_parser.add_argument("provider_id", help="Provider ID to delete")
    delete_provider_parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_confirm", help="Auto-confirm deletion"
    )

    # delete model subcommand
    delete_model_parser = delete_subparsers.add_parser(
        "model", help="Delete a model"
    )
    delete_model_parser.add_argument("model_id", help="Model ID to delete")
    delete_model_parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_confirm", help="Auto-confirm deletion"
    )

    return parser


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    default_config_path = Path.home() / ".config" / "opencode" / "config.json"
    config_path_to_use = getattr(args, "config", None) or default_config_path
    config_manager = ConfigManager(config_path_to_use)

    if args.command == "ls":
        list_models(config_manager)
    elif args.command == "show":
        show_config(config_manager)
    elif args.command == "update":
        update_models(config_manager)
    elif args.command == "change":
        change_model(config_manager, args.model_value)
    elif args.command == "add":
        if not hasattr(args, "add_type") or args.add_type is None:
            parser.parse_args(["add", "--help"])
            sys.exit(1)
        elif args.add_type == "provider":
            provider_id = args.name.lower().replace(" ", "-")
            provider_id = [x for x in provider_id if x.isalnum() or x in ["-", "_"]]
            provider_id = "".join(provider_id)
            add_provider(config_manager, provider_id, args.npm_package, args.name, args.base_url)
        elif args.add_type == "model":
            add_model(config_manager, args.provider_id, args.model_id, args.model_name)
    elif args.command == "delete":
        if not hasattr(args, "delete_type") or args.delete_type is None:
            parser.parse_args(["delete", "--help"])
            sys.exit(1)
        elif args.delete_type == "provider":
            auto_confirm = getattr(args, "auto_confirm", False)
            delete_provider(config_manager, args.provider_id, auto_confirm)
        elif args.delete_type == "model":
            auto_confirm = getattr(args, "auto_confirm", False)
            delete_model(config_manager, args.model_id, auto_confirm)
