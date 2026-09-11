"""进程内限流 / 登录失败锁定（单机部署够用）。"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self):
        self._hits = defaultdict(list)
        self._lock = Lock()

    def hit(self, key: str, limit: int, window_sec: int) -> bool:
        """记一次访问。超限返回 True。"""
        now = time.time()
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < window_sec]
            if len(recent) >= limit:
                self._hits[key] = recent
                return True
            recent.append(now)
            self._hits[key] = recent
            return False


limiter = RateLimiter()

_login_fails = {}
_login_lock = Lock()
LOGIN_FAIL_LIMIT = 5
LOGIN_LOCK_SEC = 15 * 60


def client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def check_login_lock(username: str):
    now = time.time()
    key = (username or "").strip().lower()
    with _login_lock:
        rec = _login_fails.get(key)
        if rec and rec.get("locked_until", 0) > now:
            mins = int((rec["locked_until"] - now) // 60) + 1
            raise HTTPException(status_code=429, detail=f"失败次数过多，请 {mins} 分钟后再试")


def record_login_fail(username: str):
    now = time.time()
    key = (username or "").strip().lower()
    with _login_lock:
        rec = _login_fails.get(key) or {"count": 0, "locked_until": 0}
        if rec["locked_until"] > now:
            mins = int((rec["locked_until"] - now) // 60) + 1
            raise HTTPException(status_code=429, detail=f"失败次数过多，请 {mins} 分钟后再试")
        rec["count"] = rec.get("count", 0) + 1
        if rec["count"] >= LOGIN_FAIL_LIMIT:
            rec["count"] = 0
            rec["locked_until"] = now + LOGIN_LOCK_SEC
            _login_fails[key] = rec
            raise HTTPException(status_code=429, detail="失败次数过多，请 15 分钟后再试")
        _login_fails[key] = rec


def record_login_ok(username: str):
    key = (username or "").strip().lower()
    with _login_lock:
        _login_fails.pop(key, None)


def guard_public_write(request: Request, token: str):
    ip = client_ip(request)
    if limiter.hit(f"pub:{token}:{ip}", 20, 600) or limiter.hit(f"pub:{token}", 80, 600):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
