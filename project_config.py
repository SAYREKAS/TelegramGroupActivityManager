"""Module for project settings."""

import os.path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatBotConfig(BaseModel):

    OPEN_API_KEY: str = Field(default="", description="OpenAI API key for accessing LLM")
    MODEL: (
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
    ) = Field(default="gpt-4o-mini", description="Model for text generation")
    TEMPERATURE: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature for generation")
    GENERATE_RESPONSE_RULES: str = """
    1. NEVER mention the provided group description
    2. Use the language that is commonly used by the participants in the chat.
    3. You can:
       - Disagree with other participants
       - Change the topic of conversation
       - Share your own experiences
       - Ask clarifying questions
       - Offer alternative views
    4. Avoid:
       - Simply agreeing with previous messages
       - Repeating the thoughts of other participants
       - A formal tone
       - Long messages. Try to write short comments, usually in 1-2 sentences.
    5. Be:
       - Natural in communication
       - Varied in responses
       - Specific in examples
       - Open to discussion."""
    GENERATE_INITIAL_MESSAGE_RULES: str = """
    1. NEVER mention the provided group description
    2. Create ONE short message that:
       - Breaks a specific, interesting topic
       - Provokes a discussion
       - Contains a personal opinion or experience
       - May be slightly controversial
    3. Avoid:
       - Greetings and introductions
       - General topics and questions
       - A formal tone
       - Direct questions "What do you think?"
    4. Write as a regular user who wants to share an opinion or discuss something specific."""


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="APP__",
        env_nested_delimiter="__",
    )

    chat_bot = ChatBotConfig()


settings = Settings()
