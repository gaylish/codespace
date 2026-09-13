#!/usr/bin/env python3
"""
tgbot_debug.py — 调试版，只记录收到的消息，不执行任何命令。
日志同时输出到 stdout(journald) 和文件 /home/runner/tgbot_messages.log
每条消息带精确时间戳，方便分析发送模式。
"""

import os
import time
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("请设置环境变量 BOT_TOKEN")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE = "/home/runner/tgbot_messages.log"

def log(text):
    """同时写到 stdout 和文件"""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def send_message(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=30)
    except Exception as e:
        log(f"[send error] {e}")

# 初始化日志文件
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== tgbot_debug started at {datetime.now()} ===\n")
    f.write(f"BOT_TOKEN set: {bool(BOT_TOKEN)} (len={len(BOT_TOKEN)})\n\n")

log("=== tgbot_debug started ===")
log(f"BOT_TOKEN set: {bool(BOT_TOKEN)} (len={len(BOT_TOKEN)})")

offset = None
msg_count = 0

while True:
    try:
        params = {"timeout": 30}
        if offset is not None:
            params["offset"] = offset

        resp = requests.get(f"{API}/getUpdates", params=params, timeout=40)
        data = resp.json()

        if not data.get("ok"):
            log(f"[getUpdates error] {data}")
            time.sleep(5)
            continue

        updates = data.get("result", [])
        if updates:
            log(f"[info] Received {len(updates)} update(s)")

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                log(f"[skip] non-message update type: {list(update.keys())}")
                continue

            chat = message.get("chat", {})
            chat_id = chat.get("id")
            text = message.get("text", "")
            from_user = message.get("from", {})
            username = from_user.get("username", "unknown")
            user_id = from_user.get("id", "?")
            msg_date = message.get("date", 0)

            msg_count += 1
            # Telegram 原始时间戳
            if msg_date:
                tg_time = datetime.fromtimestamp(msg_date).strftime('%Y-%m-%d %H:%M:%S')
            else:
                tg_time = "?"

            log(f"--- MESSAGE #{msg_count} ---")
            log(f"  TG_Time: {tg_time}")
            log(f"  From: @{username} (id={user_id})")
            log(f"  Chat: {chat_id}")
            log(f"  Text: {text!r}")

            # 回复但不执行
            reply = (
                f"🔍 [DEBUG MODE]\n"
                f"消息 #{msg_count}\n"
                f"From: @{username} (id={user_id})\n"
                f"Time: {tg_time}\n"
                f"Text: {text}\n"
                f"⚠️ 调试模式：不执行任何命令"
            )
            send_message(chat_id, reply)

    except KeyboardInterrupt:
        log("=== stopped ===")
        break
    except Exception as e:
        log(f"[polling error] {e}")
        time.sleep(5)
