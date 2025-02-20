"""
Module for managing the chat bot, including interaction with OpenAI API
and message history management.
"""

from typing import Iterable

from loguru import logger
from openai import OpenAI, OpenAIError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

from project_config import settings


class ChatBotError(Exception):
    """Base exception for ChatBot errors."""


class LLMConnectionError(ChatBotError):
    """Raised when there's an error connecting to the LLM service."""


class MessageGenerationError(ChatBotError):
    """Raised when there's an error generating a message."""


class ChatBot:
    """Class for managing the chat bot."""

    def __init__(self) -> None:
        """Initializes the chat bot with the API key."""
        try:
            self.client = OpenAI(api_key=settings.chat_bot.OPEN_API_KEY)
            self.message_history: dict[int, list[str]] = {}

        except Exception as e:
            logger.error(f"Failed to initialize ChatBot: {e}")
            raise ChatBotError(f"ChatBot initialization failed: {e}") from e

    @staticmethod
    def _format_system_prompt(context: str, rules: str) -> str:
        """
        Formats the system prompt with context and rules.

        Args:
            context: The context for the conversation.
            rules: The rules for message generation.

        Returns:
            str: Formatted system prompt.
        """
        return f"""
        <role>
        You are a regular participant in a group chat. 
        </role>

        <context>
        The context of the group (for understanding the topic):
        {context}
        </context>

        <rules>
        Important rules:
        {rules}
        </rules>
        """

    def _get_response(self, messages: Iterable[ChatCompletionMessageParam]) -> str:
        """
        Gets a response from the LLM.

        Args:
            messages: The messages to send to the LLM.

        Returns:
            str: The generated response.

        Raises:
            LLMConnectionError: If there's an error connecting to the LLM.
        """
        try:
            logger.debug(f"Sending messages to LLM: {messages}")

            response = self.client.chat.completions.create(
                model=settings.chat_bot.MODEL,
                messages=messages,
                temperature=settings.chat_bot.TEMPERATURE,
            )

            if not response.choices:
                raise LLMConnectionError("No response choices received from LLM")

            return str(response.choices[0].message.content)

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMConnectionError(f"Failed to get response from OpenAI: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error getting response from LLM: {e}")
            raise LLMConnectionError(f"Unexpected error: {e}") from e

    def add_to_history(self, chat_id: int, message: str, is_user: bool = True) -> None:
        """
        Adds a message to the history.

        Args:
            chat_id: The ID of the chat.
            message: The message to add.
            is_user: Whether the message is from a user.
        """
        if not message:
            logger.warning("Attempted to add empty message to history")
            return

        if chat_id not in self.message_history:
            self.message_history[chat_id] = []

        prefix = "User" if is_user else "Assistant"
        self.message_history[chat_id].append(f"{prefix}: {message}")
        logger.debug(f"Added message to history for chat {chat_id}: {prefix}: {message[:50]}...")

    def _prepare_messages(
        self,
        chat_id: int,
        prompt: str,
        message: str | None = None,
        is_reply: bool = False,
        reply_text: str | None = None,
    ) -> list[ChatCompletionMessageParam]:
        """
        Prepares messages for the LLM.

        Args:
            chat_id: The ID of the chat.
            prompt: The context prompt.
            message: The current message.
            is_reply: Whether this is a reply.
            reply_text: The text being replied to.

        Returns:
            list[ChatCompletionMessageParam]: Prepared messages.
        """
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=self._format_system_prompt(
                    context=prompt,
                    rules=settings.chat_bot.GENERATE_RESPONSE_RULES,
                ),
            )
        ]

        # Add chat history
        chat_history = self.message_history.get(chat_id, [])
        for msg in chat_history:
            if msg.startswith("Assistant: "):
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant",
                        content=msg[11:],
                    )
                )
            else:
                messages.append(
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=msg[6:],
                    )
                )

        # Add reply context if needed
        if is_reply and reply_text:
            messages.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=reply_text,
                )
            )

        # Add current message if exists
        if message:
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=message,
                )
            )

        return messages

    def generate_response(
        self,
        chat_id: int,
        prompt: str,
        message: str | None = None,
        is_reply: bool = False,
        reply_text: str | None = None,
    ) -> str:
        """
        Generates a response based on the prompt and message history.

        Args:
            chat_id: The ID of the chat.
            prompt: The context prompt.
            message: The current message.
            is_reply: Whether this is a reply.
            reply_text: The text being replied to.

        Returns:
            str: The generated response.

        Raises:
            MessageGenerationError: If there's an error generating the message.
        """
        if settings.chat_bot.TEST_MODE:
            return "Test response message in test mode"

        try:
            messages = self._prepare_messages(
                chat_id=chat_id,
                prompt=prompt,
                message=message,
                is_reply=is_reply,
                reply_text=reply_text,
            )

            response = self._get_response(messages)
            self.add_to_history(chat_id, response, is_user=False)
            return response

        except LLMConnectionError as e:
            raise MessageGenerationError(f"Failed to generate response: {e}")

        except Exception as e:
            logger.error(f"Unexpected error generating response: {e}")
            raise MessageGenerationError(f"Unexpected error: {e}") from e

    def generate_initial_message(self, prompt: str) -> str:
        """
        Generates the first message for initiating the conversation.

        Args:
            prompt: The context prompt.

        Returns:
            str: The generated initial message.

        Raises:
            MessageGenerationError: If there's an error generating the message.
        """
        if settings.chat_bot.TEST_MODE:
            return "Test initial message in test mode"

        try:
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=self._format_system_prompt(
                        context=prompt,
                        rules=settings.chat_bot.GENERATE_INITIAL_MESSAGE_RULES,
                    ),
                )
            ]

            response = self._get_response(messages)
            self.add_to_history(chat_id=0, message=response, is_user=False)
            return response

        except LLMConnectionError as e:
            raise MessageGenerationError(f"Failed to generate initial message: {e}")

        except Exception as e:
            logger.error(f"Unexpected error generating initial message: {e}")
            raise MessageGenerationError(f"Unexpected error: {e}") from e
