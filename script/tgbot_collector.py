#!/usr/bin/env python3
"""
tgbot_collector.py — 纯收集模式
- 接收所有 Telegram 消息，记录到 JSON 文件
- 不执行任何命令，不读取任何文件
- 每条消息记录: timestamp, update_id, user_id, username, first_name,
  chat_id, chat_type, text, entities, is_command
- 收集到的消息会回复发送者 "[COLLECTOR] 消息已记录，不执行命令"
"""

import os
import sys
import json
import time
import signal
from datetime import datetime, timezone

import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("请设置环境变量 BOT_TOKEN")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 输出文件路径（workflow 会把这个文件上传为 artifact）
LOG_FILE = os.environ.get("COLLECTOR_LOG_FILE", "/home/runner/tgbot_messages.jsonl")

# 运行时长（秒），到时间自动退出
RUN_DURATION = int(os.environ.get("COLLECTOR_DURATION", "120"))

# 统计
msg_count = 0
start_time = time.time()


def log_message(record):
    """追加一条 JSON 记录到日志文件"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def send_message(chat_id, text):
    try:
        requests.post(
            f"{API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )
    except Exception as e:
        print(f"[send error] {e}", flush=True)


def handle_update(update):
    global msg_count

    update_id = update.get("update_id")
    message = update.get("message")

    if not message:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "update_id": update_id,
            "type": "non_message",
            "raw": update,
        }
        log_message(record)
        print(f"[SKIP] non-message update {update_id}", flush=True)
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "")
    text = message.get("text", "")
    from_user = message.get("from", {})
    user_id = from_user.get("id", "?")
    username = from_user.get("username", "")
    first_name = from_user.get("first_name", "")
    date = message.get("date", 0)

    entities = message.get("entities", [])

    msg_count += 1

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "msg_seq": msg_count,
        "update_id": update_id,
        "tg_date": date,
        "tg_date_str": datetime.fromtimestamp(date, tz=timezone.utc).isoformat()
        if date
        else "",
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "text": text,
        "entities": entities,
        "is_command": any(
            e.get("type") == "bot_command" for e in entities
        ),
    }

    log_message(record)

    print(
        f"[#{msg_count}] @{username} (id={user_id}) "
        f"chat={chat_id} text={text!r}",
        flush=True,
    )

    send_message(
        chat_id,
        f"📋 [COLLECTOR MODE]\n"
        f"消息 #{msg_count} 已记录\n"
        f"From: @{username} (id={user_id})\n"
        f"⚠️ 收集模式：不执行任何命令",
    )


def main():
    global msg_count

    print(f"=== tgbot_collector started ===", flush=True)
    print(f"LOG_FILE: {LOG_FILE}", flush=True)
    print(f"RUN_DURATION: {RUN_DURATION}s", flush=True)
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}", flush=True)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        header = {
            "type": "collector_header",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "run_duration": RUN_DURATION,
            "log_file": LOG_FILE,
        }
        f.write(json.dumps(header, ensure_ascii=False) + "\n")

    offset = None

    while True:
        elapsed = time.time() - start_time
        if elapsed >= RUN_DURATION:
            print(
                f"=== collector finished: {msg_count} messages in {elapsed:.1f}s ===",
                flush=True,
            )
            break

        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset

            resp = requests.get(
                f"{API}/getUpdates",
                params=params,
                timeout=40,
            )
            data = resp.json()

            if not data.get("ok"):
                print(f"[getUpdates error] {data}", flush=True)
                time.sleep(5)
                continue

            updates = data.get("result", [])

            if updates:
                print(
                    f"[info] Received {len(updates)} update(s), "
                    f"elapsed {elapsed:.1f}s",
                    flush=True,
                )

            for update in updates:
                offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception as e:
                    print(
                        f"[handle error] update={update.get('update_id')}: {e}",
                        flush=True,
                    )

        except KeyboardInterrupt:
            print("=== stopped by KeyboardInterrupt ===", flush=True)
            break
        except Exception as e:
            print(f"[polling error] {e}", flush=True)
            time.sleep(5)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        footer = {
            "type": "collector_footer",
            "end_time": datetime.now(timezone.utc).isoformat(),
            "total_messages": msg_count,
            "elapsed_seconds": time.time() - start_time,
        }
        f.write(json.dumps(footer, ensure_ascii=False) + "\n")

    print(f"=== log saved to {LOG_FILE} ===", flush=True)


if __name__ == "__main__":
    main()
