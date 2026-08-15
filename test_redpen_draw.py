import os
import json
import re
from PIL import Image, ImageDraw
from google import genai

# APIキーの設定
GEMINI_API_KEY = "AQ.Ab8RN6IFlozzLdQH79UFQN9yTJgFESPHa4-Ey0S0fx01vdC9NQ"
client = genai.Client(api_key=GEMINI_API_KEY)

# 視覚分析に強いモデルを使用
MODEL_NAME = "gemini-3.6-flash"

def analyze_and_get_redpen_annotations(image_path: str):
    """画像を分析し、Geminiに精密なプロのアタリ線（JSON）を吐き出させる"""
    img = Image.open(image_path)
    
    # プロンプト（精度特化：機械的図形禁止、吸い付きを指示）
    prompt = """
    あなたは情熱的で的確なアドバイスを行うプロのイラスト講師「万波（まんなみ）先生」です。
    提供されたイラストを分析し、デッサン、骨格、パーツ配置の修正箇所（アタリ線）を赤ペンで描き込むためのJSONフォーマットのみを出力してください。解説やMarkdownの枠（```json ... ```）や、コメントは不要です。

    【重要：精度向上のルール】
    - 単なる十字や円を重ねるのではなく、イラストの【輪郭や骨格、パーツに沿って吸い付くような】アタリ線を引いてください。
    - 特に、顎のライン、髪のシルエット、目の水平ライン、顔の正中線を精密に捉えてください。勘で座標を置かないこと。
    - コマンドの種類は簡素化し、顎ラインなどは精密な曲線（path）で捉えること。

    【出力JSONフォーマット】
    [
      {{
        "type": "path",  // 顎ラインや髪のシルエットに沿った【吸い付くような曲線】
        "points": [[x1, y1], [x2, y2], [x3, y3]] // 精密な通過座標（0-1000）
      }},
      {{
        "type": "line",  // 目の水平ラインや正中線
        "points": [[x1, y1], [x2, y2]]
      }},
      {{
        "type": "circle",  // 骨格としての頭のアタリや、各目の囲み
        "box_2d": [ymin, xmin, ymax, xmax]
      }},
      {{
        "type": "arrow",  // 修正方向の矢印
        "points": [[始点x, 始点y], [終点x, 終点y]]
      }}
    ]
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[img, prompt]
    )
    
    res_text = response.text.strip()
    if res_text.startswith("```"):
        res_text = res_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    
    try:
        annotations = json.loads(res_text)
        print(f"解析成功！添削データ: {len(annotations)}件")
        return annotations
    except Exception as e:
        print(f"JSONパースエラー: {e}")
        return []


def draw_redpen_on_image(image_path: str, annotations: list, output_path: str):
    """Pillowを使って、解析結果に基づき精密な赤ペン添削を描き込む（テキスト廃止版）"""
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # 赤ペンの設定（テキストがないため、少し細くして精密感を出す）
    red_color = (255, 30, 30)  # 鮮やかな赤
    line_width = 3  # 精密に引くため、少し細く

    for item in annotations:
        a_type = item.get("type")

        # 1. 精密な曲線 (path) - 顎ラインや髪のアタリ
        if a_type == "path" and "points" in item:
            pts = item["points"]
            pixel_points = [(int(pt[0] * width / 1000), int(pt[1] * height / 1000)) for pt in pts]
            if len(pixel_points) >= 2:
                # 曲線を描く（Pillowでは直線で繋ぐ）
                draw.line(pixel_points, fill=red_color, width=line_width, joint="curve")

        # 2. 直線 (line) - 正中線や目の水平ライン
        elif a_type == "line" and "points" in item:
            pts = item["points"]
            if len(pts) >= 2:
                pixel_points = [(int(pt[0] * width / 1000), int(pt[1] * height / 1000)) for pt in pts]
                draw.line(pixel_points, fill=red_color, width=line_width)

        # 3. 丸 / 囲み (circle)
        elif a_type == "circle" and "box_2d" in item:
            box = item["box_2d"]
            left = int(box[1] * width / 1000)
            top = int(box[0] * height / 1000)
            right = int(box[3] * width / 1000)
            bottom = int(box[2] * height / 1000)
            draw.ellipse([left, top, right, bottom], outline=red_color, width=line_width)

        # 4. 矢印 (arrow)
        elif a_type == "arrow" and "points" in item:
            pts = item["points"]
            if len(pts) >= 2:
                pixel_points = [(int(pt[0] * width / 1000), int(pt[1] * height / 1000)) for pt in pts]
                draw.line(pixel_points, fill=red_color, width=line_width)
                # 簡易矢印の先端
                p2 = pixel_points[1]
                # 矢印先端の描画
                draw.ellipse([p2[0]-5, p2[1]-5, p2[0]+5, p2[1]+5], fill=red_color)

    img.save(output_path, quality=95)
    print(f"🖼️ 完了！添削画像を保存しました: {output_path}")


if __name__ == "__main__":
    input_file = "test.jpg"  # あなたのイラストファイル
    output_file = "mannami_precision_result.png"

    if os.path.exists(input_file):
        print("🔍 イラスト分析開始...")
        annotations = analyze_and_get_redpen_annotations(input_file)
        
        if annotations:
            print("🎨 精密赤ペン添削画像を生成中（テキスト廃止版）...")
            draw_redpen_on_image(input_file, annotations, output_file)
        else:
            print("添削データが取得できませんでした。")
    else:
        print(f"エラー: 入力ファイル '{input_file}' が見つかりません。")