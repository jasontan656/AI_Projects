import asyncio
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
import os
load_dotenv('.\\.env')
app = (
    ApplicationBuilder()
    .token(os.environ['TELEGRAM_BOT_TOKEN'])
    .connection_pool_size(65536)
    .get_updates_connection_pool_size(65536)
    .build()
)
async def run():
    await app.bot.get_me()
asyncio.run(run())
