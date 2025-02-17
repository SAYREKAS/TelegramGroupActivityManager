"""Data schemes"""

from TGConvertor import SessionManager  # type: ignore
from pydantic import BaseModel, field_validator

from core.project_types import ChatConfig


class TelegramBot(BaseModel):
    """Base model for a Telegram bot."""

    phone: int
    api_id: int
    api_hash: str
    session: str

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


class BotCollection(BaseModel):
    """Collection of Telegram bots."""

    bots: list[TelegramBot]


class Channel(BaseModel):
    """Model for a channel/group."""

    invite_link: str
    prompt: str

    def to_chat_config(self) -> ChatConfig:
        """Converts the model to ChatConfig.

        Returns:
            ChatConfig: The chat configuration.
        """
        return ChatConfig(invite_link=self.invite_link, prompt=self.prompt)


class ChannelCollection(BaseModel):
    """Collection of channels."""

    channels: list[Channel]
