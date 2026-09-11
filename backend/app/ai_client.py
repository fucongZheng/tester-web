"""AI 客户端（OpenAI 兼容端点；未配置时 generate_text 返回空）"""
from urllib.parse import urlparse

from .config import settings


class AIError(Exception):
    pass


def normalize_openai_base_url(url: str) -> str:
    """把官网/文档地址收成 OpenAI SDK 能用的 base_url。"""
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    for suffix in ("/chat/completions", "/completions"):
        if u.lower().endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
    host = (urlparse(u).hostname or "").lower()
    path = (urlparse(u).path or "").rstrip("/")
    if host in ("z.ai", "www.z.ai") or (host == "api.z.ai" and path in ("", "/api")):
        return "https://api.z.ai/api/paas/v4"
    if host in ("open.bigmodel.cn", "www.open.bigmodel.cn", "bigmodel.cn", "www.bigmodel.cn"):
        if "/api/paas" not in path:
            return "https://open.bigmodel.cn/api/paas/v4"
    return u


def _resolve_ai():
    """优先用环境变量；未开则尝试 API 管理里启用的那条配置。"""
    if settings.AI_ENABLED and settings.AI_API_KEY:
        return settings.AI_BASE_URL, settings.AI_API_KEY, settings.AI_MODEL
    try:
        from .database import SessionLocal
        from .models import ApiConfig
        db = SessionLocal()
        try:
            c = db.query(ApiConfig).filter(ApiConfig.enabled == 1).first()
            if c and c.api_key:
                return c.base_url, c.api_key, c.model
        finally:
            db.close()
    except Exception:
        pass
    return "", "", ""


def chat(prompt: str, system: str = "", temperature: float = 0.3, timeout: float = 90) -> str:
    """调用 AI，失败抛 AIError。"""
    base_url, api_key, model = _resolve_ai()
    if not api_key:
        raise AIError("未配置 AI：请在「系统管理 → API管理」启用一条配置，或设置环境变量 AI_API_KEY")
    try:
        from openai import OpenAI
        kwargs = {"api_key": api_key, "timeout": timeout}
        base_url = normalize_openai_base_url(base_url)
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=msgs,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    except AIError:
        raise
    except Exception as e:
        raise AIError(f"AI 调用失败：{e}") from e


def generate_text(prompt: str, system: str = "") -> str:
    """预留：接 OpenAI 兼容端点时实现。未配置则返回空，不影响模板生成。"""
    try:
        return chat(prompt, system=system)
    except AIError as e:
        msg = str(e)
        if msg.startswith("未配置"):
            return ""
        return f"[AI 调用失败] {msg}"
