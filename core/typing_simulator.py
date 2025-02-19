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

    def __init__(self) -> None:
        """Initialize typing simulator."""
        self.typing_speed = settings.bot_behavior.TYPING_SPEED
        self.max_typing_time = settings.bot_behavior.MAX_TYPING_TIME

    @staticmethod
    async def calculate_typing_duration(text_length: int, typing_speed: float, max_time: float) -> float:
        """Calculates the time of typing based on its length."""
        return min(text_length * typing_speed, max_time)

    async def simulate_typing(self, client: "Client", chat_id: int, text_length: int = 0) -> None:
        """Mimics typing text based on its length."""
        try:
            typing_duration = await self.calculate_typing_duration(
                text_length=text_length,
                typing_speed=self.typing_speed,
                max_time=self.max_typing_time,
            )

            await client.send_chat_action(chat_id, enums.ChatAction.TYPING)

            if typing_duration > 0:
                await asyncio.sleep(typing_duration)

            await client.send_chat_action(chat_id, enums.ChatAction.CANCEL)

        except FloodWait as e:
            logger.warning(f"FloodWait error: {e.value} seconds")
            raise

        except UserNotParticipant:
            logger.error(f"Bot not a participant in chat {chat_id}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in simulate_typing: {e}")
            raise
