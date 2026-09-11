"""菜单管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SysMenu
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, build_menu_tree

router = APIRouter(prefix="/api/menus", tags=["菜单管理"])


@router.get("")
def list_menus(db: Session = Depends(get_db), _=Depends(get_current_user)):
    menus = db.query(SysMenu).order_by(SysMenu.sort, SysMenu.id).all()
    return build_menu_tree(menus)


@router.post("")
def create_menu(payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = SysMenu(
        parent_id=payload.get("parent_id", 0), name=payload.get("name"),
        type=payload.get("type", "menu"), path=payload.get("path", ""),
        component=payload.get("component", ""), icon=payload.get("icon", ""),
        sort=payload.get("sort", 0), permission=payload.get("permission", ""),
        visible=payload.get("visible", 1),
    )
    db.add(m)
    db.commit()
    return {"id": m.id}


@router.put("/{mid}")
def update_menu(mid: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = db.query(SysMenu).filter(SysMenu.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="菜单不存在")
    for k in ("parent_id", "name", "type", "path", "component", "icon", "sort", "permission", "visible"):
        if k in payload:
            setattr(m, k, payload[k])
    db.commit()
    return {"id": mid}


@router.delete("/{mid}")
def delete_menu(mid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(SysMenu).filter(SysMenu.parent_id == mid).first():
        raise HTTPException(status_code=400, detail="请先删除子菜单")
    m = db.query(SysMenu).filter(SysMenu.id == mid).first()
    if m:
        db.delete(m)
        db.commit()
    return {"ok": True}
