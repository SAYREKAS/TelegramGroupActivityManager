"""Manager for working with Telegram chats.

This module provides functionality for:
- Parsing and validating invite links
- Getting chat IDs from invite links
- Normalizing chat IDs
- Joining bots to chats
"""

from typing import TYPE_CHECKING

from loguru import logger
from pyrogram.types import Chat
from pyrogram.errors import FloodWait, UserAlreadyParticipant

if TYPE_CHECKING:
    from pyrogram.client import Client


class ChatManagerError(Exception):
    """Base exception for ChatManager errors."""


class ChatAccessError(ChatManagerError):
    """Raised when there's an error accessing a chat."""


class ChatJoinError(ChatManagerError):
    """Raised when there's an error joining a chat."""


class ChatManager:
    """Manager for working with Telegram chats."""

    @staticmethod
    def parse_invite_link(invite_link: str) -> str:
        """
        Parses and normalizes an invite link.

        Args:
            invite_link: Invite link in any format.

        Returns:
            str: Normalized invite link.
        """
        invite_link = invite_link.strip()

        if invite_link.startswith(("https://t.me/", "http://t.me/")):
            return invite_link

        if invite_link.startswith("t.me/"):
            return f"https://{invite_link}"

        if invite_link.startswith("+"):
            return f"https://t.me/{invite_link}"

        return f"https://t.me/{invite_link}"

    @classmethod
    async def get_chat_id_from_invite(cls, client: "Client", invite_link: str, bot_name: str) -> int:
        """
        Gets the chat ID from an invite link.

        Args:
            client: The client instance.
            invite_link: The invite link to get chat ID from.
            bot_name: The name of the bot (for logging).

        Returns:
            int: The chat ID.

        Raises:
            ChatAccessError: If failed to get chat ID.
            FloodWait: If hit Telegram's flood limit.
        """
        try:
            logger.debug(f"Bot {bot_name} getting chat ID for link: {invite_link}")
            full_link = cls.parse_invite_link(invite_link)

            # Try to get chat directly first
            try:
                chat = await client.get_chat(full_link)
                if isinstance(chat, Chat):
                    chat_id = int(chat.id)
                    logger.info(f"Bot {bot_name} got chat ID {chat_id} directly")
                    return chat_id
            except Exception:
                pass

            # Try joining if direct access failed
            try:
                chat = await client.join_chat(full_link)
            except UserAlreadyParticipant:
                chat = await client.get_chat(full_link)

            if not isinstance(chat, Chat):
                raise ChatAccessError("Got ChatPreview instead of Chat")

            chat_id = int(chat.id)
            logger.info(f"Bot {bot_name} got chat ID {chat_id} from invite link")
            return chat_id

        except FloodWait as e:
            logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
            raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to get chat ID: {e}")
            raise ChatAccessError(f"Failed to get chat ID: {e}")

    @staticmethod
    def normalize_chat_id(chat_id: int) -> int:
        """
        Normalizes chat ID for Telegram API.

        Args:
            chat_id: The chat ID to normalize.

        Returns:
            int: Normalized chat ID.
        """
        str_id = str(chat_id)
        if str_id.startswith("-100"):
            return int(str_id[4:])
        if str_id.startswith("-"):
            return int(str_id[1:])
        return chat_id

    @classmethod
    async def join_chat(cls, client: "Client", chat_id: int, invite_link: str, bot_name: str) -> bool:
        """
        Joins a bot to a chat.

        Args:
            client: The client instance.
            chat_id: The ID of the chat to join.
            invite_link: The invite link of the chat.
            bot_name: The name of the bot.

        Returns:
            bool: True if joined successfully or already a member.

        Raises:
            ChatJoinError: If failed to join the chat.
            FloodWait: If hit Telegram's flood limit.
        """
        try:
            logger.debug(f"Bot {bot_name} trying to join chat {chat_id}")

            # Try joining via invite link
            try:
                await client.join_chat(invite_link)
                logger.info(f"Bot {bot_name} joined chat {chat_id} via invite link")
                return True
            except UserAlreadyParticipant:
                logger.info(f"Bot {bot_name} already in chat {chat_id}")
                return True
            except Exception as e:
                logger.debug(f"Failed to join via invite link: {e}")

            # Try accessing directly if invite link failed
            try:
                normalized_id = cls.normalize_chat_id(chat_id)
                await client.get_chat(normalized_id)
                logger.info(f"Bot {bot_name} already has access to chat {chat_id}")
                return True
            except Exception as e:
                logger.debug(f"Failed to access chat directly: {e}")

            raise ChatJoinError(f"Bot {bot_name} could not join chat {chat_id}")

        except FloodWait as e:
            logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
            raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to join chat: {e}")
            raise ChatJoinError(f"Failed to join chat: {e}")
