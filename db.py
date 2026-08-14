import sqlite3
import os
from datetime import datetime, date

DB_PATH = "/tmp/mannami_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

def get_user(user_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level, last_advice, last_review_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xp, level, last_advice, last_review_date) VALUES (?, 0, 1, '', '')", (user_id,))
        conn.commit()
        xp, level, last_advice, last_review_date = 0, 1, "", ""
    else:
        xp, level, last_advice, last_review_date = row
    conn.close()
    return {
        "xp": xp,
        "level": level,
        "last_advice": last_advice,
        "last_review_date": last_review_date
    }

def add_xp_and_update_advice(user_id: str, added_xp: int, new_advice: str):
    user = get_user(user_id)
    new_xp = user["xp"] + added_xp
    new_level = (new_xp // 100) + 1
    leveled_up = new_level > user["level"]
    today_str = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET xp = ?, level = ?, last_advice = ?, last_review_date = ?
        WHERE user_id = ?
    """, (new_xp, new_level, new_advice, today_str, user_id))
    conn.commit()
    conn.close()

    return {"new_xp": new_xp, "new_level": new_level, "leveled_up": leveled_up}

def get_all_users():
    """全登録ユーザーの取得（Cron用）"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, last_advice, last_review_date FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": r[0], "last_advice": r[1], "last_review_date": r[2]} for r in rows]