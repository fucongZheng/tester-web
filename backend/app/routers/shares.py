"""BUG 分享：登录侧创建链接；公开侧免登录查看/改状态/加备注"""
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Bug, BugShare, SysUser
from ..deps import get_current_user
from ..helpers import row_to_dict
from ..ratelimit import guard_public_write

SHARE_TTL_DAYS = 7

router = APIRouter(prefix="/api/shares", tags=["BUG分享"])

PUBLIC_STATUSES = ["待处理", "处理中", "已修复未发版", "已修复已发版", "不是BUG", "测试验证通过关闭"]


def _parse_ids(raw):
    if isinstance(raw, list):
        return [int(x) for x in raw if x]
    if not raw:
        return []
    try:
        return [int(x) for x in json.loads(raw)]
    except Exception:
        return []


def _share_or_404(db, token: str) -> BugShare:
    s = db.query(BugShare).filter(BugShare.token == token).first()
    if not s:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    if s.expires_at and s.expires_at < datetime.now():
        raise HTTPException(status_code=410, detail="分享链接已过期，请联系测试重新分享")
    return s


def _bug_public(b: Bug):
    d = row_to_dict(b)
    d["project_name"] = b.project.name if b.project else ""
    d["version_name"] = b.version.version_no if b.version else ""
    d["module_name"] = b.module.name if b.module else ""
    d["requirement_name"] = b.requirement.name if b.requirement else ""
    d["case_title"] = b.case.title if b.case else ""
    return d


@router.post("")
def create_share(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    ids = _parse_ids(payload.get("bug_ids") or [])
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要分享的 BUG")
    bugs = db.query(Bug).filter(Bug.id.in_(ids)).all()
    if not bugs:
        raise HTTPException(status_code=400, detail="所选 BUG 不存在")
    token = secrets.token_urlsafe(24)
    title = payload.get("title") or f"BUG分享（{len(bugs)}条）"
    s = BugShare(
        token=token, title=title, bug_ids=json.dumps([b.id for b in bugs]),
        created_by=cur.real_name or cur.username,
        expires_at=datetime.now() + timedelta(days=SHARE_TTL_DAYS),
    )
    db.add(s)
    db.commit()
    return {
        "token": token, "title": title, "count": len(bugs),
        "expires_at": s.expires_at.strftime("%Y-%m-%d %H:%M:%S") if s.expires_at else "",
    }


@router.get("/public/{token}")
def public_share(token: str, db: Session = Depends(get_db)):
    s = _share_or_404(db, token)
    ids = _parse_ids(s.bug_ids)
    bugs = db.query(Bug).filter(Bug.id.in_(ids)).order_by(Bug.id.desc()).all() if ids else []
    users = db.query(SysUser).filter(SysUser.status == 1).order_by(SysUser.id).all()
    return {
        "title": s.title,
        "created_by": s.created_by,
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
        "expires_at": s.expires_at.strftime("%Y-%m-%d %H:%M:%S") if s.expires_at else "",
        "statuses": PUBLIC_STATUSES,
        "users": [{"id": u.id, "real_name": u.real_name or u.username} for u in users],
        "items": [_bug_public(b) for b in bugs],
    }


@router.put("/public/{token}/bugs/{bid}")
def public_update_bug(token: str, bid: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    s = _share_or_404(db, token)
    guard_public_write(request, token)
    ids = set(_parse_ids(s.bug_ids))
    if bid not in ids:
        raise HTTPException(status_code=403, detail="该 BUG 不在本次分享范围内")
    b = db.query(Bug).filter(Bug.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="BUG不存在")

    extra = (payload.get("note") or "").strip()
    if extra:
        if len(extra) > 500:
            raise HTTPException(status_code=400, detail="备注不能超过 500 字")
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"[{stamp} 分享页] {extra}"
        b.remark = (b.remark + "\n" + line) if b.remark else line

    if "status" in payload and payload.get("status"):
        status = payload["status"]
        if status not in PUBLIC_STATUSES:
            raise HTTPException(status_code=400, detail="非法状态")
        b.status = status
        if status == "测试验证通过关闭" and not b.closed_at:
            b.closed_at = datetime.now()

    if "fixer" in payload:
        b.fixer = payload.get("fixer") or ""

    db.commit()
    return _bug_public(b)
