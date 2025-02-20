"""Class to work with bots"""

import random
import asyncio
from typing import TYPE_CHECKING, Optional

from loguru import logger
from pyrogram import filters
from pyrogram.client import Client
from pyrogram.types import Chat, ChatPreview
from pyrogram.errors import FloodWait, UserAlreadyParticipant

from core.chat_bot import ChatBot
from core.managers.bot_manager import BotManager
from core.managers.subscription_manager import SubscriptionManager
from core.project_types import BotProtocol
from core.typing_simulator import TypingSimulator

if TYPE_CHECKING:
    from pyrogram.types import Message
    from core.schemas import Channel, TelegramBot


class BotError(Exception):
    """Base exception for Bot errors."""


class ChatAccessError(BotError):
    """Raised when there's an error accessing a chat."""


class MessageProcessingError(BotError):
    """Raised when there's an error processing a message."""


class Bot(BotProtocol):
    """Class to work with a bot"""

    def __init__(self, name: str, bot_data: "TelegramBot") -> None:
        """
        Initializes a new Bot instance.

        Args:
            name (str): The name of the bot.
            bot_data: The data of the bot.
        """
        try:
            self.name = name
            self.client = Client(
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

        except Exception as e:
            logger.error(f"Failed to initialize bot {name}: {e}")
            raise BotError(f"Bot initialization failed: {e}") from e

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
        """Gets a prompt for the chat by its ID."""
        try:
            # Normalize chat_id
            normalized_id = self._normalize_chat_id(chat_id)
            logger.debug(f"Looking for prompt for normalized chat ID: {normalized_id}")

            # Log available channels and their IDs
            for channel in channels:
                cached_id = SubscriptionManager.chat_ids.get(channel.invite_link)
                if cached_id:
                    logger.debug(
                        f"Channel {channel.invite_link} has cached ID: {cached_id} "
                        f"(normalized: {self._normalize_chat_id(cached_id)})"
                    )

            # Look for chat in SubscriptionManager cache
            for channel in channels:
                cached_id = SubscriptionManager.chat_ids.get(channel.invite_link)
                if cached_id:
                    cached_normalized_id = self._normalize_chat_id(cached_id)
                    if cached_normalized_id == normalized_id:
                        logger.debug(f"Found prompt for chat {chat_id} by ID")
                        return channel.prompt

            # Try to find by invite link
            for channel in channels:
                if channel.invite_link in SubscriptionManager.chat_ids:
                    if SubscriptionManager.chat_ids[channel.invite_link] == chat_id:
                        logger.debug(f"Found prompt for chat {chat_id} by invite link")
                        return channel.prompt

            raise ValueError(f"No prompt found for chat {chat_id}")

        except Exception as e:
            logger.error(f"Error getting chat prompt: {e}")
            raise

    async def _check_message_conditions(self, message: "Message") -> bool:
        """Check if the message meets processing conditions."""
        if not message.from_user or not message.chat:
            return False

        chat_id = message.chat.id
        from_user = message.from_user.first_name

        # Check flood control
        can_send, remaining_time = self.bot_manager.can_send_message(chat_id)
        if not can_send:
            logger.debug(f"[{self.name}] Skipping message (flood control: {remaining_time:.1f}s remaining)")
            return False

        # Check if it's a reply to this bot's message
        if not self.client.me:
            return False

        if message.reply_to_message and message.reply_to_message.from_user.id == self.client.me.id:
            logger.info(f"[{self.name}] Processing reply from {from_user}")
            return True

        # Check if it's a message from another bot
        return message.from_user.id in self.bot_manager.get_bot_ids()

    async def _send_response(self, chat_id: int, response: str, reply_to_message_id: Optional[int]) -> None:
        """Send a response message with typing simulation."""
        if not reply_to_message_id:
            logger.warning(f"[{self.name}] No message to reply to in chat {chat_id}")
            return

        # Simulate natural delay
        wait_time = random.uniform(0.5, 3.0)
        logger.debug(f"[{self.name}] Waiting {wait_time:.1f}s before typing")
        await asyncio.sleep(wait_time)

        # Simulate typing
        await self.typing_simulator.simulate_typing(self.client, chat_id, len(response))

        # Send message
        await self.client.send_message(chat_id=chat_id, text=response, reply_to_message_id=reply_to_message_id)
        logger.info(f"[{self.name}] Sent reply in chat {chat_id}")

    async def process_message(self, message: "Message", channels: list["Channel"]) -> None:
        """
        Processes the received message.

        Args:
            message (Message): The message to process.
            channels (list[Channel]): The list of channels.
        """
        try:
            chat_id = message.chat.id
            logger.info(f"[{self.name}] Processing message in chat {chat_id}")

            # Get prompt for the chat
            prompt = self.get_chat_prompt(chat_id=chat_id, channels=channels)
            if not prompt:
                return

            # Get the text of the message being replied to
            reply_to_message_id = message.id if message.text else None

            # Generate a response
            response = self.chat_bot.generate_response(
                chat_id=chat_id,
                prompt=prompt,
                message=message.text if message.text else None,
                is_reply=True if message.reply_to_message else False,
                reply_text=message.reply_to_message.text if message.reply_to_message else None,
            )

            # Send response
            await self._send_response(chat_id=chat_id, response=response, reply_to_message_id=reply_to_message_id)

            # Mark that the bot has replied to the message
            if message.id:
                self.bot_manager.mark_bot_replied(
                    chat_id=chat_id,
                    replied_to_msg_id=message.reply_to_message.id if message.reply_to_message else message.id,
                    msg_id=message.id,
                    bot_index=self.bot_index,
                )
                logger.debug(f"[{self.name}] Marked as replied in chat {chat_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise MessageProcessingError(f"Failed to process message: {e}") from e

    async def _get_chat_access(self, chat_id: int, invite_link: str) -> Chat:
        """
        Get access to a chat.

        Args:
            chat_id: The ID of the chat.
            invite_link: The invite link of the chat.

        Returns:
            Chat: The chat object.

        Raises:
            ChatAccessError: If failed to access the chat.
        """
        try:
            # Try direct access
            try:
                chat = await self.client.get_chat(chat_id)
                if isinstance(chat, ChatPreview):
                    raise ChatAccessError("Received ChatPreview instead of Chat")
                return chat  # mypy knows it's Chat here because of isinstance check

            except Exception:
                pass

            # Try via invite link
            try:
                chat = await self.client.join_chat(invite_link)
                if isinstance(chat, ChatPreview):
                    raise ChatAccessError("Received ChatPreview instead of Chat")
                return chat

            except UserAlreadyParticipant:
                chat = await self.client.get_chat(chat_id)
                if isinstance(chat, ChatPreview):
                    raise ChatAccessError("Received ChatPreview instead of Chat")
                return chat

            except Exception as e:
                logger.error(f"Failed to join chat: {e}")
                raise

        except Exception as e:
            raise ChatAccessError(f"Failed to access chat: {e}")

    async def send_initial_message(self, chat_id: int, invite_link: str) -> None:
        """
        Sends the initial message to the chat.

        Args:
            chat_id (int): The ID of the chat.
            invite_link (str): The invite link of the chat.
        """
        max_retries = 5
        retry_delay = 10
        channels = SubscriptionManager.get_channels()

        for attempt in range(max_retries):
            try:
                # Get chat access
                current_chat = await self._get_chat_access(chat_id, invite_link)

                # Generate and send the message
                message = await self._generate_initial_message(
                    chat_title=current_chat.title,
                    chat_id=chat_id,
                    channels=channels,
                )

                await self.typing_simulator.simulate_typing(self.client, chat_id, len(message))

                await self.client.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)

                logger.info(f"[{self.name}] Sent initial message to chat {chat_id}")
                return

            except FloodWait:
                raise
            except Exception as e:
                logger.warning(f"[{self.name}] Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.name}] Failed after {max_retries} attempts")
                    raise

    async def _generate_initial_message(self, chat_title: str, chat_id: int, channels: list["Channel"]) -> str:
        """
        Generates the initial message for the chat.

        Args:
            chat_title (str): The title of the chat.
            chat_id (int): The ID of the chat.
            channels (list[Channel]): The list of channels.

        Returns:
            str: The generated initial message.
        """
        try:
            # Get prompt for the chat
            prompt = self.get_chat_prompt(chat_id=chat_id, channels=channels)
            logger.debug(f"Using prompt for chat {chat_title} (ID: {chat_id}): {prompt[:50]}...")

            # Use ChatBot to generate the message
            message = self.chat_bot.generate_initial_message(prompt=prompt)
            logger.debug(f"Generated initial message for chat {chat_title}: {message[:50]}...")
            return message

        except ValueError as e:
            logger.warning(f"Error generating initial message: {e}")
            return "😂"

        except Exception as e:
            logger.error(f"Error generating initial message: {e}")
            return "I wonder what you think about the latest developments in this field?"

    async def start(self) -> None:
        """Starts the bot."""
        try:
            await self.client.start()
            logger.info(f"Bot {self.name} started")

            @self.client.on_message(filters.text & filters.group)  # type: ignore
            async def message_handler(client: Client, message: "Message") -> None:
                """
                Handles incoming messages.

                Args:
                    client: The client instance.
                    message: The received message.
                """
                try:
                    if not await self._check_message_conditions(message):
                        return

                    channels = SubscriptionManager.get_channels()
                    await self.process_message(message=message, channels=channels)
                    self.bot_manager.reset_chat_history(message.chat.id)

                except Exception as ex:
                    logger.error(f"Error in message handler: {ex}")

        except Exception as e:
            logger.error(f"Failed to start bot {self.name}: {e}")
            raise BotError(f"Bot start failed: {e}") from e
