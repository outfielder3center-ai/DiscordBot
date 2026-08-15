import math
import os
from datetime import date
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Supabase (PostgreSQL) への接続を取得"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set!")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """テーブルの初期化（存在しない場合のみ作成）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_advice TEXT DEFAULT '',
            last_review_date TEXT DEFAULT ''
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id: str):
    """ユーザー情報の取得（いなければ作成）"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level, last_advice, last_review_date FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xp, level, last_advice, last_review_date) VALUES (%s, 0, 1, '', '')", (user_id,))
        conn.commit()
        xp, level, last_advice, last_review_date = 0, 1, "", ""
    else:
        xp, level, last_advice, last_review_date = row
    
    cursor.close()
    conn.close()
    return {
        "xp": xp,
        "level": level,
        "last_advice": last_advice,
        "last_review_date": last_review_date
    }

def add_xp_and_update_advice(user_id: str, added_xp: int, new_advice: str):
    """XP追加と動的レベル計算、および前回の改善点の更新"""
    user = get_user(user_id)
    current_xp = user["xp"]
    current_level = user["level"]

    new_xp = current_xp + added_xp
    temp_xp = new_xp  # レベルアップ判定用の残りXP
    new_level = current_level

    # 現在のレベルに必要なXPを算出し、蓄積XPが上回っている限りレベルアップを繰り返す
    while True:
        # ceil(現在のレベル ** 0.5) * 100
        required_xp_for_next_level = math.ceil(math.sqrt(new_level)) * 100

        if temp_xp >= required_xp_for_next_level:
            temp_xp -= required_xp_for_next_level
            new_level += 1
        else:
            break

    leveled_up = new_level > current_level
    today_str = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users 
        SET xp = %s, level = %s, last_advice = %s, last_review_date = %s
        WHERE user_id = %s
    """,
        (new_xp, new_level, new_advice, today_str, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "new_xp": new_xp,
        "new_level": new_level,
        "leveled_up": leveled_up,
        "next_level_xp": math.ceil(math.sqrt(new_level)) * 100 - new_xp,  # 次のレベルまでの必要XP目安
    }

def get_all_users():
    """全登録ユーザーの取得（Cron用）"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, last_advice, last_review_date FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"user_id": r[0], "last_advice": r[1], "last_review_date": r[2]} for r in rows]

def get_user_last_image(user_id: str) -> str:
    """指定されたユーザーの 'last_image_url' を取得する"""
    user = get_user(user_id)
    return user.get("last_image_url", "")

def update_user_last_image(user_id: str, image_url: str):
    """指定されたユーザーの 'last_image_url' を更新する"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET last_image_url = %s
        WHERE user_id = %s
    """, (image_url, user_id))
    conn.commit()
    cursor.close()
    conn.close()