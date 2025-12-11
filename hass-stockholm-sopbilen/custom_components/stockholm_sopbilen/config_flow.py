from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN
from .sensor import CONF_ADDRESS, DEFAULT_NAME  # reuse constants

_LOGGER = logging.getLogger(__name__)


class StockholmSopbilenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stockholm Sopbilen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """First step: ask for address and name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            name = user_input[CONF_NAME].strip()

            # Use address as unique id so you can't add the same address twice
            await self.async_set_unique_id(address.lower())
            self._abort_if_unique_id_configured()

            _LOGGER.info(
                "Creating Stockholm Sopbilen entry: name='%s', address='%s'",
                name,
                address,
            )

            return self.async_create_entry(
                title=name or DEFAULT_NAME,
                data={"address": address},
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
