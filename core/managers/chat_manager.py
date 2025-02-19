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

    @classmethod
    async def get_chat_id_from_invite(cls, client: "Client", invite_link: str, bot_name: str) -> int:
        """Gets the chat ID from an invite link."""
        try:
            logger.debug(f"Bot {bot_name} getting chat ID for link: {invite_link}")
            full_link = cls.parse_invite_link(invite_link)

            try:
                # Спочатку спробуємо отримати чат напряму
                try:
                    chat = await client.get_chat(full_link)
                    chat_id = int(chat.id)
                    logger.info(f"Bot {bot_name} got chat ID {chat_id} directly")
                    return chat_id
                except Exception:
                    pass

                # Якщо не вдалося, пробуємо приєднатися
                try:
                    chat = await client.join_chat(full_link)
                except UserAlreadyParticipant:
                    # Якщо вже учасник, отримуємо інформацію про чат
                    chat = await client.get_chat(full_link)
                
                if isinstance(chat.id, dict):
                    raise TypeError("Chat ID is a dictionary instead of an integer")
                    
                chat_id = int(chat.id)
                logger.info(f"Bot {bot_name} got chat ID {chat_id} from invite link")
                return chat_id

            except FloodWait as e:
                logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
                raise

            except (ValueError, TypeError) as e:
                logger.error(f"Bot {bot_name} received invalid chat ID format: {e}")
                raise TypeError(f"Invalid chat ID format: {e}")

            except Exception as e:
                logger.error(f"Bot {bot_name} failed to get chat ID from invite link: {e}")
                raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to get chat ID from invite link: {e}")
            raise

    @staticmethod
    def normalize_chat_id(chat_id: int) -> int:
        """Normalizes chat ID for Telegram API."""
        str_id = str(chat_id)
        if str_id.startswith("-100"):
            return int(str_id[4:])
        if str_id.startswith("-"):
            return int(str_id[1:])
        return chat_id

    @staticmethod
    async def join_chat(client: "Client", chat_id: int, invite_link: str, bot_name: str) -> bool:
        """Joins a bot to a chat."""
        try:
            logger.debug(f"Trying to join chat with link: {invite_link}")

            # Спочатку спробуємо через invite_link
            try:
                await client.join_chat(invite_link)
                logger.debug(f"Bot {bot_name} successfully joined chat via invite link")
                return True
            except UserAlreadyParticipant:
                logger.info(f"Bot {bot_name} already participant in chat {chat_id}")
                return True
            except Exception as e:
                logger.debug(f"Could not join via invite link: {e}")

            # Якщо не вдалося, спробуємо через chat_id
            try:
                normalized_id = ChatManager.normalize_chat_id(chat_id)
                await client.get_chat(normalized_id)
                logger.info(f"Bot {bot_name} already has access to chat {chat_id}")
                return True
            except Exception as e:
                logger.debug(f"Could not access chat directly: {e}")

            # Якщо обидва методи не спрацювали
            logger.error(f"Bot {bot_name} could not access chat {chat_id} via any method")
            return False

        except FloodWait as e:
            logger.warning(f"Bot {bot_name} got FloodWait for {e.value} seconds")
            raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to access chat: {e}")
            return False
