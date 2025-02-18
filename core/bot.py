"""Class to work with bots"""

import asyncio
import random
from typing import TYPE_CHECKING

from loguru import logger
from pyrogram import filters, enums
from pyrogram.client import Client
from pyrogram.types import Chat
from pyrogram.errors import FloodWait, UserAlreadyParticipant

from core.chat_bot import ChatBot
from core.managers.bot_manager import BotManager
from core.managers.subscription_manager import SubscriptionManager
from core.project_types import BotProtocol
from core.typing_simulator import TypingSimulator

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
            bot_data: The data of the bot.
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

            # Wait a random time before starting to type
            wait_time = random.uniform(0.5, 3.0)
            logger.debug(f"[{self.name}] Waiting {wait_time:.1f}s before typing")
            await asyncio.sleep(wait_time)

            # Simulate typing
            typing_time = len(response) / 20  # Approximately 20 characters per second
            logger.debug(f"[{self.name}] Typing for {typing_time:.1f}s")
            await self.client.send_chat_action(chat_id, enums.ChatAction.TYPING)
            await asyncio.sleep(typing_time)
            await self.client.send_chat_action(chat_id, enums.ChatAction.CANCEL)

            # Send the response
            if reply_to_message_id is None:
                logger.warning(f"[{self.name}] No message to reply to in chat {chat_id}")
                return

            await self.client.send_message(chat_id=chat_id, text=response, reply_to_message_id=reply_to_message_id)
            logger.info(f"[{self.name}] Sent reply in chat {chat_id}")

            # Mark that the bot has replied to the message
            if message.id:
                self.bot_manager.mark_bot_replied(
                    self.bot_index,
                    chat_id,
                    message.id,
                    message.reply_to_message.id if message.reply_to_message else message.id,
                )
                logger.debug(f"[{self.name}] Marked as replied in chat {chat_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def join_chat(self, chat_id: int, invite_link: str) -> bool:
        """
        Joins the chat if not already a participant.

        Args:
            chat_id (int): The ID of the chat.
            invite_link (str): The invite link of the chat.

        Returns:
            bool: True if the bot successfully joined the chat or is already a participant, False otherwise.
        """
        try:
            # First, try to join via invite_link
            try:
                chat = await self.client.join_chat(invite_link)
                logger.info(f"Bot {self.name} joined chat {chat.id}")
                return True
            except UserAlreadyParticipant:
                # If already in the group, just return success
                logger.info(f"Bot {self.name} already in chat")
                return True
            except Exception:
                # Try to join via chat_id
                try:
                    await self.client.get_chat(chat_id)
                    logger.info(f"Bot {self.name} accessed chat {chat_id}")
                    return True
                except Exception as inner_e:
                    logger.error(f"Bot {self.name} failed to access chat: {inner_e}")
                    return False
        except Exception as e:
            logger.error(f"Bot {self.name} failed to join chat: {str(e)}")
            return False

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

        except Exception as e:
            logger.error(f"Error generating initial message: {e}")
            return "I wonder what you think about the latest developments in this field?"

    async def send_initial_message(self, chat_id: int, invite_link: str) -> None:
        """
        Sends the initial message to the chat.

        Args:
            chat_id (int): The ID of the chat.
            invite_link (str): The invite link of the chat.
        """
        max_retries = 5
        retry_delay = 10
        channels: list["Channel"] = []  # TODO: Get channels from somewhere

        for attempt in range(max_retries):
            try:
                # Check access to the chat
                try:
                    current_chat = await self.client.get_chat(chat_id)
                    logger.debug(f"[{self.name}] Already in chat {chat_id}")

                except Exception:
                    try:
                        current_chat = await self.client.get_chat(invite_link)
                        logger.debug(f"[{self.name}] Got chat info via invite link")

                    except Exception:
                        await self.client.join_chat(invite_link)
                        await asyncio.sleep(1)
                        current_chat = await self.client.get_chat(chat_id)
                        logger.info(f"[{self.name}] Joined chat {chat_id}")

                await asyncio.sleep(retry_delay)

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
                logger.warning(f"[{self.name}] Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.name}] Failed to send initial message after {max_retries} attempts")
                    raise

    async def get_chat_id_from_invite(self, invite_link: str) -> int:
        """
        Gets the chat ID from the invite link.

        Args:
            invite_link (str): The invite link of the chat.

        Returns:
            int: The ID of the chat.

        Raises:
            ValueError: If could not find chat for the invite link.
        """
        try:
            # Join the chat or get information if already a participant
            joined_chat = await self.client.join_chat(invite_link)
            chat_id = joined_chat.id

            logger.info(f"Got chat ID {chat_id} from invite link {invite_link}")
            return chat_id

        except UserAlreadyParticipant:
            try:
                # If already in the group, try to get information via get_chat
                chat_result = await self.client.get_chat(chat_id=invite_link)

                if isinstance(chat_result, Chat):
                    chat_id = chat_result.id
                    logger.info(f"Got chat ID {chat_id} for existing participant")
                    return chat_id
                else:
                    raise ValueError("Received ChatPreview instead of Chat")

            except Exception as e:
                logger.error(f"Error getting chat ID for existing participant: {e}")
                # Try an alternative method

                try:
                    # Try to get the list of chats and find the needed one
                    dialogs = self.client.get_dialogs()
                    if not dialogs:
                        raise ValueError("Could not get dialogs")

                    async for dialog in dialogs:
                        if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                            try:
                                invite = await self.client.get_chat_invite_link(
                                    chat_id=dialog.chat.id,
                                    invite_link=invite_link,
                                )
                                if invite.invite_link == invite_link:
                                    logger.info(f"Found chat ID {dialog.chat.id} in dialogs")
                                    return dialog.chat.id

                            except Exception:
                                continue

                except Exception as e:
                    logger.error(f"Error searching for chat in dialogs: {e}")
                    raise

                raise ValueError(f"Could not find chat for invite link {invite_link}")

        except Exception as e:
            logger.error(f"Error getting chat ID from invite link: {e}")
            raise

    async def start(self) -> None:
        """Starts the bot."""
        await self.client.start()
        logger.info(f"Bot {self.name} started")

        @self.client.on_message(filters.text & filters.group)  # type: ignore
        async def message_handler(message: "Message", channels: list["Channel"]) -> None:
            """
            Handles incoming messages.

            Args:
                message: The received message.
                channels: list of channels.
            """
            try:
                if not await self.should_process_message(message):
                    return

                await self.process_message(message=message, channels=channels)
                self.bot_manager.reset_chat_history(message.chat.id)

            except Exception as e:
                logger.error(f"Error in message handler: {e}")
