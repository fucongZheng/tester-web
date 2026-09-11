"""用户管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SysUser, Handover
from ..security import hash_password
from ..deps import get_current_user, require_admin, require_password
from ..helpers import row_to_dict, paginate

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("/all")
def all_users(db: Session = Depends(get_db), _: SysUser = Depends(get_current_user)):
    items = db.query(SysUser).filter(SysUser.status == 1).order_by(SysUser.id).all()
    return [{"id": u.id, "username": u.username, "real_name": u.real_name or u.username,
             "role_name": u.role.name if u.role else ""} for u in items]


@router.get("")
def list_users(page: int = 1, size: int = 10, keyword: str = "",
               db: Session = Depends(get_db), _: SysUser = Depends(get_current_user)):
    q = db.query(SysUser)
    if keyword:
        q = q.filter(SysUser.username.like(f"%{keyword}%") | SysUser.real_name.like(f"%{keyword}%"))
    items, total = paginate(q.order_by(SysUser.id), page, size)
    data = []
    for u in items:
        d = row_to_dict(u)
        d.pop("password", None)
        d["role_name"] = u.role.name if u.role else ""
        data.append(d)
    return {"items": data, "total": total}


@router.post("")
def create_user(payload: dict, db: Session = Depends(get_db), _: SysUser = Depends(require_admin)):
    if db.query(SysUser).filter(SysUser.username == payload.get("username")).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = SysUser(
        username=payload.get("username"),
        password=hash_password(require_password(payload.get("password"), required=True)),
        real_name=payload.get("real_name", ""),
        email=payload.get("email", ""),
        phone=payload.get("phone", ""),
        role_id=payload.get("role_id"),
        status=payload.get("status", 1),
    )
    db.add(u)
    db.commit()
    return {"id": u.id}


@router.put("/{uid}")
def update_user(uid: int, payload: dict, db: Session = Depends(get_db), _: SysUser = Depends(require_admin)):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    for k in ("real_name", "email", "phone", "role_id", "status"):
        if k in payload:
            setattr(u, k, payload[k])
    if payload.get("password"):
        pwd = require_password(payload["password"], required=False)
        if pwd:
            u.password = hash_password(pwd)
    db.commit()
    return {"id": uid}


@router.delete("/{uid}")
def delete_user(uid: int, db: Session = Depends(get_db), cur: SysUser = Depends(require_admin)):
    if uid == cur.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.query(Handover).filter(Handover.tester_id == uid).update(
        {Handover.tester_id: None}, synchronize_session=False)
    db.delete(u)
    db.commit()
    return {"ok": True}
