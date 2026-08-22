"""AI 客户端（本期留桩，预留 OpenAI 兼容接口）"""
from .config import settings


def generate_text(prompt: str, system: str = "") -> str:
    """预留：接 OpenAI 兼容端点时实现。当前返回空，表示未启用润色。"""
    if not settings.AI_ENABLED:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(base_url=settings.AI_BASE_URL, api_key=settings.AI_API_KEY)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model=settings.AI_MODEL, messages=msgs)
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"[AI 调用失败] {e}"
