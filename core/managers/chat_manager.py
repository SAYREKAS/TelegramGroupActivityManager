"""Manager for working with Telegram chats.

This module provides functionality for:
- Parsing and validating invite links
- Joining bots to chats
- Getting information about chats
- Handling specific Telegram errors.
"""

from typing import TYPE_CHECKING

from loguru import logger
from pyrogram.errors import (
    UserAlreadyParticipant,
    FloodWait,
    InviteHashExpired,
    ChatAdminRequired,
    ChannelPrivate,
    PeerIdInvalid,
)

if TYPE_CHECKING:
    from pyrogram import Client  # type: ignore


class ChatManager:
    """Manager for working with chats"""

    @staticmethod
    def parse_invite_link(invite_link: str) -> str:
        """Parses an invite link and returns a clean hash.

        Args:
            invite_link: Invite link in any format

        Returns:
            str: Normalized invite link
        """
        invite_link = invite_link.strip()

        # If it's a full URL
        if invite_link.startswith(("https://t.me/", "http://t.me/")):
            return invite_link

        # If it's a shortened format
        if invite_link.startswith("t.me/"):
            return f"https://{invite_link}"

        # If it's just a hash
        if invite_link.startswith("+"):
            return f"https://t.me/{invite_link}"

        # By default, add the protocol
        return f"https://t.me/{invite_link}"

    @staticmethod
    async def get_chat_id_from_invite(client: "Client", invite_link: str, bot_name: str = "Unknown") -> int:
        """Gets the chat ID from an invite link"""
        try:
            full_link = ChatManager.parse_invite_link(invite_link)
            logger.debug(f"Bot {bot_name} getting chat ID for link: {full_link}")

            try:
                chat = await client.join_chat(full_link)
                logger.success(f"Bot {bot_name} got chat ID {chat.id} from invite link {invite_link}")
                return chat.id

            except UserAlreadyParticipant:
                chat = await client.get_chat(full_link)  # type: ignore
                logger.info(f"Bot {bot_name} already in chat, got ID {chat.id}")
                return chat.id

            except FloodWait as e:
                logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
                raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to get chat ID from invite link: {e}")
            raise

    @staticmethod
    async def join_chat(client: "Client", chat_id: int, invite_link: str, bot_name: str) -> bool:
        """Joins a bot to a chat.

        Args:
            client: Telegram client
            chat_id: Chat ID
            invite_link: Invite link
            bot_name: Bot name for logging.

        Returns:
            bool: True if successfully joined or already a participant
        """
        try:
            logger.debug(f"Trying to join chat with link: {invite_link}")

            try:
                await client.get_chat(chat_id)
                logger.info(f"Bot {bot_name} already in chat")
                return True
            except (PeerIdInvalid, ChannelPrivate):
                pass

            # Try to join via invite
            await client.join_chat(invite_link)
            logger.debug(f"Bot {bot_name} successfully joined chat {chat_id}")
            return True

        except FloodWait as e:
            logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
            raise

        except InviteHashExpired:
            logger.error(f"Invite link expired for chat {chat_id}")
            raise

        except UserAlreadyParticipant:
            logger.info(f"Bot {bot_name} already participant in chat {chat_id}")
            return True

        except ChatAdminRequired:
            logger.error(f"Bot {bot_name} needs admin rights to join chat {chat_id}")
            return False

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to access chat: {e}")
            return False
