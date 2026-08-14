import os
from dotenv import load_dotenv
import requests

load_dotenv()

APP_ID = os.getenv("DISCORD_APPLICATION_ID")  # Developer PortalのApplication ID
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Bot Token

# 全サーバー共通で使えるコマンドを登録
url = f"https://discord.com/api/v10/applications/{APP_ID}/commands"

headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}

# /review コマンド（画像を添付させる）
payload = {
    "name": "review",
    "description": "万波先生にイラストを添削してもらうぞ！",
    "options": [
        {
            "type": 11,  # Attachment（ファイル添付）
            "name": "image",
            "description": "添削してほしいイラスト画像",
            "required": True,
        },
        {
            "type": 3,  # String（テキスト）
            "name": "comment",
            "description": "先生への一言や悩んでいるポイント（任意）",
            "required": False,
        },
    ],
}

response = requests.post(url, json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.json())