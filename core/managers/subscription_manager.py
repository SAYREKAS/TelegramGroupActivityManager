"""Manager for handling bot subscriptions to groups"""

import asyncio
import json
import os
from typing import TYPE_CHECKING, Sequence, Any, ClassVar

from loguru import logger
from pyrogram.errors import FloodWait

from core.managers.chat_manager import ChatManager
from core.schemas import Channel

if TYPE_CHECKING:
    from pyrogram.client import Client
    from core.project_types import BotProtocol, ChatConfig


class SubscriptionManager:
    """Manager for handling bot subscriptions to groups"""

    _subscribed_bots: ClassVar[dict[int, set[int]]] = {}
    _cache_file: ClassVar[str] = "chat_ids_cache.json"
    _channels: ClassVar[list["Channel"]] = []
    chat_ids: ClassVar[dict[str, int]] = {}

    @classmethod
    async def get_chat_id_from_invite(cls, client: "Client", invite_link: str, bot_name: str = "Unknown") -> int | None:
        """Gets the chat ID from an invite link"""
        try:
            # Check cache
            if invite_link in cls.chat_ids:
                return cls.chat_ids[invite_link]

            # Get chat_id
            chat_id = await ChatManager.get_chat_id_from_invite(client, invite_link, bot_name)
            if chat_id:
                cls.chat_ids[invite_link] = chat_id
                cls.save_cache()
                logger.success(f"Bot {bot_name} cached chat ID {chat_id} for {invite_link}")
                return chat_id

            return None

        except FloodWait as e:
            logger.warning(f"Bot {bot_name} got FloodWait in get_chat_id: {e.value} seconds")
            raise

        except Exception as e:
            logger.error(f"Bot {bot_name} failed to get chat ID for {invite_link}: {e}")
            return None

    @classmethod
    async def check_subscription(cls, bot: "BotProtocol", chat_id: int) -> bool:
        """Checks if a bot is subscribed to a channel and updates the cache."""
        try:
            await bot.client.get_chat(chat_id)
            if chat_id not in cls._subscribed_bots:
                cls._subscribed_bots[chat_id] = set()

            api_id = bot.client.api_id
            if api_id is not None:  # Check that api_id is not None
                cls._subscribed_bots[chat_id].add(api_id)
                cls.save_cache()
                logger.info(f"Bot {bot.name} (API ID: {api_id}) already has access to chat {chat_id}")
                return True

            return False

        except FloodWait as e:
            logger.warning(f"Bot {bot.name} got FloodWait in check_subscription: {e.value} seconds")
            raise

        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid bot configuration for {bot.name}: {e}")
            return False

        except ConnectionError as e:
            logger.warning(f"Connection error for bot {bot.name}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error checking subscription for bot {bot.name}: {e}")
            return False

    @classmethod
    async def subscribe_bot(cls, bot: "BotProtocol", chat_id: int, invite_link: str) -> None:
        """Subscribes a single bot to a single channel"""
        while True:
            try:
                api_id = bot.client.api_id
                if api_id is None:  # Check that api_id is not None
                    logger.error(f"Bot {bot.name} has no API ID")
                    return

                # Check if already subscribed
                if chat_id in cls._subscribed_bots and api_id in cls._subscribed_bots[chat_id]:
                    logger.info(f"Bot {bot.name} (API ID: {api_id}) already subscribed to chat {chat_id}")
                    return

                # Check access
                if await cls.check_subscription(bot, chat_id):
                    return

                # Try to subscribe
                success = await ChatManager.join_chat(
                    client=bot.client, chat_id=chat_id, invite_link=invite_link, bot_name=bot.name
                )

                if success:
                    if chat_id not in cls._subscribed_bots:
                        cls._subscribed_bots[chat_id] = set()
                    cls._subscribed_bots[chat_id].add(api_id)
                    cls.save_cache()
                    logger.success(f"Bot {bot.name} (API ID: {api_id}) successfully subscribed to chat {chat_id}")
                    return

                logger.warning(f"Failed to subscribe {bot.name} to {chat_id}, retrying in 5s")
                await asyncio.sleep(5)

            except FloodWait as e:
                wait_time = e.value + 5
                logger.warning(f"Bot {bot.name} got FloodWait, sleeping for {wait_time} seconds")
                await asyncio.sleep(wait_time)
                logger.info(f"Bot {bot.name} woke up after FloodWait")

    @classmethod
    async def subscribe_all_bots_to_chats(cls, bots: Sequence["BotProtocol"], chats: Sequence["ChatConfig"]) -> None:
        """Subscribes all bots to all chats"""
        logger.info("Starting subscription process...")

        # First, get all chat_ids
        for chat in chats:
            if chat["invite_link"] not in cls.chat_ids:
                for bot in bots:
                    try:
                        if await cls.get_chat_id_from_invite(bot.client, chat["invite_link"], bot.name):
                            break

                    except FloodWait:
                        logger.warning(f"Bot {bot.name} got FloodWait, trying next bot")
                        continue

        # Create tasks for each bot and each chat
        tasks = []
        for bot in bots:
            for chat in chats:
                chat_id = cls.chat_ids.get(chat["invite_link"])
                if not chat_id:
                    logger.warning(f"No chat ID found for {chat['invite_link']}, skipping...")
                    continue

                task = asyncio.create_task(cls.subscribe_bot(bot, chat_id, chat["invite_link"]))
                tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    @classmethod
    def load_cache(cls) -> None:
        """Loads the cache of chat_ids and subscriptions"""
        try:
            if os.path.exists(cls._cache_file):
                with open(cls._cache_file, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    cls.chat_ids = {str(k): int(v) for k, v in data.get("chat_ids", {}).items()}
                    cls._subscribed_bots = {int(k): set(v) for k, v in data.get("subscribed_bots", {}).items()}

        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    @classmethod
    def save_cache(cls) -> None:
        """Saves the cache of chat_ids and subscriptions"""
        try:
            data = {
                "chat_ids": cls.chat_ids,
                "subscribed_bots": {str(k): list(v) for k, v in cls._subscribed_bots.items()},
            }
            with open(cls._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    @classmethod
    def initialize_channels(cls, channels: list["Channel"]) -> None:
        """
        Initializes the channels list.

        Args:
            channels: List of channels to initialize with.
        """
        cls._channels = channels

    @classmethod
    def get_channels(cls) -> list["Channel"]:
        """
        Gets the list of channels.

        Returns:
            list[Channel]: List of channels.
        """
        return cls._channels
