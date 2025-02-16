"""
Module for managing the chat bot, including interaction with OpenAI API
and message history management.
"""

from typing import Iterable

from loguru import logger
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

from project_config import settings


class ChatBot:
    """Class for managing the chat bot."""

    def __init__(self) -> None:
        """Initializes the chat bot with the API key."""
        self.client = OpenAI(api_key=settings.chat_bot.OPEN_API_KEY)
        self.message_history: dict[int, list[str]] = {}

    def _get_response(self, messages: Iterable[ChatCompletionMessageParam]) -> str:
        """Gets a response from the LLM."""
        try:
            logger.debug(f"Sending messages to LLM: {messages}")

            response = self.client.chat.completions.create(
                model=settings.chat_bot.MODEL,
                messages=messages,
                temperature=settings.chat_bot.TEMPERATURE,
            )
            return str(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error getting response from LLM: {e}")
            raise

    def add_to_history(self, chat_id: int, message: str, is_user: bool = True) -> None:
        """Adds a message to the history."""
        if chat_id not in self.message_history:
            self.message_history[chat_id] = []

        prefix = "User" if is_user else "Assistant"
        self.message_history[chat_id].append(f"{prefix}: {message}")

    def generate_response(
        self,
        chat_id: int,
        prompt: str,
        message: str | None = None,
        is_reply: bool = False,
        reply_text: str | None = None,
    ) -> str:
        """Generates a response based on the prompt and message history."""
        try:
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=f"""
                    <role>
                    You are a participant in a group chat. 
                    </role>
                    
                    <context>
                    The context of the group (for understanding the topic):
                    {prompt}
                    </context>
                    
                    <rules>
                    Important communication rules:
                    {settings.chat_bot.GENERATE_RESPONSE_RULES}
                    </rules>
                    """,
                )
            ]

            chat_history = self.message_history.get(chat_id, [])
            for msg in chat_history:
                if msg.startswith("Assistant: "):
                    messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=msg[11:]))
                else:
                    messages.append(ChatCompletionUserMessageParam(role="user", content=msg))

            if is_reply and reply_text:
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=reply_text))
            if message:
                messages.append(ChatCompletionUserMessageParam(role="user", content=message))

            response = self._get_response(messages)
            self.add_to_history(chat_id, response, is_user=False)
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ""

    def generate_initial_message(self, prompt: str) -> str:
        """Generates the first message for initiating the conversation."""
        messages = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=f"""
                <role>
                You are a regular participant in a group chat. 
                </role>
                
                <context>
                The context of the group (for understanding the topic):
                {prompt}
                </context>

                <rules>
                Important rules:
                {settings.chat_bot.GENERATE_INITIAL_MESSAGE_RULES}
                </rules>
                """,
            )
        ]

        try:
            response = self._get_response(messages)
            self.add_to_history(chat_id=0, message=response, is_user=False)
            return response

        except Exception as e:
            logger.error(f"Error generating initial message: {e}")
            return ""
