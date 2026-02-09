"""
Factory for creating platform-specific booking clients.

Supports both the legacy flat config format (Resy-only) and the new
nested format for multi-platform configs.
"""

import json

from .base import BookingClient, BookingClientError


def create_client(platform: str, credentials: dict) -> BookingClient:
    """
    Create a booking client for the given platform.

    Args:
        platform: Platform name ('resy', 'opentable')
        credentials: Platform-specific credential dict

    Returns:
        A configured BookingClient instance

    Raises:
        BookingClientError: If the platform is unknown
    """
    if platform == "resy":
        from .resy_client import ResyClient
        return ResyClient(
            api_key=credentials["api_key"],
            auth_token=credentials["auth_token"],
        )
    elif platform == "opentable":
        from .opentable_client import OpenTableClient
        return OpenTableClient(credentials)
    else:
        raise BookingClientError(f"Unknown platform: {platform}", platform=platform)


def load_client_from_config(platform: str = "resy", config_path: str = "config.json") -> BookingClient:
    """
    Load a booking client from a config file.

    Supports two config formats:

    Legacy flat format (backwards compatible, assumes Resy):
        {"api_key": "...", "auth_token": "..."}

    New nested format:
        {"resy": {"api_key": "...", "auth_token": "..."}, "opentable": {...}}

    Args:
        platform: Platform name ('resy', 'opentable')
        config_path: Path to JSON config file

    Returns:
        A configured BookingClient instance
    """
    with open(config_path) as f:
        config = json.load(f)

    # Check for nested format first
    if platform in config and isinstance(config[platform], dict):
        credentials = config[platform]
    elif platform == "resy" and "api_key" in config:
        # Legacy flat format — only works for Resy
        credentials = config
    else:
        raise BookingClientError(
            f"No credentials found for platform '{platform}' in {config_path}. "
            f"Add a '{platform}' section to your config.json.",
            platform=platform,
        )

    return create_client(platform, credentials)
