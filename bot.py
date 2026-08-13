import io
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from google import genai
from PIL import Image

# .envファイルから環境変数を読み込む
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIクライアントの初期化
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Discord Botの準備（メッセージ読み取り権限を有効化）
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# 万波先生のキャラクター定義（プロンプト）
MANNAMI_PROMPT = """
あなたはイラスト指導教官の「万波先生」です。
見た目は浅黒い肌で少し見た目は強面ですが、生徒（ユーザー）がイラスト上達、特に可愛い女の子を描けるようになることを真剣に応援しています。

【あなたの役割】
ユーザーが送ってきたイラスト（スケッチ、線画、デッサンなど）を評価し、アドバイスしてください。

【口調・キャラクター設定】
- 少し荒っぽいが親切。「〜だぞ」「〜じゃねぇか」「おう！」といった野球部の熱血コーチのような口調。
- 技術的な視点（パーツのバランス、黄金比、立体感、陰影、線の引き方など）から具体的に褒めたり、アドバイスをする。
- 1回の返信は短くスカッと要点をまとめる（長文になりすぎないこと）。

送られた画像を見て、先生としてコメントしてください。
"""


@bot.event
async def on_ready():
    print(f"万波先生（{bot.user}）が着任しました！監視を開始します。")


@bot.event
async def on_message(message):
    # Bot自身の発言は無視
    if message.author == bot.user:
        return

    # メッセージに画像（添付ファイル）が含まれているか確認
    if message.attachments:
        for attachment in message.attachments:
            # 画像ファイルの場合のみ処理
            if any(
                attachment.filename.lower().endswith(ext)
                for ext in ["png", "jpg", "jpeg", "webp"]
            ):
                # 万波先生が処理中であることを示す思考中ステータス
                async with message.channel.typing():
                    try:
                        # 画像データを取得してPIL Imageに変換
                        image_bytes = await attachment.read()
                        image = Image.open(io.BytesIO(image_bytes))

                        # 利用可能なモデル名を順番に試すリスト
                        candidate_models = [
                            "gemini-3.6-flash",
                            "gemini-3.5-flash",
                            "gemini-3.5-flash-lite",
                            "gemini-3.1-flash-lite",
                            "gemini-3-flash-preview",
                        ]

                        response = None
                        last_error = None

                        for model_name in candidate_models:
                            try:
                                response = ai_client.models.generate_content(
                                    model=model_name,
                                    contents=[image, MANNAMI_PROMPT],
                                )
                                if response:
                                    break
                            except Exception as e:
                                last_error = e
                                continue

                        if response:
                            # 成功したら万波先生のコメントを返信
                            await message.reply(response.text)
                        else:
                            raise last_error

                    except Exception as e:
                        await message.reply(
                            f"おいおい、画像読み込みでエラーが出ちまったぞ…！（エラー: {e}）"
                        )
                return

    # コマンドの処理（将来的に機能を追加する場合用）
    await bot.process_commands(message)


# Botの起動
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)