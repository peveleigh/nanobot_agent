"""Config flow for the nanobot_agent integration."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AGENT_NAME,
    CONF_NANOBOT_URL,
    CONF_REQUEST_TIMEOUT,
    CONF_WEBHOOK_ID,
    DEFAULT_AGENT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NANOBOT_URL): str,
        vol.Optional(CONF_AGENT_NAME, default=DEFAULT_AGENT_NAME): str,
        vol.Optional(CONF_REQUEST_TIMEOUT, default=DEFAULT_TIMEOUT): int,
    }
)


class NanobotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for nanobot_agent."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """First (and only) step: collect nanobot URL and preferences."""
        errors: dict[str, str] = {}

        if user_input is not None:
            nanobot_url: str = user_input[CONF_NANOBOT_URL].rstrip("/")
            reachable = await self._test_connection(nanobot_url)
            if not reachable:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(nanobot_url)
                self._abort_if_unique_id_configured()

                webhook_id = secrets.token_hex(16)
                return self.async_create_entry(
                    title=user_input.get(CONF_AGENT_NAME, DEFAULT_AGENT_NAME),
                    data={
                        CONF_NANOBOT_URL: nanobot_url,
                        CONF_AGENT_NAME: user_input.get(
                            CONF_AGENT_NAME, DEFAULT_AGENT_NAME
                        ),
                        CONF_WEBHOOK_ID: webhook_id,
                        CONF_REQUEST_TIMEOUT: user_input.get(
                            CONF_REQUEST_TIMEOUT, DEFAULT_TIMEOUT
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, url: str) -> bool:
        """Return True if nanobot's health endpoint responds with HTTP 2xx."""
        # Import deferred to avoid blocking the event loop at module load time.
        import aiohttp  # noqa: PLC0415

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status < 500
        except aiohttp.ClientError:
            return False
