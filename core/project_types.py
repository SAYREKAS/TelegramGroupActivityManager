"""Data types for the project.

This module contains definitions of data types used in the project,
including protocols for bots and Telegram clients, as well as schemas
for bot and chat configurations.
"""

from typing import TYPE_CHECKING, Protocol, TypeAlias, Literal
from typing_extensions import TypedDict


if TYPE_CHECKING:
    from pyrogram.client import Client

ChatID: TypeAlias = int
BotIndex: TypeAlias = int
UserID: TypeAlias = int
LastMessageAuthors: TypeAlias = dict[ChatID, set[BotIndex]]
LastMessageTime: TypeAlias = dict[ChatID, float]

ChatBotModel: TypeAlias = (
    Literal[
        "o3-mini",
        "o3-mini-2025-01-31",
        "o1",
        "o1-2024-12-17",
        "o1-preview",
        "o1-preview-2024-09-12",
        "o1-mini",
        "o1-mini-2024-09-12",
        "gpt-4o",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o-audio-preview",
        "gpt-4o-audio-preview-2024-10-01",
        "gpt-4o-audio-preview-2024-12-17",
        "gpt-4o-mini-audio-preview",
        "gpt-4o-mini-audio-preview-2024-12-17",
        "chatgpt-4o-latest",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-0125-preview",
        "gpt-4-turbo-preview",
        "gpt-4-1106-preview",
        "gpt-4-vision-preview",
        "gpt-4",
        "gpt-4-0314",
        "gpt-4-0613",
        "gpt-4-32k",
        "gpt-4-32k-0314",
        "gpt-4-32k-0613",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-16k-0613",
    ]
    | str
)


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
