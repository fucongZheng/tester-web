"""角色管理"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SysRole
from ..deps import get_current_user
from ..helpers import row_to_dict, paginate

router = APIRouter(prefix="/api/roles", tags=["角色管理"])


@router.get("")
def list_roles(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(SysRole).order_by(SysRole.id).all()
    data = []
    for r in items:
        d = row_to_dict(r)
        try:
            d["menu_ids"] = json.loads(r.menu_ids or "[]")
        except Exception:
            d["menu_ids"] = []
        data.append(d)
    return {"items": data, "total": len(data)}


@router.post("")
def create_role(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(SysRole).filter(SysRole.code == payload.get("code")).first():
        raise HTTPException(status_code=400, detail="角色编码已存在")
    r = SysRole(
        name=payload.get("name"), code=payload.get("code"),
        description=payload.get("description", ""),
        menu_ids=json.dumps(payload.get("menu_ids", [])),
        status=payload.get("status", 1),
    )
    db.add(r)
    db.commit()
    return {"id": r.id}


@router.put("/{rid}")
def update_role(rid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(SysRole).filter(SysRole.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="角色不存在")
    for k in ("name", "description", "status"):
        if k in payload:
            setattr(r, k, payload[k])
    if "menu_ids" in payload:
        r.menu_ids = json.dumps(payload["menu_ids"])
    db.commit()
    return {"id": rid}


@router.delete("/{rid}")
def delete_role(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(SysRole).filter(SysRole.id == rid).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}
