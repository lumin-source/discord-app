import asyncio
import logging

TARGET_USER_ID = 1434053916479328286
TARGET_CHANNEL_ID = 1507588079563575316


def register(bot):
    @bot.event
    async def on_message(message):
        if message.author.id == TARGET_USER_ID and message.channel.id == TARGET_CHANNEL_ID:
            await asyncio.sleep(5)
            try:
                await message.delete()
                logging.info(
                    "Deleted honeypot message from %s (ID: %s): %s",
                    message.author,
                    message.author.id,
                    message.content or "<no text content>",
                )
            except Exception as exc:
                logging.warning("Failed to delete honeypot message: %s", exc)

        await bot.process_commands(message)
