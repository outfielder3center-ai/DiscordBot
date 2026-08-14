import os
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("DISCORD_APPLICATION_ID")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

token_header = f"Bot {BOT_TOKEN}" if BOT_TOKEN and not BOT_TOKEN.startswith("Bot ") else BOT_TOKEN

url = f"https://discord.com/api/v10/applications/{APP_ID}/commands"

headers = {
    "Authorization": token_header,
    "Content-Type": "application/json",
}

payload = {
    "name": "review",
    "description": "万波先生にイラストを添削してもらうぞ！",
    "options": [
        {
            "type": 11,  # Attachment
            "name": "image",
            "description": "添削してほしいイラスト画像",
            "required": True,
        },
        {
            "type": 3,  # String
            "name": "comment",
            "description": "先生への一言や悩んでいるポイント（任意）",
            "required": False,
        },
        {
            "type": 5,  # Boolean (True/False)
            "name": "is_fix",
            "description": "前回の指摘事項を修正した絵ならTrueを選ぼう！",
            "required": False,
        },
    ],
}

response = requests.post(url, json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.json())