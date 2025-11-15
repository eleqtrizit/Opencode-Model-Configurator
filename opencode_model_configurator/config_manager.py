"""Configuration manager for handling JSON config file operations."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import httpx


class ConfigManager:
    """Manages configuration file operations."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize the config manager.

        :param config_path: Path to the config file. If None, defaults to config.json in current directory.
        :type config_path: Optional[Path]
        """
        if config_path is None:
            config_path = Path.cwd() / "config.json"
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the JSON file.

        :return: Configuration dictionary
        :rtype: Dict[str, Any]
        :raises FileNotFoundError: If config file doesn't exist
        :raises json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to the JSON file.

        :param config: Configuration dictionary to save
        :type config: Dict[str, Any]
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_model(self) -> str:
        """
        Get the model value from config.

        :return: Model string value
        :rtype: str
        """
        config = self.load_config()
        return config.get("model", "")

    def update_model(self, model: str) -> None:
        """
        Update the model value in config.

        :param model: Model string value (format: provider_id/model_id)
        :type model: str
        """
        config = self.load_config()
        config["model"] = model
        self.save_config(config)

    def get_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all providers from config.

        :return: Dictionary of provider_id -> provider config
        :rtype: Dict[str, Dict[str, Any]]
        """
        config = self.load_config()
        return config.get("provider", {})

    def add_provider(self, provider_id: str, provider_config: Dict[str, Any]) -> None:
        """
        Add a new provider to the config.

        :param provider_id: Unique provider identifier
        :type provider_id: str
        :param provider_config: Provider configuration with npm, name, options, and models
        :type provider_config: Dict[str, Any]
        """
        config = self.load_config()
        if "provider" not in config:
            config["provider"] = {}
        config["provider"][provider_id] = provider_config
        self.save_config(config)

    def add_model_to_provider(self, provider_id: str, model_id: str, model_config: Dict[str, Any]) -> None:
        """
        Add a model to an existing provider.

        :param provider_id: ID of the provider
        :type provider_id: str
        :param model_id: ID of the model to add
        :type model_id: str
        :param model_config: Model configuration dictionary
        :type model_config: Dict[str, Any]
        :raises ValueError: If provider not found
        """
        config = self.load_config()
        providers = config.get("provider", {})
        if provider_id not in providers:
            raise ValueError(f"Provider '{provider_id}' not found")

        if "models" not in providers[provider_id]:
            providers[provider_id]["models"] = {}
        providers[provider_id]["models"][model_id] = model_config
        self.save_config(config)

    def get_all_models(self) -> Dict[str, list[str]]:
        """
        Get all models grouped by provider.

        :return: Dictionary mapping provider IDs to lists of model IDs
        :rtype: Dict[str, list[str]]
        """
        providers = self.get_providers()
        result = {}
        for provider_id, provider_config in providers.items():
            models = provider_config.get("models", {})
            result[provider_id] = list(models.keys())
        return result

    def find_providers_for_model(self, model_id: str) -> list[str]:
        """
        Find all providers that have a model with the given ID.

        :param model_id: ID of the model to search for
        :type model_id: str
        :return: List of provider IDs that have this model
        :rtype: list[str]
        """
        models_by_provider = self.get_all_models()
        return [provider_id for provider_id, models in models_by_provider.items() if model_id in models]

    def validate_provider_model(self, provider_id: str, model_id: str) -> bool:
        """
        Validate that a provider has a specific model.

        :param provider_id: ID of the provider
        :type provider_id: str
        :param model_id: ID of the model
        :type model_id: str
        :return: True if the provider has the model, False otherwise
        :rtype: bool
        """
        models_by_provider = self.get_all_models()
        provider_models = models_by_provider.get(provider_id, [])
        return model_id in provider_models

    def delete_provider(self, provider_id: str) -> None:
        """
        Delete a provider from the config.

        :param provider_id: ID of the provider to delete
        :type provider_id: str
        :raises ValueError: If provider not found
        """
        config = self.load_config()
        providers = config.get("provider", {})
        if provider_id not in providers:
            raise ValueError(f"Provider '{provider_id}' not found")
        del providers[provider_id]
        self.save_config(config)

    def delete_model(self, model_id: str) -> None:
        """
        Delete a model from all providers that contain it.

        :param model_id: ID of the model to delete
        :type model_id: str
        :raises ValueError: If model not found in any provider
        """
        config = self.load_config()
        providers = config.get("provider", {})
        model_found = False
        for provider_id, provider_config in providers.items():
            models = provider_config.get("models", {})
            if model_id in models:
                del models[model_id]
                model_found = True
        if not model_found:
            raise ValueError(f"Model '{model_id}' not found in any provider")
        self.save_config(config)

    def fetch_provider_models(self, base_url: str, timeout: int = 10) -> list[str]:
        """
        Fetch available models from a provider's /v1/models endpoint.

        :param base_url: Base URL of the provider API
        :type base_url: str
        :param timeout: Request timeout in seconds
        :type timeout: int
        :return: List of model IDs from the provider
        :rtype: list[str]
        :raises httpx.HTTPError: If request fails
        """
        url = f"{base_url.rstrip('/')}/v1/models"
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return [model.get("id", "") for model in data.get("data", []) if model.get("id")]

    def update_provider_models(self, provider_id: str, new_model_ids: list[str]) -> Dict[str, Any]:
        """
        Update provider models with smart merge strategy.

        - Remove models that no longer exist
        - Add new models discovered
        - Preserve existing models with options

        :param provider_id: ID of the provider to update
        :type provider_id: str
        :param new_model_ids: List of model IDs from provider API
        :type new_model_ids: list[str]
        :return: Dictionary with added and removed model counts
        :rtype: Dict[str, Any]
        :raises ValueError: If provider not found
        """
        config = self.load_config()
        providers = config.get("provider", {})

        if provider_id not in providers:
            raise ValueError(f"Provider '{provider_id}' not found")

        provider_config = providers[provider_id]
        existing_models = provider_config.get("models", {})

        new_model_ids_set = set(new_model_ids)
        existing_model_ids_set = set(existing_models.keys())

        # Models to remove (exist locally but not in API response)
        to_remove = existing_model_ids_set - new_model_ids_set

        # Models to add (exist in API but not locally)
        to_add = new_model_ids_set - existing_model_ids_set

        # Remove obsolete models
        for model_id in to_remove:
            del existing_models[model_id]

        # Add new models with basic config
        for model_id in to_add:
            existing_models[model_id] = {"name": model_id}

        # Ensure models dict exists
        provider_config["models"] = existing_models

        self.save_config(config)

        return {
            "added": len(to_add),
            "removed": len(to_remove),
            "preserved": len(existing_model_ids_set & new_model_ids_set)
        }
