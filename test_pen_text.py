import pen_text


def independent_decode(payload):
    rows = []
    i = 0
    n = len(payload)
    while i < n:
        rc_field = payload[i:i + 4]
        color_field = payload[i + 4:i + 5]
        assert len(rc_field) == 4 and rc_field.isdigit(), rc_field
        assert len(color_field) == 1 and color_field.isdigit(), color_field
        rc = int(rc_field)
        color = int(color_field)
        i += 5
        runs = []
        for _ in range(rc):
            rec = payload[i:i + 8]
            assert len(rec) == 8 and rec.isdigit(), rec
            y = int(rec[0:2])
            x1 = int(rec[2:5])
            x2 = int(rec[5:8])
            assert 0 <= y <= 18, y
            assert 0 <= x1 <= 479, x1
            assert 0 <= x2 <= 479, x2
            runs.append((y, x1, x2))
            i += 8
        rows.append((color, runs))
    return rows, i


def expected_rows(text, color, align):
    out = []
    for row_text in pen_text.wrap(text):
        out.append((color, pen_text._runs(row_text, align)))
    return out


def check(text, color, align):
    payload = pen_text.encode(text, color, align)
    decoded_rows, consumed = independent_decode(payload)
    assert consumed == len(payload), (consumed, len(payload))

    want_rows = expected_rows(text, color, align)
    assert decoded_rows == want_rows, (decoded_rows, want_rows)

    expected_len = sum(5 + len(runs) * 8 for _, runs in want_rows)
    assert len(payload) == expected_len, (len(payload), expected_len)


CASES = [
    ("こんにちは", 1, "right"),
    ("こんにちは", 2, "left"),
    ("hello", 1, "right"),
    ("", 1, "left"),
    ("あ\nい\nう", 2, "left"),
    ("長い文章をたくさん書いて折り返しが複数回起きるかどうかをここで確認するための文です。" * 2, 2, "left"),
    ("Mixed 日本語 and English 123", 1, "right"),
    ("　", 2, "left"),
]


def main():
    for text, color, align in CASES:
        check(text, color, align)
        print("OK", repr(text[:20]), color, align)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
