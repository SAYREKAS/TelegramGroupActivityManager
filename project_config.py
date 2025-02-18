"""Module for project settings."""

import os.path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.project_types import ChatBotModel


class ChatBotConfig(BaseModel):

    OPEN_API_KEY: str = Field(default="", description="OpenAI API key for accessing LLM")
    MODEL: ChatBotModel = Field(default="gpt-4o-mini", description="Model for text generation")
    TEMPERATURE: float = Field(ge=0.0, le=1.0, default=0.7, description="Temperature for generation")
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
    TEST_MODE: bool = Field(default=False, description="Test mode")


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

    FLOOD_LIMIT: float = Field(default=3.0, description="")
    TYPING_SPEED: float = Field(default=0.1, ge=0.0, description="Typing speed (seconds per character)")
    MAX_TYPING_TIME: float = Field(default=60.0, ge=0.0, description="Limits the maximum typing time")


settings = Settings()
