"""Data schemes"""

from typing import Self

from TGConvertor import SessionManager  # type: ignore
from pydantic import BaseModel, field_validator

from core.project_types import BotConfig, ChatConfig, BotConfigDict, ChatConfigDict


class TelegramBot(BaseModel):
    """Base model for a Telegram bot."""

    phone: str
    api_id: int
    api_hash: str
    session: str

    @classmethod
    def from_dict(cls, data: BotConfigDict) -> Self:
        """Creates an instance from a dictionary.

        Args:
            data: The dictionary containing bot configuration.

        Returns:
            Self: An instance of the TelegramBot class.
        """
        return cls(
            phone=str(data["phone"]),
            api_id=int(data["api_id"]),
            api_hash=str(data["api_hash"]),
            session=str(data["session"]),
        )

    @field_validator("session", mode="after")
    def convert_session_string(cls, v: str) -> str:
        """Converts the session from Telethon to Pyrogram format if needed.

        Args:
            v: The session string to convert.

        Returns:
            str: The converted session string.
        """
        if v.startswith("1") and v.endswith("="):
            session = SessionManager.from_telethon_string(v)
            return str(session.to_pyrogram_string())
        return v

    def to_bot_config(self) -> BotConfig:
        """Converts the model to BotConfig.

        Returns:
            BotConfig: The bot configuration.
        """
        return BotConfig(
            phone=self.phone,
            api_id=self.api_id,
            api_hash=self.api_hash,
            session=self.session,
        )


class BotCollection(BaseModel):
    """Collection of Telegram bots."""

    bots: list[TelegramBot]

    @classmethod
    def from_dicts(cls, data: list[BotConfigDict]) -> "BotCollection":
        """Creates a collection from a list of dictionaries.

        Args:
            data: The list of bot configuration dictionaries.

        Returns:
            BotCollection: An instance of the BotCollection class.
        """
        return cls(bots=[TelegramBot.from_dict(bot) for bot in data])


class Channel(BaseModel):
    """Model for a channel/group."""

    invite_link: str
    prompt: str

    @classmethod
    def from_dict(cls, data: ChatConfigDict) -> "Channel":
        """Creates an instance from a dictionary.

        Args:
            data: The dictionary containing channel configuration.

        Returns:
            Channel: An instance of the Channel class.
        """
        return cls(
            invite_link=str(data["invite_link"]),
            prompt=str(data["prompt"]),
        )

    def to_chat_config(self) -> ChatConfig:
        """Converts the model to ChatConfig.

        Returns:
            ChatConfig: The chat configuration.
        """
        return ChatConfig(invite_link=self.invite_link, prompt=self.prompt)


class ChannelCollection(BaseModel):
    """Collection of channels."""

    channels: list[Channel]

    @classmethod
    def from_dicts(cls, data: list[ChatConfigDict]) -> "ChannelCollection":
        """Creates a collection from a list of dictionaries.

        Args:
            data: The list of channel configuration dictionaries.

        Returns:
            ChannelCollection: An instance of the ChannelCollection class.
        """
        return cls(channels=[Channel.from_dict(channel) for channel in data])
