import os
import asyncio
import httpx
from dotenv import load_dotenv
load_dotenv('.\\.env')
token=os.environ['TELEGRAM_BOT_TOKEN']
async def main():
    async with httpx.AsyncClient(http2=True, timeout=10) as client:
        resp=await client.get(f'https://api.telegram.org/bot{token}/getMe')
        print(resp.status_code, resp.text[:200])
asyncio.run(main())
