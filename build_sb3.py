import os

from sb3lib import *
from sb3lib import b, A, SNUM, STXT, SWHOLE, SIDX

SEND = "☁ 送信"
RECV = "☁ 受信"
STATE = "☁ 状態"

PALETTE = [0x202830, 0x7fd8ff, 0xffffff, 0xffd23f, 0x9affa0,
           0xff9ab0, 0xc0c0c0, 0x808080, 0x404040, 0x000000]


def ask(q):
    return b.add("sensing_askandwait", inputs={"QUESTION": A(q, STXT)})


def answer():
    return b.add("sensing_answer")


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
    variables=["受信前", "送信連番", "本文", "長さ", "i", "rc", "行色",
               "行数", "r", "idx", "上端", "残り", "消去数", "状態前",
               "行高", "最大行", "基準Y", "seg", "sy"],
    lists=["SEGY", "SEGX1", "SEGX2", "ROWC", "ROWN", "PAL"],
    cloud=[SEND, RECV, STATE],
)

define("古い行を消す", [], [
    setv("消去数", item("ROWN", 1)),
    repeat_(var("消去数"), [dell("SEGY", 1), dell("SEGX1", 1), dell("SEGX2", 1)]),
    dell("ROWC", 1),
    dell("ROWN", 1),
    changev("行数", -1),
], x=0, y=0)

define("受信を取り込む", [], [
    setv("本文", cvar(RECV)),
    setv("長さ", length_(var("本文"))),
    setv("i", 5),
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
    ifb(eq(cvar(STATE), 1), [
        pencolor(item("PAL", 5)),
        pensize(4),
        setv("seg", 0),
        repeat_(3, [
            gotoxy(add_(-224, mul_(var("seg"), 10)), -160),
            pendown(),
            penup(),
            changev("seg", 1),
        ]),
    ]),
], x=0, y=560)

b.link([
    whenflag(x=400, y=0),
    hide(),
    setv("行高", 19),
    setv("最大行", 16),
    setv("基準Y", 170),
    setv("行数", 0),
    setv("送信連番", 0),
    dellall("SEGY"), dellall("SEGX1"), dellall("SEGX2"),
    dellall("ROWC"), dellall("ROWN"),
    setv("受信前", cvar(RECV)),
    setv("状態前", cvar(STATE)),
    penclear(),
    penup(),
    forever_([
        ifb(not_(eq(cvar(RECV), var("受信前"))), [
            setv("受信前", cvar(RECV)),
            call("受信を取り込む"),
            call("再描画"),
        ]),
        ifb(not_(eq(cvar(STATE), var("状態前"))), [
            setv("状態前", cvar(STATE)),
            call("再描画"),
        ]),
    ]),
])

b.link([
    whenflag(x=400, y=400),
    forever_([
        ask(""),
        ifb(gt(length_(answer()), 0), [
            changev("送信連番", 1),
            setcv(SEND, join_(join_(var("送信連番"), "|"), answer())),
            until_(eq(cvar(STATE), 1), []),
            until_(eq(cvar(STATE), 0), []),
        ]),
    ]),
])

print(save(os.path.join(os.path.dirname(__file__), "pen_chat.sb3"),
           sprite_name="端末",
           extensions=["pen"],
           list_values={"PAL": PALETTE}))
