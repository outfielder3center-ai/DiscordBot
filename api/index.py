import io
import os
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from PIL import Image
import requests

app = FastAPI()

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

MANNAMI_PROMPT = """
あなたはイラスト指導教官の「万波先生」です。
見た目は浅黒い肌で少し強面ですが、生徒（ユーザー）がイラスト上達、特に可愛い女の子を描けるようになることを真剣に応援しています。

【あなたの役割】
ユーザーが送ってきたイラスト（スケッチ、線画、デッサンなど）を評価し、熱血アドバイスをしてください。

【口調・キャラクター設定】
- 少し荒っぽいが親切。「〜だぞ」「〜じゃねぇか」「おう！」といった野球部の熱血コーチのような口調。
- 技術的な視点（パーツのバランス、立体感、陰影、線の引き方など）から具体的に褒めたり、アドバイスをする。
- 要点をスカッと分かりやすくまとめること。
"""


def verify_discord_request(request_body: bytes, signature: str, timestamp: str):
    if not PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="PUBLIC_KEY is missing")
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    try:
        verify_key.verify(
            f"{timestamp}".encode() + request_body, bytes.fromhex(signature)
        )
    except BadSignatureError:
        raise HTTPException(
            status_code=401, detail="Invalid request signature"
        )


# バックグラウンドでGeminiに画像を解析させ、Discordのメッセージを更新する処理
def process_review_in_background(
    token: str, app_id: str, image_url: str, user_comment: str
):
    try:
        # 画像のダウンロード
        img_resp = requests.get(image_url)
        img = Image.open(io.BytesIO(img_resp.content))

        # Promptの作成
        prompt = f"ユーザーからのコメント: {user_comment if user_comment else '特になし'}\nこのイラストを指導してください！"

        # Gemini APIへリクエスト
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash", contents=[img, MANNAMI_PROMPT, prompt]
        )
        advice = response.text

    except Exception as e:
        advice = f"おう…すまねぇ、画像が上手く読み込めなかったみたいだ。もう一度送ってみてくれ！（エラー: {e}）"

    # Discordの初期レスポンス（「考え中…」）を書き換えるAPIを叩く
    patch_url = (
        f"https://discord.com/api/v10/webhooks/{app_id}/{token}/messages/@original"
    )
    requests.patch(patch_url, json={"content": advice})


@app.post("/")
async def interactions(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp:
        raise HTTPException(
            status_code=401, detail="Missing signature headers"
        )

    verify_discord_request(body, signature, timestamp)
    data = await request.json()

    # PING応答
    if data.get("type") == 1:
        return JSONResponse({"type": 1})

    # スラッシュコマンド処理
    if data.get("type") == 2:
        command_name = data["data"]["name"]
        interaction_token = data["token"]
        app_id = data["application_id"]

        if command_name == "review":
            options = {
                opt["name"]: opt["value"]
                for opt in data["data"].get("options", [])
            }
            resolved_attachments = (
                data["data"].get("resolved", {}).get("attachments", {})
            )

            attachment_id = options.get("image")
            image_info = resolved_attachments.get(attachment_id, {})
            image_url = image_info.get("url")
            user_comment = options.get("comment", "")

            # 重い処理（Gemini解析）はバックグラウンドタスクに回す
            background_tasks.add_task(
                process_review_in_background,
                interaction_token,
                app_id,
                image_url,
                user_comment,
            )

            # Discordには「考え中（Type 5）」を即座に返す（これで3秒タイムアウトを防ぐ）
            return JSONResponse({"type": 5})

    return JSONResponse(
        {"type": 4, "data": {"content": "未対応のコマンドだぞ！"}}
    )