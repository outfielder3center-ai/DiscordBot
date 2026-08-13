import io
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from PIL import Image
import requests

app = FastAPI()

# 環境変数の読み込み
PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIクライアント
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# 万波先生のキャラクター定義
MANNAMI_PROMPT = """
あなたはイラスト指導教官の「万波先生」です。
見た目は浅黒い肌で少し見た目は強面ですが、生徒（ユーザー）がイラスト上達、特に可愛い女の子を描けるようになることを真剣に応援しています。

【あなたの役割】
ユーザーが送ってきたイラスト（スケッチ、線画、デッサンなど）を評価し、アドバイスしてください。

【口調・キャラクター設定】
- 少し荒っぽいが親切。「〜だぞ」「〜じゃねぇか」「おう！」といった野球部の熱血コーチのような口調。
- 技術的な視点（パーツのバランス、黄金比、立体感、陰影、線の引き方など）から具体的に褒めたり、アドバイスをする。
- 1回の返信は短くスカッと要点をまとめる（長文になりすぎないこと）。
"""


# Discordの署名検証関数
def verify_discord_request(request_body: bytes, signature: str, timestamp: str):
    if not PUBLIC_KEY:
        raise HTTPException(
            status_code=500, detail="PUBLIC_KEY is not configured"
        )

    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    try:
        verify_key.verify(
            f"{timestamp}".encode() + request_body, bytes.fromhex(signature)
        )
    except BadSignatureError:
        raise HTTPException(
            status_code=401, detail="Invalid request signature"
        )


@app.post("/")
async def interactions(request: Request):
    # 1. 署名の検証
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp:
        raise HTTPException(
            status_code=401, detail="Missing signature headers"
        )

    verify_discord_request(body, signature, timestamp)

    # 2. リクエスト解析
    data = await request.json()

    # Discordからの接続テスト（PING）に応答
    if data.get("type") == 1:
        return JSONResponse({"type": 1})

    # メッセージ（コンテキストメニューやスラッシュコマンド）などの処理拡張ポイント
    # ※今回は一番シンプルな「画像URLを受け取って返信する」ロジックのベースを作成
    return JSONResponse(
        {
            "type": 4,
            "data": {
                "content": "おう！万波だ！クラウド側もバッチリ起動してるぞ！"
            },
        }
    )