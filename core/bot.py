"""Class to work with boots"""

import random
import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from pyrogram.client import Client
from pyrogram import filters, enums
from pyrogram.errors import FloodWait, UserAlreadyParticipant

from core.chat_bot import ChatBot
from core.project_types import BotProtocol
from core.managers.bot_manager import BotManager
from core.typing_simulator import TypingSimulator
from core.managers.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from pyrogram.types import Message
    from core.schemas import Channel, TelegramBot


class Bot(BotProtocol):
    """Class to work with a bot"""

    def __init__(self, name: str, bot_data: "TelegramBot"):
        """
        Initializes a new Bot instance.

        Args:
            name (str): The name of the bot.
            bot_data (TelegramBot): The data of the bot.
        """
        self.name = name
        self.client: Client = Client(
            name=name,
            api_id=bot_data.api_id,
            api_hash=bot_data.api_hash,
            session_string=bot_data.session,
            in_memory=True,
        )

        self.chat_bot = ChatBot()
        self.typing_simulator = TypingSimulator()

        # Register the bot in the manager
        self.bot_manager = BotManager()
        self.bot_index = self.bot_manager.register_bot(self)

    @staticmethod
    def _normalize_chat_id(chat_id: int) -> int:
        """
        Normalizes the chat ID for internal use.

        Args:
            chat_id (int): The chat ID to normalize.

        Returns:
            int: The normalized chat ID.
        """
        str_id = str(chat_id)

        if str_id.startswith("-100"):
            return int(str_id[4:])  # Remove -100

        elif str_id.startswith("-"):
            return int(str_id[1:])  # Remove minus

        return chat_id

    def get_chat_prompt(self, chat_id: int, channels: list["Channel"]) -> str:
        """
        Gets a prompt for the chat by its ID or name.

        Args:
            chat_id (int): The ID of the chat.
            channels (list[Channel]): The list of channels.

        Returns:
            str: The prompt for the chat.

        Raises:
            Exception: If no specific prompt is found for the chat.
        """
        try:
            # Normalize chat_id
            normalized_id = self._normalize_chat_id(chat_id)

            # Look for chat in SubscriptionManager cache
            for channel in channels:
                cached_id = SubscriptionManager.chat_ids.get(channel.invite_link)

                if cached_id:
                    if self._normalize_chat_id(cached_id) == normalized_id:
                        logger.debug(f"Found prompt for chat {chat_id} by ID")
                        return channel.prompt

            # If not found for ID, return the default industry
            logger.warning(f"No specific prompt found for chat {chat_id}.")
            raise

        except Exception as e:
            logger.error(f"Error getting chat prompt: {e}")
            raise
