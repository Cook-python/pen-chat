import asyncio
import json
import sys
import time

import websockets

URI = "ws://127.0.0.1:9080/"
SEND_VAR = "☁ 送信"
RECV_VAR = "☁ 受信"
STATE_VAR = "☁ 状態"


async def main():
    seq = sys.argv[2] if len(sys.argv) > 2 else str(int(time.time()) % 10000)
    message_text = sys.argv[3] if len(sys.argv) > 3 else "こんにちは"

    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps({
            "method": "handshake",
            "user": "tester",
            "project_id": "1",
        }) + "\n")

        pending_initial = {SEND_VAR, RECV_VAR, STATE_VAR}
        recv_values = []
        sent_message = False
        thinking_started = False
        finished = False

        while not finished:
            raw = await asyncio.wait_for(ws.recv(), timeout=60)
            for line in str(raw).splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                name = msg["name"]
                value = msg["value"]
                print("<-", name, repr(value)[:40])

                if not sent_message and name in pending_initial:
                    pending_initial.discard(name)
                    continue

                if name == RECV_VAR and sent_message:
                    recv_values.append(value)
                if name == STATE_VAR and sent_message:
                    if value == "1":
                        thinking_started = True
                    elif value == "0" and thinking_started:
                        finished = True

            if not sent_message and not pending_initial:
                await ws.send(json.dumps({
                    "method": "set",
                    "name": SEND_VAR,
                    "value": "%s|%s" % (seq, message_text),
                }) + "\n")
                sent_message = True

        for i, v in enumerate(recv_values):
            print("VALUE", i, "seq=%s" % v[:4], "len=", len(v))

        with open(sys.argv[1], "w", encoding="utf-8") as f:
            json.dump(recv_values, f, ensure_ascii=False)


asyncio.run(main())
