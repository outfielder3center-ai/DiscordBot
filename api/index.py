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
RAW_SHINO_URLS = """
https://www.pixiv.net/artworks/147425596
https://www.pixiv.net/artworks/146887834
https://www.pixiv.net/artworks/146606921
https://www.pixiv.net/artworks/146040140
https://www.pixiv.net/artworks/145694759
https://www.pixiv.net/artworks/144925800
https://www.pixiv.net/artworks/143782883
https://www.pixiv.net/artworks/143221828
https://www.pixiv.net/artworks/142928901
https://www.pixiv.net/artworks/142862776
https://www.pixiv.net/artworks/142651282
https://www.pixiv.net/artworks/140127980
https://www.pixiv.net/artworks/139845925
https://www.pixiv.net/artworks/139557180
https://www.pixiv.net/artworks/138903880
https://www.pixiv.net/artworks/137579331
https://www.pixiv.net/artworks/137517950
https://www.pixiv.net/artworks/137314991
https://www.pixiv.net/artworks/137051350
https://www.pixiv.net/artworks/135676579
https://www.pixiv.net/artworks/135132645
https://www.pixiv.net/artworks/133754864
https://www.pixiv.net/artworks/132951216
https://www.pixiv.net/artworks/132688849
https://www.pixiv.net/artworks/132149267
https://www.pixiv.net/artworks/131849988
https://www.pixiv.net/artworks/130834961
https://www.pixiv.net/artworks/130520379
https://www.pixiv.net/artworks/129548851
https://www.pixiv.net/artworks/129057876
https://www.pixiv.net/artworks/128558536
https://www.pixiv.net/artworks/128064233
https://www.pixiv.net/artworks/127586111
https://www.pixiv.net/artworks/125642720
https://www.pixiv.net/artworks/125243118
https://www.pixiv.net/artworks/125037689
https://www.pixiv.net/artworks/124622814
https://www.pixiv.net/artworks/124417500
https://www.pixiv.net/artworks/123990875
https://www.pixiv.net/artworks/123757994
https://www.pixiv.net/artworks/123544178
https://www.pixiv.net/artworks/122909027
https://www.pixiv.net/artworks/122703620
https://www.pixiv.net/artworks/122074873
https://www.pixiv.net/artworks/121640685
https://www.pixiv.net/artworks/121205696
https://www.pixiv.net/artworks/120772121
https://www.pixiv.net/artworks/120555969
https://www.pixiv.net/artworks/120150903
https://www.pixiv.net/artworks/119725498
https://www.pixiv.net/artworks/119517953
https://www.pixiv.net/artworks/118896432
https://www.pixiv.net/artworks/118490285
https://www.pixiv.net/artworks/118267355
https://www.pixiv.net/artworks/117863612
https://www.pixiv.net/artworks/117453366
https://www.pixiv.net/artworks/116204171
https://www.pixiv.net/artworks/115787849
https://www.pixiv.net/artworks/115192884
https://www.pixiv.net/artworks/114334415
https://www.pixiv.net/artworks/113948074
https://www.pixiv.net/artworks/113756746
https://www.pixiv.net/artworks/113378461
https://www.pixiv.net/artworks/112976284
https://www.pixiv.net/artworks/112929691
https://www.pixiv.net/artworks/112407096
https://www.pixiv.net/artworks/112215027
https://www.pixiv.net/artworks/112024722
https://www.pixiv.net/artworks/111441100
https://www.pixiv.net/artworks/111393433
https://www.pixiv.net/artworks/110821950
https://www.pixiv.net/artworks/110403409
https://www.pixiv.net/artworks/110002104
https://www.pixiv.net/artworks/109582609
https://www.pixiv.net/artworks/109252650
https://www.pixiv.net/artworks/109155377
https://www.pixiv.net/artworks/108750662
https://www.pixiv.net/artworks/108545614
https://www.pixiv.net/artworks/107942593
https://www.pixiv.net/artworks/107480637
https://www.pixiv.net/artworks/107050698
https://www.pixiv.net/artworks/106611446
https://www.pixiv.net/artworks/106391014
https://www.pixiv.net/artworks/105968949
https://www.pixiv.net/artworks/105553553
https://www.pixiv.net/artworks/105139624
https://www.pixiv.net/artworks/104938338
https://www.pixiv.net/artworks/104566925
https://www.pixiv.net/artworks/104167146
https://www.pixiv.net/artworks/103549508
https://www.pixiv.net/artworks/103170557
https://www.pixiv.net/artworks/102788387
https://www.pixiv.net/artworks/102388696
https://www.pixiv.net/artworks/102013515
https://www.pixiv.net/artworks/101660994
https://www.pixiv.net/artworks/101339949
https://www.pixiv.net/artworks/101016572
https://www.pixiv.net/artworks/100682272
https://www.pixiv.net/artworks/100328450
https://www.pixiv.net/artworks/99986860
https://www.pixiv.net/artworks/99653962
https://www.pixiv.net/artworks/99340665
https://www.pixiv.net/artworks/99028011
https://www.pixiv.net/artworks/98711823
https://www.pixiv.net/artworks/98388796
https://www.pixiv.net/artworks/98046364
https://www.pixiv.net/artworks/97872943
https://www.pixiv.net/artworks/97559815
https://www.pixiv.net/artworks/97402534
https://www.pixiv.net/artworks/96908377
https://www.pixiv.net/artworks/96416668
https://www.pixiv.net/artworks/95903087
https://www.pixiv.net/artworks/95589697
https://www.pixiv.net/artworks/95065014
https://www.pixiv.net/artworks/94605935
https://www.pixiv.net/artworks/94002091
https://www.pixiv.net/artworks/93847847
"""

# 改行で分割して、空行を除外したリストを作る
SHINO_WORKS = [url.strip() for url in RAW_SHINO_URLS.strip().splitlines() if url.strip()]

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

def verify_discord_request(request_body: bytes, signature: str, timestamp: str):
    if not PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="PUBLIC_KEY is missing")
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    try:
        verify_key.verify(f"{timestamp}".encode() + request_body, bytes.fromhex(signature))
    except BadSignatureError:
        raise HTTPException(status_code=401, detail="Invalid request signature")

def process_review_in_background(token: str, app_id: str, user_id: str, image_url: str, user_comment: str, is_fix: bool):
    try:
        # DBからユーザー状態を取得
        user_data = get_user(user_id)
        last_advice = user_data["last_advice"]

        img_resp = requests.get(image_url)
        img = Image.open(io.BytesIO(img_resp.content))

        # 修正版かどうかでプロンプトと獲得XPを変更
        earned_xp = 100
        prompt_context = f"ユーザーコメント: {user_comment if user_comment else '特になし'}\n"
        
        if is_fix and last_advice:
            earned_xp = 200  # 修正ボーナス！
            prompt_context += f"【重要】ユーザーは前回のあなたの指摘（前回の指摘内容:「{last_advice}」）を意識して描き直してくれました！前回の指摘が改善されているかを重点的に評価し、褒めてあげてください！"
        else:
            prompt_context += "このイラストを熱血指導してください！"

        # Gemini解析
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[img, MANNAMI_PROMPT, prompt_context]
        )
        advice_text = response.text

        # 要約したアドバイス（次回比較用）とXP更新
        # 今回のアドバイスから最初の200文字程度を記憶しておく
        short_advice = advice_text[:200].replace("\n", " ")
        db_result = add_xp_and_update_advice(user_id, earned_xp, short_advice)

        # レスポンスメッセージ作成
        xp_msg = f"\n\n--- \n🔥 **+{earned_xp} XP 獲得！** (現在の累計: {db_result['new_xp']} XP / Lv.{db_result['new_level']})"
        if is_fix:
            xp_msg = "\n✨ **【前回の修正ボーナス適用！】** ✨" + xp_msg
        if db_result["leveled_up"]:
            xp_msg += f"\n🎉 **LEVEL UP!!** Lv.{db_result['new_level']} に上がったぞ！その調子だ！"

        final_response = advice_text + xp_msg

    except Exception as e:
        final_response = f"おう…すまねぇ、処理中にエラーが起きちまった！（エラー: {e}）"

    patch_url = f"https://discord.com/api/v10/webhooks/{app_id}/{token}/messages/@original"
    requests.patch(patch_url, json={"content": final_response})

@app.post("/")
async def interactions(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")

    verify_discord_request(body, signature, timestamp)
    data = await request.json()

    if data.get("type") == 1:
        return JSONResponse({"type": 1})

    if data.get("type") == 2:
        command_name = data["data"]["name"]
        interaction_token = data["token"]
        app_id = data["application_id"]
        # 送信したユーザーのIDを取得
        user_id = data.get("member", {}).get("user", {}).get("id") or data.get("user", {}).get("id")

        if command_name == "review":
            options = {opt["name"]: opt["value"] for opt in data["data"].get("options", [])}
            resolved_attachments = data["data"].get("resolved", {}).get("attachments", {})

            attachment_id = options.get("image")
            image_info = resolved_attachments.get(attachment_id, {})
            image_url = image_info.get("url")
            user_comment = options.get("comment", "")
            is_fix = options.get("is_fix", False)

            background_tasks.add_task(
                process_review_in_background,
                interaction_token,
                app_id,
                user_id,
                image_url,
                user_comment,
                is_fix,
            )

            return JSONResponse({"type": 5})

    return JSONResponse({"type": 4, "data": {"content": "未対応のコマンドだぞ！"}})