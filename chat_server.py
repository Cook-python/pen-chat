import asyncio
import json
import os
import urllib.error
import urllib.request

import websockets

import pen_text

HOST = os.environ.get("PEN_CHAT_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("PEN_CHAT_PORT", "9080")))
MAX_PAYLOAD = 90000

SEND = "☁ 送信"
RECV = "☁ 受信"
STATE = "☁ 状態"

COLOR_USER = 1
COLOR_BOT = 2

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("PEN_CHAT_MODEL", "qwen/qwen3.8-27b")
GROQ_REASONING_EFFORT = os.environ.get("PEN_CHAT_REASONING_EFFORT", "none")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT = float(os.environ.get("PEN_CHAT_TIMEOUT", "25"))
MAX_NEW_TOKENS = int(os.environ.get("PEN_CHAT_MAX_TOKENS", "96"))
MAX_REPLY_CHARS = int(os.environ.get("PEN_CHAT_MAX_REPLY_CHARS", "300"))
HISTORY_TURNS = int(os.environ.get("PEN_CHAT_HISTORY_TURNS", "4"))

SYSTEM_PROMPT = (
    "あなたはScratchのステージにペンで文字を描いて表示する小さな端末の中身です。"
    "返答は日本語の口語で、2〜3文程度の短い文章にまとめてください。"
    "箇条書きや記号による装飾、コードブロックは使わないでください。"
)

SENTENCE_END = "。！？!?\n"
QUOTE_OPEN = "「『"
QUOTE_CLOSE = "」』"

if not GROQ_API_KEY:
    raise SystemExit(
        "環境変数 GROQ_API_KEY が設定されていません。"
        "https://console.groq.com/keys で取得して設定してください。")

rooms = {}


class Room:
    def __init__(self):
        self.vars = {SEND: "0000", RECV: "0000", STATE: "0"}
        self.clients = set()
        self.last_send_seq = "0000"
        self.recv_seq = 0
        self.history = []


async def push(room, name):
    if not room.clients:
        return
    msg = json.dumps({"method": "set", "name": name, "value": room.vars[name]}) + "\n"
    dead = []
    for ws in room.clients:
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        room.clients.discard(ws)


async def set_var(room, name, value):
    room.vars[name] = value
    await push(room, name)


def call_groq(messages):
    body = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": MAX_NEW_TOKENS,
        "temperature": 0.7,
        "reasoning_effort": GROQ_REASONING_EFFORT,
    }).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL,
        data=body,
        headers={
            "Authorization": "Bearer %s" % GROQ_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "pen-chat/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=GROQ_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def split_chunks(text):
    chunks = []
    buf = []
    depth = 0
    for ch in text:
        buf.append(ch)
        if ch in QUOTE_OPEN:
            depth += 1
        elif ch in QUOTE_CLOSE:
            depth = max(0, depth - 1)
        elif ch in SENTENCE_END and depth == 0:
            chunk = "".join(buf).strip()
            if chunk:
                chunks.append(chunk)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        chunks.append(tail)
    return chunks


async def generate_reply(room, text):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(room.history)
    messages.append({"role": "user", "content": text})
    try:
        reply = await asyncio.to_thread(call_groq, messages)
    except urllib.error.HTTPError as exc:
        print("生成エラー:", exc.code, exc.read().decode("utf-8", "replace")[:500])
        return None
    except Exception as exc:
        print("生成エラー:", repr(exc))
        return None
    if len(reply) > MAX_REPLY_CHARS:
        reply = reply[:MAX_REPLY_CHARS] + "…"
    room.history.append({"role": "user", "content": text})
    room.history.append({"role": "assistant", "content": reply})
    del room.history[:-HISTORY_TURNS * 2]
    return reply


async def show(room, text, color, align):
    payload = pen_text.encode(text, color, align)
    if len(payload) > MAX_PAYLOAD:
        payload = payload[:0]
    room.recv_seq = (room.recv_seq + 1) % 10000
    await set_var(room, RECV, "%04d%s" % (room.recv_seq, payload))
    await asyncio.sleep(0.15)


async def handle_send(room, value):
    seq, sep, text = value.partition("|")
    if not sep or seq == room.last_send_seq:
        return
    room.last_send_seq = seq
    text = text.strip()
    if not text:
        return
    print("<<", text)
    await show(room, text, COLOR_USER, "right")
    await set_var(room, STATE, "1")
    reply = await generate_reply(room, text)
    if reply is None:
        await show(room, "(応答の生成に失敗しました)", COLOR_BOT, "left")
    else:
        print(">>", reply)
        for chunk in split_chunks(reply):
            await show(room, chunk, COLOR_BOT, "left")
    await set_var(room, STATE, "0")


async def serve(ws):
    room = None
    try:
        async for raw in ws:
            for line in str(raw).splitlines():
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                method = msg.get("method")
                if method == "handshake":
                    key = str(msg.get("project_id", "0"))
                    room = rooms.setdefault(key, Room())
                    room.clients.add(ws)
                    for name in room.vars:
                        await ws.send(json.dumps(
                            {"method": "set", "name": name,
                             "value": room.vars[name]}) + "\n")
                    print("接続:", msg.get("user"), "room", key)
                elif method == "set" and room is not None:
                    name = msg.get("name")
                    value = str(msg.get("value"))
                    if name not in room.vars:
                        continue
                    room.vars[name] = value
                    if name == SEND:
                        await handle_send(room, value)
                    else:
                        await push(room, name)
    except Exception as exc:
        print("切断:", exc)
    finally:
        if room:
            room.clients.discard(ws)


async def main():
    print("待受 ws://%s:%d/" % (HOST, PORT))
    async with websockets.serve(serve, HOST, PORT, max_size=2 ** 22):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
