"""API 管理：OpenAI / 中转站等配置"""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ApiConfig
from ..deps import require_admin
from ..helpers import row_to_dict
from ..ai_client import normalize_openai_base_url

router = APIRouter(prefix="/api/apiconfigs", tags=["API管理"])

PROVIDERS = ["openai", "azure", "z.ai", "中转站", "custom"]


def _safe(c: ApiConfig):
    d = row_to_dict(c)
    key = d.get("api_key") or ""
    d["api_key_masked"] = (key[:4] + "****" + key[-4:]) if len(key) > 8 else ("****" if key else "")
    d.pop("api_key", None)
    return d


@router.get("")
def list_configs(db: Session = Depends(get_db), _=Depends(require_admin)):
    items = db.query(ApiConfig).order_by(ApiConfig.id.desc()).all()
    return {"items": [_safe(c) for c in items], "total": len(items)}


@router.get("/options")
def options(_=Depends(require_admin)):
    return {"providers": PROVIDERS}


@router.post("")
def create_config(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    if not payload.get("name"):
        raise HTTPException(status_code=400, detail="名称必填")
    enabled = 1 if payload.get("enabled") else 0
    if enabled:
        db.query(ApiConfig).update({ApiConfig.enabled: 0})
    c = ApiConfig(
        name=payload["name"],
        provider=payload.get("provider", "openai"),
        base_url=payload.get("base_url", ""),
        api_key=payload.get("api_key", ""),
        model=payload.get("model", ""),
        enabled=enabled,
        remark=payload.get("remark", ""),
    )
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.put("/{cid}")
def update_config(cid: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(ApiConfig).filter(ApiConfig.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    for k in ("name", "provider", "base_url", "model", "remark"):
        if k in payload:
            setattr(c, k, payload[k])
    if payload.get("api_key"):
        c.api_key = payload["api_key"]
    if "enabled" in payload:
        c.enabled = 1 if payload.get("enabled") else 0
        if c.enabled:
            db.query(ApiConfig).filter(ApiConfig.id != cid).update({ApiConfig.enabled: 0})
    db.commit()
    return {"id": cid}


@router.post("/test")
def test_config(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    """用表单或已保存配置打一次极短对话，验证 Key / Base URL / 模型。"""
    base_url = (payload.get("base_url") or "").strip()
    api_key = (payload.get("api_key") or "").strip()
    model = (payload.get("model") or "").strip()
    cid = payload.get("id")
    if cid and not api_key:
        c = db.query(ApiConfig).filter(ApiConfig.id == int(cid)).first()
        if not c:
            raise HTTPException(status_code=404, detail="配置不存在")
        api_key = c.api_key or ""
        base_url = base_url or (c.base_url or "")
        model = model or (c.model or "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请先填写 API Key")
    resolved = normalize_openai_base_url(base_url)
    started = time.time()
    try:
        from openai import OpenAI
        kwargs = {"api_key": api_key, "timeout": 20}
        if resolved:
            kwargs["base_url"] = resolved
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            temperature=0,
        )
        reply = ((resp.choices[0].message.content or "") if resp.choices else "").strip()
        used = getattr(resp, "model", None) or model or ""
        ms = int((time.time() - started) * 1000)
        return {
            "ok": True,
            "message": "连接成功" + (f"：{reply}" if reply else ""),
            "latency_ms": ms,
            "model": used,
            "base_url": resolved or "(OpenAI 官方默认)",
        }
    except Exception as e:
        ms = int((time.time() - started) * 1000)
        raise HTTPException(status_code=400, detail=f"连接失败（{ms}ms）：{e}") from e


@router.delete("/{cid}")
def delete_config(cid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(ApiConfig).filter(ApiConfig.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}
