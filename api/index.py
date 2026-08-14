import io
import os
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from PIL import Image
import requests

# SQLite連携モジュールの読み込み
from db import get_user, add_xp_and_update_advice

app = FastAPI()

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

MANNAMI_PROMPT = """
あなたはイラスト指導教官の「万波先生」です。
見た目は少し強面ですが、生徒のイラスト上達を熱血サポートします。

【口調・設定】
- 野球部の熱血コーチのような力強い口調（「〜だぞ」「〜じゃねぇか」「おう！」）。
- 生徒の頑張りをしっかり認め、技術的アドバイスを熱く伝えること。
"""

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