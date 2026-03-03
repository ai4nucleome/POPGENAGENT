"""
Centralized configuration loader for PopGenAgent.
Reads config.yaml from the project root and provides a global accessor.
"""

import os
import yaml
from typing import Any, Dict, Optional

_CONFIG: Optional[Dict[str, Any]] = None
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def load_config(path: str = None) -> Dict[str, Any]:
    """Load and cache the YAML configuration file."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    config_path = path or _CONFIG_PATH
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please copy config.yaml.example to config.yaml and fill in your values."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG


def get_llm_config() -> Dict[str, Any]:
    """Return the default LLM configuration block."""
    cfg = load_config()
    return cfg.get("llm", {})


def get_api_pool_config() -> list:
    """Return the API key pool list."""
    cfg = load_config()
    return cfg.get("api_pool", [])


def get_pubmed_config() -> Dict[str, Any]:
    """Return PubMed retrieval settings."""
    cfg = load_config()
    return cfg.get("pubmed", {})


def get_django_config() -> Dict[str, Any]:
    """Return Django-specific settings."""
    cfg = load_config()
    return cfg.get("django", {})


def reload_config(path: str = None) -> Dict[str, Any]:
    """Force-reload configuration (e.g. after user edits config.yaml)."""
    global _CONFIG
    _CONFIG = None
    return load_config(path)
