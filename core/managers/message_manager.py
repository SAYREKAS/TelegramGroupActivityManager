"""Message and flood control manager.

This module is responsible for:
- Managing message history in chats.
- Checking the ability of bots to respond to messages.
- Controlling flood limits between messages.
"""

from time import time

from project_config import settings


class MessageManager:
    """Manager for message and flood control"""

    _last_message_authors: dict[int, set[int]] = {}
    _last_message_time: dict[int, float] = {}
    _flood_limit: float = settings.bot_manager.FLOOD_LIMIT

    @classmethod
    def can_bot_reply(cls, chat_id: int, bot_index: int) -> bool:
        """Checks if a bot can reply in a given chat"""
        authors = cls._last_message_authors.setdefault(chat_id, set())
        return bot_index not in authors

    @classmethod
    def mark_bot_replied(cls, chat_id: int, bot_index: int) -> None:
        """Marks that a bot has replied in a chat"""
        authors = cls._last_message_authors.setdefault(chat_id, set())
        authors.add(bot_index)

    @classmethod
    def reset_chat_history(cls, chat_id: int, total_bots: int) -> None:
        """Resets the message history of a chat"""
        if len(cls._last_message_authors.get(chat_id, set())) >= total_bots - 1:
            cls._last_message_authors[chat_id] = set()

    @classmethod
    def can_send_message(cls, chat_id: int) -> bool:
        """Checks flood limits"""
        current_time = time()
        last_time = cls._last_message_time.get(chat_id, 0)

        if current_time - last_time < cls._flood_limit:
            return False

        cls._last_message_time[chat_id] = current_time
        return True
