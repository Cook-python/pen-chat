import os

from sb3lib import *
from sb3lib import b, A, SNUM, STXT, SWHOLE, SIDX

import pen_text

PALETTE = [0x202830, 0x7fd8ff, 0xffffff, 0xffd23f, 0x9affa0,
           0xff9ab0, 0xc0c0c0, 0x808080, 0x404040, 0x000000]

TITLE = 3
USER = 1
BOT = 2

SCRIPT = [
    ("pen_chat", TITLE, "left", 2.0),
    ("Scratchでも、AIとおしゃべりできる。", TITLE, "left", 2.5),
    ("文字は全部、Pythonが送ってくる線分をペンでなぞって描いている。", TITLE, "left", 3.0),
    ("ねえ、これって本当にScratchなの?", USER, "right", 2.0),
    ("うん、本物のScratchだよ。フォントは持たずに、届いた線分をペンでなぞっているんだ。", BOT, "left", 3.2),
    ("AIともちゃんと話せるの?", USER, "right", 1.8),
    ("話せるよ。裏側でAIが考えて、返事だけがここに届く仕組みになってる。", BOT, "left", 3.0),
    ("使ってみたい!", USER, "right", 1.5),
    ("こちらからどうぞ↓", BOT, "left", 1.5),
    ("https://chat-in-scratch.netlify.app", TITLE, "left", 4.0),
]


def digit(pos, src):
    return letter(pos, var(src))


def num(start, width, src):
    total = None
    for k in range(width):
        term = digit(add_(var(start), k), src)
        scale = 10 ** (width - 1 - k)
        piece = mul_(term, scale) if scale != 1 else term
        total = piece if total is None else add_(total, piece)
    return total


declare(
    variables=["本文", "長さ", "i", "rc", "行色", "行数", "r", "idx",
               "上端", "残り", "消去数", "行高", "最大行", "基準Y",
               "sy", "mi"],
    lists=["SEGY", "SEGX1", "SEGX2", "ROWC", "ROWN", "PAL", "MESSAGES", "WAITS"],
)

define("古い行を消す", [], [
    setv("消去数", item("ROWN", 1)),
    repeat_(var("消去数"), [dell("SEGY", 1), dell("SEGX1", 1), dell("SEGX2", 1)]),
    dell("ROWC", 1),
    dell("ROWN", 1),
    changev("行数", -1),
], x=0, y=0)

define("メッセージを取り込む", ["本文"], [
    setv("本文", arg("本文")),
    setv("長さ", length_(var("本文"))),
    setv("i", 1),
    until_(gt(var("i"), var("長さ")), [
        setv("rc", num("i", 4, "本文")),
        changev("i", 4),
        setv("行色", digit(var("i"), "本文")),
        changev("i", 1),
        addl("ROWC", var("行色")),
        addl("ROWN", var("rc")),
        changev("行数", 1),
        repeat_(var("rc"), [
            addl("SEGY", num("i", 2, "本文")),
            changev("i", 2),
            addl("SEGX1", num("i", 3, "本文")),
            changev("i", 3),
            addl("SEGX2", num("i", 3, "本文")),
            changev("i", 3),
        ]),
        until_(not_(gt(var("行数"), var("最大行"))), [call("古い行を消す")]),
    ]),
], x=0, y=260)

define("再描画", [], [
    penclear(),
    penup(),
    pencolor(item("PAL", 1)),
    pensize(400),
    gotoxy(-440, 0),
    pendown(),
    gotoxy(440, 0),
    penup(),
    pensize(1),
    setv("idx", 1),
    setv("r", 1),
    repeat_(var("行数"), [
        pencolor(item("PAL", add_(item("ROWC", var("r")), 1))),
        setv("上端", sub_(var("基準Y"), mul_(sub_(var("r"), 1), var("行高")))),
        setv("残り", item("ROWN", var("r"))),
        repeat_(var("残り"), [
            setv("sy", sub_(var("上端"), item("SEGY", var("idx")))),
            gotoxy(sub_(item("SEGX1", var("idx")), 240), var("sy")),
            pendown(),
            gotoxy(sub_(item("SEGX2", var("idx")), 240), var("sy")),
            penup(),
            changev("idx", 1),
        ]),
        changev("r", 1),
    ]),
], x=0, y=560)

b.link([
    whenflag(x=400, y=0),
    hide(),
    setv("行高", 19),
    setv("最大行", 16),
    setv("基準Y", 170),
    penclear(),
    penup(),
    forever_([
        setv("行数", 0),
        dellall("SEGY"), dellall("SEGX1"), dellall("SEGX2"),
        dellall("ROWC"), dellall("ROWN"),
        setv("mi", 1),
        repeat_(lenl("MESSAGES"), [
            call("メッセージを取り込む", item("MESSAGES", var("mi"))),
            call("再描画"),
            wait_(item("WAITS", var("mi"))),
            changev("mi", 1),
        ]),
    ]),
])

messages = [pen_text.encode(text, color, align) for text, color, align, _ in SCRIPT]
waits = [w for _, _, _, w in SCRIPT]

print(save(os.path.join(os.path.dirname(__file__), "pen_chat_promo.sb3"),
           sprite_name="看板",
           extensions=["pen"],
           list_values={"PAL": PALETTE, "MESSAGES": messages, "WAITS": waits}))
