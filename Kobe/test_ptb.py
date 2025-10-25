import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
load_dotenv('.\\.env')
token=os.environ['TELEGRAM_BOT_TOKEN']
bot=Bot(token)
async def main():
    me=await bot.get_me()
    print(me)
asyncio.run(main())
