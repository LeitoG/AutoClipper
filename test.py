import json

video_w, video_h = 1920, 1080

def safe_crop(c):
    raw_x = c.get('x', 0)
    raw_y = c.get('y', 0)
    raw_w = c.get('w', 1920)
    raw_h = c.get('h', 1080)
    print(f"Input: {raw_x}, {raw_y}, {raw_w}, {raw_h}")
    x = max(0, int(raw_x * (video_w / 1920.0)))
    y = max(0, int(raw_y * (video_h / 1080.0)))
    w = max(2, int(raw_w * (video_w / 1920.0)))
    h = max(2, int(raw_h * (video_h / 1080.0)))
    print(f"Scaled: {x}, {y}, {w}, {h}")
    x -= x % 2
    y -= y % 2
    w -= w % 2
    h -= h % 2
    if w < 2: w = 2
    if h < 2: h = 2
    if x >= video_w: x = video_w - 2
    if y >= video_h: y = video_h - 2
    if x + w > video_w: w = video_w - x
    if y + h > video_h: h = video_h - y
    w -= w % 2
    h -= h % 2
    if w < 2: w = 2
    if h < 2: h = 2
    print(f"Final: {w}, {h}, {x}, {y}")
    return w, h, x, y

print(safe_crop({'x': 1400, 'y': 0, 'w': 400, 'h': 400}))
