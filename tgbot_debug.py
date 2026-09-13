#!/usr/bin/env python3
"""
tgbot_debug.py — 调试版，只记录收到的消息，不执行任何命令。
所有消息都会打印到 stdout（journald 可见）并回复给发送者。
"""

import os
import time
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("请设置环境变量 BOT_TOKEN")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=30)
    except Exception as e:
        print(f"[send error] {e}")

print("=== tgbot_debug started ===")
print(f"BOT_TOKEN set: {bool(BOT_TOKEN)} (len={len(BOT_TOKEN)})")

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
            print(f"[getUpdates error] {data}")
            time.sleep(5)
            continue

        updates = data.get("result", [])
        if updates:
            print(f"[info] Received {len(updates)} update(s)")

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                print(f"[skip] non-message update: {update}")
                continue

            chat = message.get("chat", {})
            chat_id = chat.get("id")
            text = message.get("text", "")
            from_user = message.get("from", {})
            username = from_user.get("username", "unknown")
            user_id = from_user.get("id", "?")

            msg_count += 1
            # 打印到 journald
            print(f"=== MESSAGE #{msg_count} ===")
            print(f"  From: @{username} (id={user_id})")
            print(f"  Chat: {chat_id}")
            print(f"  Text: {text!r}")
            print(f"  Raw: {message}")

            # 回复但不执行
            reply = (
                f"🔍 [DEBUG MODE]\n"
                f"收到消息 #{msg_count}\n"
                f"From: @{username} (id={user_id})\n"
                f"Text: {text}\n"
                f"⚠️ 调试模式：不执行任何命令"
            )
            send_message(chat_id, reply)

    except KeyboardInterrupt:
        print("=== stopped ===")
        break
    except Exception as e:
        print(f"[polling error] {e}")
        time.sleep(5)
