"""Simulator Text Boots Simulator"""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from pyrogram import enums
from pyrogram.errors import FloodWait, UserNotParticipant

from project_config import settings

if TYPE_CHECKING:
    from pyrogram.client import Client


class TypingSimulator:
    """Class to simulate text typing actions for bots."""

    @staticmethod
    async def calculate_typing_duration(text_length: int) -> float:
        """Calculates the time of typing based on its length.

        Args:
            text_length: The length of the text to be typed.
        Returns:
            float: The calculated typing duration.
        """
        return min(text_length * settings.TYPING_SPEED, settings.MAX_TYPING_TIME)

    async def simulate_typing(self, client: "Client", chat_id: int, text_length: int = 0) -> None:
        """Mimics a set of text based on its length.

        Args:
            client (Client): The Pyrogram client instance.
            chat_id (int): The ID of the chat where the message will be sent.
            text_length (int, optional): The length of the text to be typed. Defaults to 0.
        """
        try:
            typing_duration = await self.calculate_typing_duration(text_length)

            await client.send_chat_action(chat_id, enums.ChatAction.TYPING)

            if typing_duration > 0:
                await asyncio.sleep(typing_duration)

            await client.send_chat_action(chat_id, enums.ChatAction.CANCEL)

        except FloodWait as e:
            logger.warning(
                f"FloodWait error: {e.value} seconds. Please wait before sending more messages."
            )

        except UserNotParticipant as e:
            logger.error(f"User not a participant in chat {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in simulate_typing: {e}")
