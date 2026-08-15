import io
import json
import os
import random
import re
import time
from datetime import date
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from PIL import Image, ImageDraw
import requests
import asyncio

# DBモジュールから last_image 系の関数もインポートする想定
from db import (
    get_user,
    add_xp_and_update_advice,
    get_all_users,
    get_user_last_image,      # ← 追加: 前回画像URL取得
    update_user_last_image,   # ← 追加: 画像URL更新
)

app = FastAPI()

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_PRIORITY_LIST = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]

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

SHINO_WORKS = [url.strip() for url in RAW_SHINO_URLS.strip().splitlines() if url.strip()]


def generate_with_fallback(contents, config=None):
    """優先リスト順にモデルを呼び出すフォールバック処理"""
    last_exception = None
    for model_name in MODEL_PRIORITY_LIST:
        try:
            print(f"🤖 モデル [{model_name}] を呼び出し中...")
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            print(f"✅ モデル [{model_name}] で成功しました！")
            return response
        except Exception as e:
            print(f"⚠️ モデル [{model_name}] でエラーが発生: {e}")
            last_exception = e
    raise last_exception


def draw_precision_redpen_to_bytes(img: Image.Image, commands: list) -> bytes:
    """赤ペン描画（文字なし）"""
    img_work = img.copy().convert("RGB")
    draw = ImageDraw.Draw(img_work)
    width, height = img_work.size

    red_color = (255, 30, 30)
    line_width = 3

    for item in commands:
        a_type = item.get("type")

        def to_px(pts):
            return [(int(pt[0] * width / 1000), int(pt[1] * height / 1000)) for pt in pts]

        if a_type == "path" and "points" in item:
            pixel_points = to_px(item["points"])
            if len(pixel_points) >= 2:
                draw.line(pixel_points, fill=red_color, width=line_width, joint="curve")

        elif a_type == "line" and "points" in item:
            pixel_points = to_px(item["points"])
            if len(pixel_points) >= 2:
                draw.line(pixel_points, fill=red_color, width=line_width)

        elif a_type == "circle" and "box_2d" in item:
            ymin, xmin, ymax, xmax = item["box_2d"]
            left = int(xmin * width / 1000)
            top = int(ymin * height / 1000)
            right = int(xmax * width / 1000)
            bottom = int(ymax * height / 1000)
            draw.ellipse([left, top, right, bottom], outline=red_color, width=line_width)

        elif a_type == "arrow" and "points" in item:
            pixel_points = to_px(item["points"])
            if len(pixel_points) >= 2:
                draw.line(pixel_points, fill=red_color, width=line_width)
                p2 = pixel_points[1]
                draw.ellipse([p2[0]-5, p2[1]-5, p2[0]+5, p2[1]+5], fill=red_color)

    output = io.BytesIO()
    img_work.save(output, format="PNG", quality=95)
    return output.getvalue()


def send_discord_channel_message(channel_id: str, content: str):
    if not channel_id or not DISCORD_BOT_TOKEN:
        return
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, json={"content": content}, headers=headers)


@app.get("/api/cron")
@app.post("/api/cron")
async def handle_cron(request: Request, type: str = "morning"):
    users = get_all_users()
    today_str = date.today().isoformat()

    if type == "morning":
        ref_url = random.choice(SHINO_WORKS)
        msg = f"🌅 **【万波先生の朝の熱血お題出し！】**\n"
        msg += "おう！朝だぞ！今日のイラスト練習の準備はできているか！？\n\n"
        if users and users[0].get("last_advice"):
            msg += f"💡 **前回の課題・改善ポイント:**\n{users[0]['last_advice']}\n\n"
        msg += f"🎨 **本日の模写課題（千種みのり先生 / 早乙女志乃）：**\n{ref_url}\n"
        msg += "今日も上記の意識ポイントを念頭に置いて描いてみろ！待ってるぞ！"
        send_discord_channel_message(DISCORD_CHANNEL_ID, msg)

    elif type == "evening":
        already_reviewed = any(u.get("last_review_date") == today_str for u in users)
        if not already_reviewed:
            msg = f"🌙 **【万波先生の夜の確認だ！】**\n"
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


async def process_review_in_background(interaction_token, app_id, user_id, image_url, user_comment, is_fix):
    try:
        # 重い処理（Gemini呼び出し等）を asyncio.to_thread で別スレッドに追い出す
        await asyncio.to_thread(
            _sync_process_review, # 重い処理をまとめた関数
            interaction_token, app_id, user_id, image_url, user_comment, is_fix
        )
    except Exception as e:
        print(f"Background task error: {e}")

def _sync_process_review(token: str, app_id: str, user_id: str, image_url: str, user_comment: str, is_fix: bool):
    """
    バックグラウンド処理：
    is_fix == True の場合、前回画像と比較分析して修正努力を褒めつつ添削
    """
    try:
        user_data = get_user(user_id)
        last_advice = user_data.get("last_advice", "")
        
        # 今回送られてきた画像を読み込む
        img_resp = requests.get(image_url)
        current_img = Image.open(io.BytesIO(img_resp.content))
        width, height = current_img.size

        # Geminiに渡すコンテンツリストの初期化
        gemini_contents = [current_img]
        
        prompt_context = f"ユーザーコメント: {user_comment if user_comment else '特になし'}\n"

        if is_fix:
            prev_image_url = get_user_last_image(user_id)
            if prev_image_url:
                try:
                    prev_resp = requests.get(prev_image_url)
                    prev_img = Image.open(io.BytesIO(prev_resp.content))
                    gemini_contents = [prev_img, current_img]
                    prompt_context += (
                        "【ビフォーアフター比較モード】\n"
                        "1枚目の画像が「修正前（前回）」、2枚目の画像が「修正後（今回）」の作品です！\n"
                        f"前回のあなたのアドバイス（「{last_advice}」）を元に、生徒が描き直してくれました。\n"
                        "前回の課題がどれくらい改善されたかを2枚の画像を見比べて重点的に確認し、"
                        "描き直して挑戦した努力と上達したポイントを熱く褒めちぎってください！\n"
                    )
                except Exception as img_err:
                    print(f"⚠️ 前回画像の読み込みに失敗しました: {img_err}")
                    prompt_context += "（前回の修正版として提出されました！挑戦姿勢を褒めて指導してください）\n"
            else:
                prompt_context += "（前回の修正版として提出されました！挑戦姿勢を褒めて指導してください）\n"
        else:
            prompt_context += "このイラストを熱血指導してください！\n"

        system_instruction = """
        あなたはイラスト指導教官の「万波先生」です。
        見た目は少し強面ですが、野球部の熱血コーチのような力強い口調（「〜だぞ」「〜じゃねぇか」「おう！」）で生徒を指導します。
        イラストを分析し、アドバイス文章と骨格修正用の赤ペン描画コマンドを必ず指定されたJSONフォーマットのみで出力してください。Markdownの枠（```json ... ```）は不要です。
        """

        # ★ 描画精度を高めるためにプロンプトを厳格に指定
        prompt = f"""
        【最新（今回）画像情報】
        幅: {width}px, 高さ: {height}px
        コンテキスト: {prompt_context}

        【指示】
        イラスト内の「顔・人物」を正確に検出し、添削してください。

        1. advice: 万波先生口調での熱血アドバイス文章（日本語）。
        2. draw_commands: イラストの上に精密に引く赤ペン描画コマンド配列。

        【描画コマンドの厳密ルール】
        - 座標系: 0〜1000 の正規化座標（[0,0]が左上、[1000,1000]が右下）。
        - 必ず「キャラクターのパーツそのもの」に重なるように描画すること。背景や画像の端まで飛び出す大きな線を描いてはいけません。
        - 以下の具体線のみを出力してください：
          a) `line`: 顔の縦の正中線（額〜生え際〜鼻筋〜唇〜顎先をまっすぐ通る1本の直線）
          b) `line`: 目の水平ガードライン（左目頭〜右目尻を平行に通る1本の直線）
          c) `path` または `circle`: 両目の位置を正しく囲む円、または顎〜頭頂部の実際の輪郭に沿った曲線
          d) `arrow`: 修正すべき方向（例：顎を引き締める方向、髪のボリュームを増やす方向）を示す矢印

        【返却JSONフォーマット】
        {{
          "advice": "おう！熱い想いが伝わってくるぞ！だが顔の軸と目の水平ラインが少しずれてるな！...",
          "draw_commands": [
            {{ "type": "line", "points": [[500, 200], [500, 700]] }},
            {{ "type": "line", "points": [[350, 450], [650, 450]] }},
            {{ "type": "circle", "box_2d": [420, 360, 480, 440] }}
          ]
        }}
        """

        gemini_contents.append(prompt)

        # Gemini呼び出し
        response = generate_with_fallback(
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        res_text = response.text.strip()
        if res_text.startswith("```"):
            res_text = res_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()

        mannami_result = json.loads(res_text)
        advice_text = mannami_result.get("advice", "添削完了だ！")
        commands = mannami_result.get("draw_commands", [])

        # アドバイス要約処理
        summary_prompt = f"""
        以下の添削文から、描いた人が次回意識すべき「具体的な改善点・アドバイス」だけを抽出してください。
        【制約】挨拶や褒め言葉は除外 / 2〜3項目の簡潔な箇条書き / 万波先生口調（〜だぞ！など）は維持せず簡潔に / 100〜150文字程度
        【添削文】
        {advice_text}
        """
        summary_response = generate_with_fallback(contents=summary_prompt)
        short_advice = summary_response.text.strip()

        # ----------------------------------------------------
        # ③ XP判定（固定100XP）と DB更新
        # ----------------------------------------------------
        earned_xp = 100
        db_result = add_xp_and_update_advice(user_id, earned_xp, short_advice)
        
        update_user_last_image(user_id, image_url)

        # レスポンスメッセージ作成
        xp_msg = f"\n\n--- \n🔥 **+{earned_xp} XP 獲得！** (累計: {db_result['new_xp']} XP / Lv.{db_result['new_level']} [次Lvまで: {db_result['next_level_xp']} XP])"
        if is_fix:
            xp_msg = "\n✨ **【修正チャレンジ達成！】** ✨" + xp_msg
        if db_result.get("leveled_up"):
            xp_msg += f"\n🎉 **LEVEL UP!!** Lv.{db_result['new_level']} に上がったぞ！その調子だ！"

        final_text = advice_text + xp_msg

        # 赤ペン添削画像を最新イラストを元に生成
        image_bytes = draw_precision_redpen_to_bytes(current_img, commands)

        # Discord Webhookへ送信
        patch_url = f"[https://discord.com/api/v10/webhooks/](https://discord.com/api/v10/webhooks/){app_id}/{token}/messages/@original"
        payload = {"content": final_text}
        files = {
            "files[0]": ("tensaku_redpen.png", image_bytes, "image/png")
        }
        
        requests.patch(patch_url, data={"payload_json": json.dumps(payload)}, files=files)

    except Exception as e:
        final_response = f"おう…すまねぇ、処理中にエラーが起きちまった！（エラー: {e}）"
        patch_url = f"[https://discord.com/api/v10/webhooks/](https://discord.com/api/v10/webhooks/){app_id}/{token}/messages/@original"
        requests.patch(patch_url, json={"content": final_response})


@app.post("/")
async def interactions(request: Request, background_tasks: BackgroundTasks):
    t0 = time.time()
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()

    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    verify_discord_request(body, signature, timestamp)
    print(f"⏱️ 署名検証完了: {time.time() - t0:.2f}s")
    data = await request.json()
    print(f"⏱️ JSON解析完了: {time.time() - t0:.2f}s")

    # 1. Ping応答
    if data.get("type") == 1:
        return JSONResponse({"type": 1})

    # 2. コマンド応答
    if data.get("type") == 2:
        command_name = data["data"]["name"]
        interaction_token = data["token"]
        app_id = data["application_id"]
        user_id = data.get("member", {}).get("user", {}).get("id") or data.get("user", {}).get("id")

        if command_name == "review":
            options = {opt["name"]: opt["value"] for opt in data["data"].get("options", [])}
            resolved_attachments = data["data"].get("resolved", {}).get("attachments", {})

            attachment_id = options.get("image")
            image_info = resolved_attachments.get(attachment_id, {})
            image_url = image_info.get("url")
            user_comment = options.get("comment", "")
            is_fix = options.get("is_fix", False)
            print(f"⏱️ オプション取得完了: {time.time() - t0:.2f}s")
            # =========================================================
            # ★ ここが最重要ポイント！
            # Gemini呼び出しや画像処理、DB処理を行う重い関数は
            # 必ず background_tasks.add_task(...) に登録する！
            # =========================================================
            background_tasks.add_task(
                process_review_in_background,  # ← 27秒かかる関数
                interaction_token,
                app_id,
                user_id,
                image_url,
                user_comment,
                is_fix,
            )
            print(f"⏱️ add_task完了: {time.time() - t0:.2f}s")
            # =========================================================
            # ★ 重い処理を一切待たずに、0.05秒で即座にDiscordへType 5を返す！
            # =========================================================
            s = JSONResponse({"type": 5})
            print(f"⏱️ レスポンス返却直前: {time.time() - t0:.2f}s")
            return s

    return JSONResponse({"type": 4, "data": {"content": "未対応のコマンドだぞ！"}})