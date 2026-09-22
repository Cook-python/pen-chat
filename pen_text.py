import os
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "C:\\Windows\\Fonts\\YuGothM.ttc",
    "C:\\Windows\\Fonts\\meiryo.ttc",
]

STAGE_W = 480
MARGIN = 10
FONT_SIZE = 15
ROW_HEIGHT = 19
TEXT_WIDTH = STAGE_W - MARGIN * 2


def _font_path():
    override = os.environ.get("PEN_CHAT_FONT")
    if override and os.path.exists(override):
        return override
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise RuntimeError("日本語フォントが見つかりません。PEN_CHAT_FONT に .ttf/.ttc のパスを指定してください")


_font = ImageFont.truetype(_font_path(), FONT_SIZE)


def _text_width(s):
    return _font.getbbox(s)[2]


def wrap(text, width=TEXT_WIDTH):
    rows = []
    for raw in text.split("\n"):
        if raw == "":
            rows.append("")
            continue
        cur = ""
        for ch in raw:
            if _text_width(cur + ch) > width and cur:
                rows.append(cur)
                cur = ch
            else:
                cur += ch
        rows.append(cur)
    return rows


def _runs(row_text, align):
    if row_text == "":
        return []
    w = min(_text_width(row_text), TEXT_WIDTH)
    img = Image.new("L", (TEXT_WIDTH, ROW_HEIGHT), 0)
    ImageDraw.Draw(img).text((0, 0), row_text, font=_font, fill=255)
    px = img.load()
    shift = MARGIN if align == "left" else STAGE_W - MARGIN - w
    out = []
    for y in range(ROW_HEIGHT):
        x = 0
        while x < TEXT_WIDTH:
            if px[x, y] > 100:
                x2 = x
                while x2 + 1 < TEXT_WIDTH and px[x2 + 1, y] > 100:
                    x2 += 1
                a = int(x + shift)
                bx = int(x2 + shift)
                if 0 <= a <= 479 and 0 <= bx <= 479:
                    out.append((y, a, bx))
                x = x2 + 1
            else:
                x += 1
    return out


def encode(text, color_index, align="left"):
    payload = []
    for row_text in wrap(text):
        runs = _runs(row_text, align)
        payload.append("%04d%d" % (len(runs), color_index))
        payload.append("".join("%02d%03d%03d" % r for r in runs))
    return "".join(payload)


def decode(payload):
    rows = []
    i = 0
    while i < len(payload):
        rc = int(payload[i:i + 4])
        color = int(payload[i + 4])
        i += 5
        runs = []
        for _ in range(rc):
            rec = payload[i:i + 8]
            runs.append((int(rec[0:2]), int(rec[2:5]), int(rec[5:8])))
            i += 8
        rows.append((color, runs))
    return rows
