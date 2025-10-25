import os
import requests
from dotenv import load_dotenv
load_dotenv('.\\.env')
token=os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('BOT_TOKEN')
print('token',token[:8]+'...')
try:
    resp=requests.get(f'https://api.telegram.org/bot{token}/getMe',timeout=10)
    print('status',resp.status_code)
    print(resp.text)
except Exception as e:
    import traceback;traceback.print_exc()
