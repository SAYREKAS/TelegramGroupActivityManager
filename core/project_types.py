"""Data types for the project.

This module contains definitions of data types used in the project,
including protocols for bots and Telegram clients, as well as schemas
for bot and chat configurations.
"""

from typing import TYPE_CHECKING, Protocol, TypeAlias
from typing_extensions import TypedDict


if TYPE_CHECKING:
    from pyrogram.client import Client

ChatID: TypeAlias = int
BotIndex: TypeAlias = int
UserID: TypeAlias = int
LastMessageAuthors: TypeAlias = dict[ChatID, set[BotIndex]]
LastMessageTime: TypeAlias = dict[ChatID, float]


class BotProtocol(Protocol):
    """Protocol for a bot."""

    name: str
    client: "Client"
    bot_index: BotIndex
    flood_wait_until: float

    async def start(self) -> None:
        """Starts the bot."""

    async def send_initial_message(self, chat_id: int, invite_link: str) -> None:
        """Sends an initial message to the chat.

        Args:
            chat_id (int): The ID of the chat where the message will be sent.
            invite_link (str): The invite link for the chat.
        """


class ChatConfig(TypedDict):
    """Configuration for a chat."""

    invite_link: str
    prompt: str


class BotConfig(TypedDict):
    """Configuration for a bot."""

    phone: int
    api_id: int
    api_hash: str
    session: str


# Types for configuration
BotConfigDict = dict[str, str | int]
ChatConfigDict = dict[str, str]
