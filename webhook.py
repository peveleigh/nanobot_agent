"""Webhook handler for receiving nanobot agent responses."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Awaitable
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def make_webhook_handler(hass: HomeAssistant, entry_id: str) -> Callable[..., Awaitable[None]]:
    """
    Return a webhook handler bound to *entry_id*.

    The returned coroutine is passed directly to HA's webhook.async_register().
    It resolves the Future that conversation.py's async_process() is awaiting,
    completing the request/response cycle.

    Expected JSON body from nanobot::

        {
            "conversation_id": "abc-123",
            "sender_id":       "ha_user",
            "text":            "I've turned on the kitchen lights.",
            "metadata":        {}
        }
    """

    async def handle_webhook(
        hass: HomeAssistant,
        webhook_id: str,
        request: Any,
    ) -> None:
        """
        Receive an agent response from nanobot and resolve the waiting Future.

        Steps
        -----
        1. Parse the JSON body.
        2. Extract conversation_id and response text.
        3. Look up the matching Future in hass.data[DOMAIN][entry_id]["pending"].
        4. Resolve it so async_process() in conversation.py can return.
        """
        # DIAGNOSTIC: Log that webhook handler was called
        _LOGGER.info(
            "🔔 WEBHOOK HANDLER CALLED — webhook_id=%s, entry_id=%s, remote=%s",
            webhook_id,
            entry_id,
            getattr(request, 'remote', 'unknown'),
        )
        
        # ------------------------------------------------------------------
        # 1. Parse body
        # ------------------------------------------------------------------
        try:
            data: dict[str, Any] = await request.json()
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Nanobot webhook received a non-JSON body; ignoring. Error: %s", exc
            )
            return

        # ------------------------------------------------------------------
        # 2. Validate required fields
        # ------------------------------------------------------------------
        conversation_id: str = data.get("conversation_id", "").strip()
        text: str = data.get("text", "").strip()

        if not conversation_id:
            _LOGGER.warning(
                "Nanobot webhook payload missing 'conversation_id': %s", data
            )
            return

        if not text:
            _LOGGER.warning(
                "Nanobot webhook payload missing 'text' for conversation %s: %s",
                conversation_id,
                data,
            )
            return

        _LOGGER.info(
            "📨 Webhook received response — conversation_id=%s, text=%r",
            conversation_id,
            text,
        )

        # ------------------------------------------------------------------
        # 3. Retrieve the entry-scoped pending futures dict
        # ------------------------------------------------------------------
        entry_data: dict | None = hass.data.get(DOMAIN, {}).get(entry_id)
        if entry_data is None:
            _LOGGER.error(
                "Webhook fired for unknown entry_id=%s. "
                "The integration may have been unloaded.",
                entry_id,
            )
            return

        pending: dict[str, asyncio.Future[str]] = entry_data.get("pending", {})
        
        # DIAGNOSTIC: Log pending conversations
        _LOGGER.info(
            "📋 Pending conversations for entry_id=%s: %s",
            entry_id,
            list(pending.keys()),
        )

        # ------------------------------------------------------------------
        # 4. Resolve the Future so conversation.py can return the response
        # ------------------------------------------------------------------
        future: asyncio.Future[str] | None = pending.get(conversation_id)

        if future is None:
            _LOGGER.warning(
                "No pending Future for conversation_id=%s. "
                "The request may have already timed out or the response arrived twice.",
                conversation_id,
            )
            return

        if future.done():
            _LOGGER.warning(
                "Future for conversation_id=%s is already resolved; "
                "ignoring duplicate webhook delivery.",
                conversation_id,
            )
            return

        future.set_result(text)
        _LOGGER.info(
            "✅ RESOLVED Future for conversation_id=%s with text=%r",
            conversation_id,
            text,
        )

    return handle_webhook
