"""ConversationEntity for the nanobot_agent integration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.conversation import AbstractConversationAgent
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AGENT_NAME,
    DATA_CALLBACK_URL,
    DATA_CLIENT,
    DEFAULT_AGENT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

RESPONSE_TIMEOUT = 30.0


# This file is no longer used as an entity platform.
# The conversation agent is now registered directly in __init__.py


class NanobotConversationEntity(AbstractConversationAgent):
    """Home Assistant ConversationEntity backed by nanobot."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        # Call parent class initialization
        super().__init__()
        
        self.hass = hass
        self._entry = entry
        self._entry_id = entry.entry_id
        self._attr_name = entry.data.get(CONF_AGENT_NAME, DEFAULT_AGENT_NAME)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_agent"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Accept all languages."""
        return "*"

    async def _validate_callback_url(self, callback_url: str | None) -> bool:
        """Validate that the callback URL is reachable."""
        if not callback_url:
            return False
        
        # Import deferred to avoid blocking event loop at module load time.
        import aiohttp  # noqa: PLC0415
        
        try:
            session = async_get_clientsession(self.hass)
            async with session.head(
                callback_url,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status < 500
        except aiohttp.ClientError:
            return False

    async def async_process(self, user_input: Any) -> Any:
        """Process an incoming utterance."""
        # Deferred imports.
        from homeassistant.components.conversation import ConversationResult  # noqa: PLC0415
        from homeassistant.helpers import intent  # noqa: PLC0415

        entry_data: dict = self.hass.data[DOMAIN][self._entry_id]
        client = entry_data[DATA_CLIENT]
        callback_url: str | None = entry_data.get(DATA_CALLBACK_URL)

        if not callback_url:
            _LOGGER.error(
                "Nanobot has not registered a callback URL yet. "
                "Ensure nanobot is running and can reach /api/nanobot_agent/register."
            )
            return self._error_result(user_input, "Nanobot is not connected.", intent)
        
        # Validate callback URL is reachable
        if not await self._validate_callback_url(callback_url):
            _LOGGER.warning(
                "Nanobot callback URL %s is not reachable. "
                "The nanobot service may be offline or misconfigured.",
                callback_url
            )
            return self._error_result(user_input, "Nanobot service is not reachable.", intent)

        conversation_id: str = user_input.conversation_id or str(uuid.uuid4())

        loop = asyncio.get_event_loop()
        future: asyncio.Future[str] = loop.create_future()
        pending: dict[str, asyncio.Future[str]] = entry_data["pending"]
        pending[conversation_id] = future
        
        # DIAGNOSTIC: Log the conversation setup
        _LOGGER.info(
            "🎯 Created Future for conversation_id=%s, total pending=%d",
            conversation_id,
            len(pending),
        )

        payload = {
            "sender_id": user_input.context.user_id or "ha_user",
            "conversation_id": conversation_id,
            "text": user_input.text,
            "language": user_input.language,
            "metadata": {
                "device_id": user_input.device_id,
                "agent_id": str(self._attr_unique_id),
            },
        }

        _LOGGER.info(
            "📤 Forwarding to nanobot (conversation=%s, callback=%s): %r",
            conversation_id,
            callback_url,
            user_input.text,
        )

        success = await client.send_to_nanobot(callback_url, payload)
        if not success:
            pending.pop(conversation_id, None)
            return self._error_result(
                user_input,
                "Could not reach nanobot.",
                intent,
            )

        try:
            _LOGGER.info(
                "⏳ Waiting for response (conversation=%s, timeout=%ds)...",
                conversation_id,
                RESPONSE_TIMEOUT,
            )
            response_text: str = await asyncio.wait_for(
                future,
                timeout=RESPONSE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "⏰ TIMEOUT waiting for nanobot response (conversation=%s). "
                "Future still pending: %s",
                conversation_id,
                conversation_id in pending,
            )
            pending.pop(conversation_id, None)
            return self._error_result(
                user_input,
                "Nanobot did not respond in time.",
                intent,
            )
        finally:
            pending.pop(conversation_id, None)

        _LOGGER.info(
            "✅ Received response for conversation %s: %r",
            conversation_id,
            response_text,
        )

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(response_text)
        return ConversationResult(
            conversation_id=conversation_id,
            response=response,
        )

    @staticmethod
    def _error_result(user_input: Any, message: str, intent: Any) -> Any:
        """Return a ConversationResult representing an error."""
        # Import ConversationResult locally since it's not in module scope
        from homeassistant.components.conversation import ConversationResult  # noqa: PLC0415
        
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_error(
            intent.IntentResponseErrorCode.UNKNOWN,
            message,
        )
        return ConversationResult(
            conversation_id=user_input.conversation_id,
            response=response,
        )
