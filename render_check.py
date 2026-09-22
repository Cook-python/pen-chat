import json
import sys

from PIL import Image, ImageDraw

import pen_text

STAGE_W = 480
STAGE_H = 360
ROW_HEIGHT = 19
TOP_Y = 170

PALETTE = [0x202830, 0x7fd8ff, 0xffffff, 0xffd23f, 0x9affa0,
           0xff9ab0, 0xc0c0c0, 0x808080, 0x404040, 0x000000]


def hexcolor(v):
    return (v >> 16 & 0xff, v >> 8 & 0xff, v & 0xff)


def main():
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        recv_values = json.load(f)

    img = Image.new("RGB", (STAGE_W, STAGE_H), hexcolor(PALETTE[0]))
    draw = ImageDraw.Draw(img)

    row_index = 0
    for value in recv_values:
        payload = value[5:]
        rows = pen_text.decode(payload)
        for color_index, runs in rows:
            y_top = TOP_Y + row_index * ROW_HEIGHT
            color = hexcolor(PALETTE[color_index])
            for y, x1, x2 in runs:
                draw.line((x1, y_top + y, x2, y_top + y), fill=color)
            row_index += 1

    img.save(sys.argv[2])
    print("rows drawn:", row_index)


if __name__ == "__main__":
    main()
