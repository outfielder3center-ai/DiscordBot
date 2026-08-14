import io
import os
import random
from datetime import date
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from PIL import Image
import requests

from db import get_user, add_xp_and_update_advice, get_all_users

app = FastAPI()

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# リマインドを送るDiscordチャンネルのID（環境変数または直書き）
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

MANNAMI_PROMPT = """
あなたはイラスト指導教官の「万波先生」です。
見た目は少し強面ですが、生徒のイラスト上達を熱血サポートします。

【口調・設定】
- 野球部の熱血コーチのような力強い口調（「〜だぞ」「〜じゃねぇか」「おう！」）。
- 生徒の頑張りをしっかり認め、技術的アドバイスを熱く伝えること。
"""

# 千種みのり先生（早乙女志乃）の作例URL候補リスト
SHINO_WORKS = [
    "https://pixiv-waengallery.com/catalog_goods/53025/",
    "https://union-creative.jp/goods/detail/?id=987"
]

def send_discord_channel_message(channel_id: str, content: str):
    """指定したDiscordチャンネルにBotからメッセージを送信"""
    if not channel_id or not DISCORD_BOT_TOKEN:
        return
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, json={"content": content}, headers=headers)

@app.get("/api/cron")
async def handle_cron(type: str = "morning"):
    """Vercel Cron から呼び出される定期実行エンドポイント"""
    users = get_all_users()
    today_str = date.today().isoformat()

    for user in users:
        user_id = user["user_id"]
        last_advice = user["last_advice"]
        last_review_date = user["last_review_date"]

        if type == "morning":
            # 8:00 課題出し
            ref_url = random.choice(SHINO_WORKS)
            msg = f"🌅 **【万波先生の朝の熱血お題出し！】** <@{user_id}>\n"
            msg += "おう！朝だぞ！今日のイラスト練習の準備はできているか！？\n\n"
            if last_advice:
                msg += f"💡 **前回の指導のおさらい:**\n「{last_advice}」\n\n"
            msg += f"🎨 **本日の模写課題（千種みのり先生 / 早乙女志乃）：**\n{ref_url}\n"
            msg += "この素晴らしい作例の『表情』や『線のメリハリ』を意識して描いてみろ！待ってるぞ！"
            
            send_discord_channel_message(DISCORD_CHANNEL_ID, msg)

        elif type == "evening":
            # 20:00 催促（今日まだ添削されてない場合のみ）
            if last_review_date != today_str:
                msg = f"🌙 **【万波先生の夜の確認だ！】** <@{user_id}>\n"
                msg += "おいおい！今日の添削指導がまだ入ってねぇぞ！\n"
                msg += "10分だけの雑描きでも構わねぇ！`/review` で今日の成果を見せてみろ！待ってるぞ！"
                
                send_discord_channel_message(DISCORD_CHANNEL_ID, msg)

    return JSONResponse({"status": "ok", "type": type})

# --- (既存の verify_discord_request, process_review_in_background, @app.post("/") はそのまま維持) ---