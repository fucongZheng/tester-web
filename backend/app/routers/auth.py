"""认证：登录、当前用户、菜单"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SysUser, SysMenu
from ..security import verify_password, create_access_token
from ..deps import get_current_user
from ..helpers import build_menu_tree
from ..ratelimit import check_login_lock, client_ip, limiter, record_login_fail, record_login_ok

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login")
def login(payload: dict, request: Request, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password", "")
    ip = client_ip(request)
    if limiter.hit(f"login:{ip}", 20, 600):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")
    check_login_lock(username)
    user = db.query(SysUser).filter(SysUser.username == username).first()
    if not user or not verify_password(password, user.password):
        record_login_fail(username)
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已禁用")
    record_login_ok(username)
    token = create_access_token(user.id, user.username)
    return {
        "token": token,
        "user": {
            "id": user.id, "username": user.username, "real_name": user.real_name,
            "role_id": user.role_id,
            "role_name": user.role.name if user.role else "",
            "role_code": user.role.code if user.role else "",
        },
    }


@router.get("/me")
def me(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    role = user.role
    return {
        "id": user.id, "username": user.username, "real_name": user.real_name,
        "email": user.email, "role_id": user.role_id,
        "role_name": role.name if role else "",
        "role_code": role.code if role else "",
        "menu_ids": json.loads(role.menu_ids) if role and role.menu_ids else [],
    }


@router.get("/menus")
def menus(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """返回当前角色可见的菜单树。"""
    role = user.role
    if not role:
        return []
    try:
        allowed = set(json.loads(role.menu_ids or "[]"))
    except Exception:
        allowed = set()
    all_menus = db.query(SysMenu).filter(SysMenu.visible == 1).all()
    visible = [m for m in all_menus if m.id in allowed]
    if (role.code or "") != "admin":
        visible = [m for m in visible if m.path != "/dashboard" and m.name != "看板统计"]
    return build_menu_tree(visible)
