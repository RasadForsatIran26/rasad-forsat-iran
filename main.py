
import json
import os
import sqlite3
import time
import hashlib
from datetime import datetime, timezone

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "300"))
DB_PATH = os.getenv("DATABASE_PATH", "rasad.db")

KEYWORDS = {
    "استخدام": ["استخدام", "جذب نیرو", "آزمون استخدامی", "فرصت شغلی"],
    "خودرو": ["فروش خودرو", "قرعه کشی خودرو", "پیش فروش خودرو"],
    "مزایده": ["مزایده", "حراج"],
    "وام": ["وام", "تسهیلات", "اعتبار"],
    "بازار": ["طلا", "دلار", "بیت کوین", "بورس", "ارز", "نفت", "سهام"],
    "سرمایه گذاری": ["سرمایه گذاری", "کارآفرینی", "فرصت اقتصادی"]
}


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            category TEXT,
            published TEXT
        )
    """)
    conn.commit()
    return conn


def classify(text):
    text = text.lower()
    for category, words in KEYWORDS.items():
        if any(word.lower() in text for word in words):
            return category
    return "سایر"


def load_sources():
    with open("sources.json", encoding="utf-8") as file:
        return json.load(file)


def poll_once():
    conn = connect_db()

    for source in load_sources():
        if not source.get("enabled"):
            continue

        try:
            feed = feedparser.parse(source["url"])

            for entry in feed.entries:
                title = entry.get("title", "بدون عنوان")
                link = entry.get("link", "")
                summary = entry.get("summary", "")

                fingerprint = hashlib.sha256(
                    (source["url"] + link + title).encode()
                ).hexdigest()

                category = classify(title + " " + summary)

                try:
                    conn.execute(
                        """INSERT INTO items
                        (id, title, link, category, published)
                        VALUES (?, ?, ?, ?, ?)""",
                        (
                            fingerprint,
                            title,
                            link,
                            category,
                            datetime.now(timezone.utc).isoformat()
                        )
                    )
                    conn.commit()

                    print(f"[{category}] {title}")
                    print(link)
                    print("-" * 40)

                except sqlite3.IntegrityError:
                    continue

        except Exception as error:
            print("خطا در دریافت منبع:", error)

    conn.close()


if __name__ == "__main__":
    print("سامانه رصد فرصت ایران آغاز شد.")
    print("حالت فعلی: آزمایشی و بدون انتشار خودکار")

    while True:
        try:
            poll_once()
        except Exception as error:
            print("خطای برنامه:", error)

        time.sleep(POLL_SECONDS)
              
