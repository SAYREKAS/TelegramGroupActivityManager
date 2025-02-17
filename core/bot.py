"""Клас для роботи з ботами"""

from typing import TYPE_CHECKING

from pyrogram.client import Client

from core.chat_bot import ChatBot
from core.managers.bot_manager import BotManager
from core.project_types import BotProtocol
from core.typing_simulator import TypingSimulator

if TYPE_CHECKING:
    from core.schemas import TelegramBot


class Bot(BotProtocol):
    """Клас для роботи з ботом"""

    def __init__(self, name: str, bot_data: "TelegramBot"):
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

        # Реєструємо бота в менеджері
        self.bot_manager = BotManager()
        self.bot_index = self.bot_manager.register_bot(self)
