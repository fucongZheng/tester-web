"""依赖注入：当前用户、鉴权"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .database import get_db
from .models import SysUser, SysRole
from .security import decode_token


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.query(SysUser).filter(SysUser.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已禁用")
    return user


def get_current_user_or_none(
    db: Session = Depends(get_db),
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        return None
    payload = decode_token(authorization[7:])
    if not payload:
        return None
    return db.query(SysUser).filter(SysUser.id == int(payload["sub"])).first()


def require_admin(user: SysUser = Depends(get_current_user)):
    code = user.role.code if user.role else ""
    if code != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_password(password: str, required: bool = True) -> str:
    pwd = (password or "").strip()
    if not pwd:
        if required:
            raise HTTPException(status_code=400, detail="密码不能为空")
        return ""
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    return pwd
