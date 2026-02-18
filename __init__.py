"""
Nanobot Agent custom component for Home Assistant.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AGENT_NAME,
    CONF_NANOBOT_URL,
    CONF_REQUEST_TIMEOUT,
    CONF_WEBHOOK_ID,
    DATA_CALLBACK_URL,
    DATA_CLIENT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .webhook import make_webhook_handler

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up nanobot_agent from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    client = NanobotClient(
        nanobot_url=entry.data[CONF_NANOBOT_URL],
        timeout=entry.data.get(CONF_REQUEST_TIMEOUT, DEFAULT_TIMEOUT),
        session=session,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_CALLBACK_URL: None,
        "pending": {},
    }

    webhook_id: str = entry.data[CONF_WEBHOOK_ID]
    
    # DIAGNOSTIC: Log webhook registration details
    _LOGGER.info(
        "🔗 Registering webhook — webhook_id=%s, entry_id=%s, domain=%s",
        webhook_id,
        entry.entry_id,
        DOMAIN,
    )
    
    # Call webhook_register and check what it returns
    result = webhook_register(
        hass,
        DOMAIN,
        entry.data.get(CONF_AGENT_NAME, "Nanobot"),
        webhook_id,
        make_webhook_handler(hass, entry.entry_id),
    )
    
    # Only await if it's actually a coroutine
    import inspect
    if inspect.iscoroutine(result):
        await result
    
    _LOGGER.info(
        "✅ Registered HA webhook — id=%s, URL should be: /api/webhook/%s",
        webhook_id,
        webhook_id,
    )

    _register_api_views(hass, entry.entry_id)

    # Register the conversation agent directly (not as an entity platform)
    from homeassistant.components import conversation as conv_component
    from .conversation import NanobotConversationEntity
    
    agent = NanobotConversationEntity(hass, entry)
    conv_component.async_set_agent(hass, entry, agent)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from homeassistant.components import conversation as conv_component
    
    webhook_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    conv_component.async_unset_agent(hass, entry)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


def _register_api_views(hass: HomeAssistant, entry_id: str) -> None:
    """Register the /api/nanobot_agent/register HTTP endpoint."""
    from homeassistant.components.http import HomeAssistantView  # noqa: PLC0415

    class NanobotRegisterView(HomeAssistantView):
        """Accept registration POSTs from nanobot."""

        url = "/api/nanobot_agent/register"
        name = "api:nanobot_agent:register"
        requires_auth = True

        async def post(self, request: Any) -> Any:
            """Store the nanobot callback URL."""
            _LOGGER.info("Registration POST received from %s", request.remote)
            _LOGGER.debug("Request headers: %s", dict(request.headers))
            
            try:
                data: dict[str, Any] = await request.json()
                _LOGGER.debug("Parsed JSON data: %s", data)
            except (ValueError, TypeError) as exc:
                _LOGGER.error("Failed to parse JSON in registration request: %s", exc)
                return self.json_message("Invalid JSON", status_code=400)

            callback_url: str = data.get("callback_url", "")
            if not callback_url:
                _LOGGER.error("Registration request missing 'callback_url' field. Received data: %s", data)
                return self.json_message("callback_url is required", status_code=400)

            entry_data = hass.data[DOMAIN].get(entry_id)
            if entry_data is None:
                return self.json_message("Integration not loaded", status_code=503)

            entry_data[DATA_CALLBACK_URL] = callback_url
            _LOGGER.info("Nanobot registered callback URL: %s", callback_url)
            return self.json({"status": "ok"})

    hass.http.register_view(NanobotRegisterView)


class NanobotClient:
    """Thin HTTP client for pushing inbound messages to nanobot."""

    def __init__(
        self,
        nanobot_url: str,
        timeout: int,
        session: Any,
    ) -> None:
        self._url = nanobot_url
        self._timeout = timeout
        self._session = session

    async def send_to_nanobot(
        self,
        callback_url: str,
        payload: dict[str, Any],
    ) -> bool:
        """POST payload to nanobot and return True on HTTP 2xx."""
        # Deferred import to avoid blocking event loop at module load time.
        import aiohttp  # noqa: PLC0415

        try:
            async with self._session.post(
                callback_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                if resp.status < 300:
                    return True
                _LOGGER.error(
                    "Nanobot returned HTTP %s for %s", resp.status, callback_url
                )
        except aiohttp.ClientError as exc:
            _LOGGER.error("Failed to reach nanobot at %s: %s", callback_url, exc)
        return False
