import os
from google import genai

GEMINI_API_KEY = "AQ.Ab8RN6IFlozzLdQH79UFQN9yTJgFESPHa4-Ey0S0fx01vdC9NQ"
client = genai.Client(api_key=GEMINI_API_KEY)

print("=== 利用可能なモデル一覧 ===")
# 利用可能な全モデルを検索して表示
for model in client.models.list():
    # 画像生成（generateImages）やコンテンツ生成（generateContent）などの対応機能をチェック
    methods = getattr(model, 'supported_generation_methods', [])
    print(f"モデル名: {model.name}")
    print(f"  └ 対応機能: {methods}\n")