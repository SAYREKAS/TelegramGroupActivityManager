"""Module for project settings."""

import os.path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.project_types import ChatBotModel


class ChatBotConfig(BaseModel):
    """Configuration for ChatBot."""

    OPEN_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for accessing LLM",
    )
    MODEL: ChatBotModel = Field(
        default="gpt-4o-mini",
        description="Model for text generation",
    )
    TEMPERATURE: float = Field(
        ge=0.0,
        le=1.0,
        default=0.7,
        description="Temperature for generation",
    )
    GENERATE_INITIAL_MESSAGE_RULES: str = Field(
        default="""
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
    4. Write as a regular user who wants to share an opinion or discuss something specific.
    """,
        description="Rules for generating initial messages",
    )
    GENERATE_RESPONSE_RULES: str = Field(
        default="""
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
       - Open to discussion.
       """,
        description="Rules for generating responses",
    )
    TEST_MODE: bool = Field(
        default=False,
        description="Test mode",
    )


class BotManagerConfig(BaseModel):
    """Configuration for bot manager."""

    FLOOD_LIMIT: float = Field(
        default=30.0,
        ge=0.0,
        description="Time limit between messages to prevent flooding",
    )

    MIN_BOTS_TO_RESET: int = Field(
        default=2,
        ge=1,
        description="Minimum number of bots that should reply before resetting chat history.",
    )


class TypingSimulatorConfig(BaseModel):
    """Configuration for typing simulation."""

    TYPING_SPEED: float = Field(
        default=0.1,
        ge=0.0,
        description="Typing speed in seconds per character",
    )
    MAX_TYPING_TIME: float = Field(
        default=60.0,
        ge=0.0,
        description="Maximum time limit for typing simulation",
    )


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="APP__",
        env_nested_delimiter="__",
    )

    chat_bot: ChatBotConfig = ChatBotConfig()
    bot_manager: BotManagerConfig = BotManagerConfig()
    typing_simulator: TypingSimulatorConfig = TypingSimulatorConfig()


settings = Settings()
