import sqlite3
import os

DB_PATH = "/tmp/mannami_bot.db"  # Vercel等のサーバーで書き込み可能な一時領域

def init_db():
    """データベースとテーブルの初期化"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_advice TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: str):
    """ユーザー情報の取得（存在しなければ新規作成）"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level, last_advice FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xp, level, last_advice) VALUES (?, 0, 1, '')", (user_id,))
        conn.commit()
        xp, level, last_advice = 0, 1, ""
    else:
        xp, level, last_advice = row
    conn.close()
    return {"xp": xp, "level": level, "last_advice": last_advice}

def add_xp_and_update_advice(user_id: str, added_xp: int, new_advice: str):
    """XPの加算、レベルアップ計算、最新のアドバイスの更新"""
    user = get_user(user_id)
    new_xp = user["xp"] + added_xp
    
    # 簡易レベル計算（100XPごとに1レベルアップ）
    new_level = (new_xp // 100) + 1
    leveled_up = new_level > user["level"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET xp = ?, level = ?, last_advice = ? 
        WHERE user_id = ?
    """, (new_xp, new_level, new_advice, user_id))
    conn.commit()
    conn.close()

    return {"new_xp": new_xp, "new_level": new_level, "leveled_up": leveled_up}