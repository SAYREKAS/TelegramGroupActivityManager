"""Manager for bot management.

This module is responsible for:
- Registering, initializing, and managing a group of bots.
- Defining the main bot and managing its status.
- Controlling flood and message-sending restrictions.
- Bot response logic to messages.
- Storing and processing message history in chats.
"""

import random
from time import time
from typing import TYPE_CHECKING, Optional, ClassVar, Self, Any

from loguru import logger


if TYPE_CHECKING:
    from core.project_types import (
        BotProtocol,
        ChatID,
        BotIndex,
        UserID,
        LastMessageAuthors,
        LastMessageTime,
    )


class BotManager:
    """Manager for managing a group of bots"""

    _instance: ClassVar[Optional[Self]] = None
    _bots: ClassVar[dict[str, "BotProtocol"]] = {}
    _total_bots: ClassVar[int] = 0
    _main_bot_id: ClassVar[Optional[int]] = None
    _last_message_authors: ClassVar["LastMessageAuthors"] = {}
    _last_message_time: ClassVar["LastMessageTime"] = {}
    _bot_replies: ClassVar[dict["ChatID", dict[int, set["BotIndex"]]]] = {}
    _flood_limit: ClassVar[float] = 3.0

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)

        return cls._instance

    @classmethod
    def register_bot(cls, bot: "BotProtocol") -> "BotIndex":
        """Registers a new bot in the system"""

        if bot.name not in cls._bots:
            bot_index = cls._total_bots
            cls._bots[bot.name] = bot
            cls._total_bots += 1
            logger.debug(f"Registered bot {bot.name} with index {bot_index}")
            return bot_index

        logger.debug(f"Bot {bot.name} already registered")
        return cls._bots[bot.name].bot_index

    @classmethod
    def initialize(cls) -> None:
        """Initializes the bot manager"""
        if not cls._bots:
            raise ValueError("No bots registered")

        cls.select_random_main_bot()

    @classmethod
    def select_random_main_bot(cls) -> None:
        """Selects a random bot as the main bot.

        Raises:
            ValueError: If no bots are registered or bots are not initialized
        """
        if not cls._bots:
            raise ValueError("No bots registered")

        available_bots = [
            bot for bot in cls._bots.values() if bot.client.me is not None and hasattr(bot.client.me, "id")
        ]

        if not available_bots:
            raise ValueError("No initialized bots available")

        random_bot = random.choice(available_bots)
        assert random_bot.client.me is not None
        cls._main_bot_id = random_bot.client.me.id
        logger.debug(f"Selected {random_bot.name} as main bot")

    @classmethod
    def get_main_bot(cls) -> Optional["BotProtocol"]:
        """Returns the current main bot"""
        if not cls._main_bot_id:
            return None

        return next(
            (bot for bot in cls._bots.values() if bot.client.me is not None and bot.client.me.id == cls._main_bot_id),
            None,
        )

    @classmethod
    def get_bot_ids(cls) -> set["UserID"]:
        """Returns the IDs of all bots in the system"""
        return {
            bot.client.me.id for bot in cls._bots.values() if bot.client.me is not None and hasattr(bot.client.me, "id")
        }

    @classmethod
    def can_send_message(cls, chat_id: "ChatID") -> tuple[bool, Any]:
        """Checks if a message can be sent to the chat"""
        current_time = time()
        last_message_time = cls._last_message_time.get(chat_id, 0)
        time_diff = current_time - last_message_time
        can_send = time_diff >= cls._flood_limit
        remaining_time: float = max(0.0, cls._flood_limit - time_diff)
        return can_send, remaining_time

    @classmethod
    def mark_bot_replied(cls, chat_id: "ChatID", replied_to_msg_id: int, msg_id: int, bot_index: "BotIndex") -> None:
        """Marks that a bot has replied to a message"""

        if chat_id not in cls._bot_replies:
            cls._bot_replies[chat_id] = {}

        if replied_to_msg_id not in cls._bot_replies[chat_id]:
            cls._bot_replies[chat_id][replied_to_msg_id] = set()

        if msg_id not in cls._bot_replies[chat_id][replied_to_msg_id]:
            cls._bot_replies[chat_id][replied_to_msg_id][msg_id] = set()

        cls._bot_replies[chat_id][replied_to_msg_id][msg_id].add(bot_index)
        logger.debug(
            f"Bot {bot_index} marked as replied to message {msg_id} "
            f"(reply to {replied_to_msg_id}) in chat {chat_id}"
        )

    @classmethod
    def can_bot_reply(cls) -> bool:
        """Checks if the bot can reply to a message"""
        # Bots can always reply
        return True

    @classmethod
    def reset_chat_history(cls, chat_id: "ChatID") -> None:
        """Resets the message history for a chat"""

        authors = cls._last_message_authors.get(chat_id, set())

        if len(authors) >= 2 or len(authors) >= cls._total_bots - 1:
            cls._last_message_authors[chat_id] = set()
            logger.debug(f"Reset chat history for chat {chat_id}")

    @classmethod
    def should_reply_to_bot(cls) -> bool:
        """Checks if the bot should reply to another bot's message"""
        # Bots should always maintain the conversation
        return True

    @classmethod
    def get_bots(cls) -> dict[str, "BotProtocol"]:
        """Returns a dictionary of registered bots"""
        return cls._bots
