"""Main module for running bots"""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from pyrogram import idle  # type: ignore

from core.bot import Bot
from core.managers.bot_manager import BotManager
from core.managers.chat_manager import ChatManager
from core.managers.subscription_manager import SubscriptionManager

if TYPE_CHECKING:
    from core.schemas import BotCollection, ChannelCollection
    from core.project_types import BotProtocol, ChatConfig


class TelegramActivityManager:
    """Class for managing Telegram bot activity."""

    def __init__(self, bots_data: "BotCollection", channels_data: "ChannelCollection") -> None:
        """
        Initializes the TelegramActivityManager.

        Args:
            bots_data: Collection of bot data.
            channels_data: Collection of channel data.
        """

        self.telegram_bots = bots_data.bots
        self.telegram_channels = channels_data.channels
        SubscriptionManager.set_channels(self.telegram_channels)

    @staticmethod
    def log_info_block(text: str) -> None:
        """Log info block."""

        logger.info("=" * 50)
        logger.info(text.upper())
        logger.info("=" * 50)

    async def _create_and_start_bots(self) -> list[Bot]:
        """
        Creates and starts all bots.

        Returns:
            list[Bot]: List of created and started bots.
        """

        self.log_info_block("STARTING BOT CREATION AND INITIALIZATION")

        # Load cache
        SubscriptionManager.load_cache()

        # Create all bots
        created_bots: list[Bot] = []
        for bot_data in self.telegram_bots:
            try:
                bot = Bot(name=f"BOT_{bot_data.phone}", bot_data=bot_data)
                created_bots.append(bot)

            except Exception as ex:
                logger.error(f"Failed to create BOT_{bot_data.phone}: {ex}")

        if not created_bots:
            raise ValueError("No bots were created")

        # Start all bots
        for bot in created_bots:
            await bot.start()

        logger.success("All bots started successfully")
        logger.info(f"Total bots registered: {len(BotManager.get_bots())}")
        return created_bots

    @staticmethod
    async def _initialize_bot_manager() -> "BotProtocol":
        """
        Initializes the bot manager and selects the main bot.

        Returns:
            BotProtocol: The main bot.
        """

        try:
            # Initialize BotManager and select the main bot
            BotManager.initialize()
            main_bot = BotManager.get_main_bot()

            if not main_bot:
                raise ValueError("Failed to select main bot")

            logger.info(f"Main bot selected: {main_bot.name}")
            return main_bot

        except Exception as ex:
            logger.error(f"Failed to initialize bot manager: {ex}")
            raise

    async def _initialize_chats(self, main_bot: "BotProtocol") -> None:
        """
        Initializes dialogs in all groups.

        Args:
            main_bot: The main bot.
        """

        for channel in self.telegram_channels:
            invite_link = channel.invite_link
            try:
                # Get chat ID from invite link
                try:
                    chat_id = await ChatManager.get_chat_id_from_invite(
                        client=main_bot.client, invite_link=invite_link, bot_name=main_bot.name
                    )
                    logger.info(f"Successfully got chat ID: {chat_id} for {invite_link}")

                except Exception as ex:
                    logger.error(f"Failed to get chat ID for {invite_link}: {ex}")
                    continue

                # Give time between attempts to access the group
                await asyncio.sleep(2)

                await main_bot.send_initial_message(chat_id=chat_id, invite_link=invite_link)

                # Give time for other bots to process the message
                await asyncio.sleep(5)

            except Exception as ex:
                logger.error(f"Failed to initialize chat with invite link {invite_link}: {ex}")

    async def _subscribe_bots_to_chats(self, all_bots: list[Bot]) -> None:
        """
        Performs the subscription process for all bots to all groups.

        Args:
            all_bots: List of all bots.
        """

        self.log_info_block("STARTING BOT SUBSCRIPTION PROCESS")

        # Subscribe all bots to all groups
        chat_configs: list["ChatConfig"] = [channel.to_chat_config() for channel in self.telegram_channels]
        logger.info("Starting bot subscription process...")
        await SubscriptionManager.subscribe_all_bots_to_chats(all_bots, chat_configs)
        logger.success("Bot subscription process completed")

    async def _start_main_script(self, all_bots: list[Bot], main_bot: "BotProtocol") -> None:
        """
        Starts the main script.

        Args:
            all_bots: List of all bots.
            main_bot: The main bot.
        """

        self.log_info_block("STARTING MAIN SCRIPT")

        # Give time for full initialization
        await asyncio.sleep(3)

        # Initialize dialog in each channel
        for channel in self.telegram_channels:  # Use channel objects
            try:
                logger.info(f"Initializing dialog in chat {channel.invite_link}")

                # Send initial message
                chat_id = await ChatManager.get_chat_id_from_invite(
                    client=main_bot.client, invite_link=channel.invite_link, bot_name=main_bot.name
                )
                await main_bot.send_initial_message(chat_id=chat_id, invite_link=channel.invite_link)
                logger.success(f"Successfully initialized dialog in chat {channel.invite_link}")

            except Exception as ex:
                logger.error(f"Error processing channel {channel.invite_link}: {ex}")

        # Keep bots active
        try:
            await idle()
        finally:
            self.log_info_block("SHUTTING DOWN")
            for bot in all_bots:
                await bot.client.stop()

    async def _run_main_process(self) -> None:
        """Runs the main process of the program."""

        try:
            created_bots = await self._create_and_start_bots()
            main_bot = await self._initialize_bot_manager()
            await self._initialize_chats(main_bot=main_bot)
            await self._subscribe_bots_to_chats(all_bots=created_bots)
            await self._start_main_script(all_bots=created_bots, main_bot=main_bot)

        except Exception as ex:
            logger.error(f"Error in main process: {ex}")
            raise

    def run(self) -> None:
        """Runs the main program."""

        try:
            asyncio.run(self._run_main_process())

        except KeyboardInterrupt:
            logger.info("Shutting down...")

        except Exception as e:
            logger.error(f"Fatal error: {e}")

        finally:
            logger.info("Stopped")
