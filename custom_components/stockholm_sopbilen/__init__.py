"""Stockholm Sopbilen custom integration."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN: Final = "stockholm_sopbilen"
PLATFORMS: Final = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up via YAML (legacy)."""
    # We still allow YAML (sensor platform), so nothing special to do here.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (GUI)."""
    _LOGGER.info(
        "Setting up Stockholm Sopbilen config entry '%s' for address '%s'",
        entry.title,
        entry.data.get("address"),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info(
            "Unloaded Stockholm Sopbilen config entry '%s'", entry.entry_id
        )
    return unload_ok
