"""Message and flood control manager.

This module is responsible for:
- Managing message history in chats
- Controlling which bots can reply to messages
- Enforcing flood limits between messages
- Resetting chat history when needed
"""

from typing import TYPE_CHECKING, ClassVar

from loguru import logger
from project_config import settings

if TYPE_CHECKING:
    from core.project_types import ChatID, BotIndex


class MessageManagerError(Exception):
    """Base exception for MessageManager errors."""


class FloodLimitError(MessageManagerError):
    """Raised when flood limit is exceeded."""


class MessageManager:
    """Manager for message and flood control."""

    _last_message_authors: ClassVar[dict["ChatID", set["BotIndex"]]] = {}
    _last_message_time: ClassVar[dict["ChatID", float]] = {}
    _flood_limit: ClassVar[float] = settings.bot_manager.FLOOD_LIMIT

    @classmethod
    def mark_bot_replied(cls, chat_id: "ChatID", bot_index: "BotIndex") -> None:
        """
        Marks that a bot has replied in a chat.

        Args:
            chat_id: The ID of the chat.
            bot_index: The index of the bot.
        """
        authors = cls._last_message_authors.setdefault(chat_id, set())
        authors.add(bot_index)
        logger.debug(f"Marked bot {bot_index} as replied in chat {chat_id}")

    @classmethod
    def reset_chat_history(cls, chat_id: "ChatID", total_bots: int) -> None:
        """
        Resets the message history of a chat if enough bots have replied.

        Args:
            chat_id: The ID of the chat.
            total_bots: Total number of bots in the system.
        """
        authors = cls._last_message_authors.get(chat_id, set())
        if len(authors) >= total_bots - 1:
            cls._last_message_authors[chat_id] = set()
            logger.info(f"Reset message history for chat {chat_id}")
