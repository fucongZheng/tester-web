"""图形验证码：Pillow 生成、进程内存存储、一次性校验（单机部署够用）。"""
import base64
import io
import random
import os
import time
import uuid
from threading import Lock

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_TTL = 300  # 有效期 5 分钟
# 仅供自动化测试（e2e 脚本无法识图）：设置后验证码固定为该值，且接口返回 dev_code 提示
CAPTCHA_FIXED_CODE = os.getenv("CAPTCHA_FIXED_CODE", "").strip()

_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混淆的 I O 0 1
_WIDTH, _HEIGHT, _LEN = 132, 44, 4

_store = {}  # captcha_id -> (code, expire_ts)
_lock = Lock()


def _load_font(size=30):
    """优先用系统 TrueType 字体，容器 slim 镜像里退回 Pillow 内置字体。"""
    for path in (
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _random_code():
    if CAPTCHA_FIXED_CODE:
        return CAPTCHA_FIXED_CODE
    return "".join(random.choices(_CHARS, k=_LEN))


def _cleanup(now):
    for k in [k for k, (_, exp) in _store.items() if exp < now]:
        _store.pop(k, None)


def generate():
    """生成一张验证码，返回 (captcha_id, png_base64)。"""
    code = _random_code()
    img = Image.new("RGB", (_WIDTH, _HEIGHT), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    font = _load_font()
    # 每个字符：随机深色 + 上下抖动
    for i, ch in enumerate(code):
        color = random.choice([(31, 60, 90), (120, 53, 15), (25, 90, 70), (90, 30, 70), (60, 60, 110)])
        x = 10 + i * (_WIDTH - 20) // _LEN + random.randint(-2, 2)
        y = random.randint(0, _HEIGHT - 32)
        draw.text((x, y), ch, fill=color, font=font)
    # 干扰线 + 噪点
    for _ in range(4):
        color = tuple(random.randint(120, 200) for _ in range(3))
        draw.line(
            [(random.randint(0, _WIDTH), random.randint(0, _HEIGHT)),
             (random.randint(0, _WIDTH), random.randint(0, _HEIGHT))],
            fill=color, width=2,
        )
    for _ in range(60):
        xy = (random.randint(0, _WIDTH - 1), random.randint(0, _HEIGHT - 1))
        draw.point(xy, fill=tuple(random.randint(60, 220) for _ in range(3)))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    captcha_id = uuid.uuid4().hex
    with _lock:
        _cleanup(time.time())
        _store[captcha_id] = (code.upper(), time.time() + CAPTCHA_TTL)
    return captcha_id, base64.b64encode(buf.getvalue()).decode()


def verify(captcha_id, code):
    """一次性校验：无论对错都消费掉，防止重放；忽略大小写。"""
    now = time.time()
    with _lock:
        rec = _store.pop((captcha_id or "").strip(), None)
        _cleanup(now)
    if not rec or rec[1] < now:
        return False
    return rec[0] == (code or "").strip().upper()
