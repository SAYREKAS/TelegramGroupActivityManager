"""Class to work with bots"""

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

    async def should_process_message(self, message: "Message") -> bool:
        """
        Checks if the message should be processed.

        Args:
            message (Message): The message to check.

        Returns:
            bool: True if the message should be processed, False otherwise.
        """
        try:
            chat_id = message.chat.id
            from_user = message.from_user.first_name

            # Check flood control
            can_send, remaining_time = self.bot_manager.can_send_message(chat_id)
            if not can_send:
                logger.debug(f"[{self.name}] Skipping message (flood control: {remaining_time:.1f}s remaining)")
                return False

            # If it's a reply to this bot's message
            if self.client.me is None:
                raise

            if message.reply_to_message and message.reply_to_message.from_user.id == self.client.me.id:
                logger.info(f"[{self.name}] Processing reply to own message from {from_user}")
                logger.info(f"[{self.name}] User {from_user} replied to bot message: {message.text}")
                return True

            # If it's a message from another bot
            if message.from_user.id in self.bot_manager.get_bot_ids():
                return True

            return False

        except Exception as e:
            logger.error(f"[{self.name}] Error in should_process_message: {e}")
            return False
