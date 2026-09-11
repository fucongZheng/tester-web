"""项目管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Project, Version, Module, Requirement, TestCase, Bug,
                      TestReport, FlowInstance, Handover, ReviewRecord, TestSuite)
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, refuse_if_related

router = APIRouter(prefix="/api/projects", tags=["项目"])

PROJECT_TYPES = ["产业中台", "教育", "数建", "住建", "其他"]


@router.get("")
def list_projects(page: int = 1, size: int = 10, keyword: str = "", type: str = "",
                  db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Project)
    if keyword:
        q = q.filter(Project.name.like(f"%{keyword}%"))
    if type:
        q = q.filter(Project.type == type)
    items, total = paginate(q.order_by(Project.id.desc()), page, size)
    return {"items": [row_to_dict(i) for i in items], "total": total}


@router.get("/all")
def all_projects(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Project).order_by(Project.id.desc()).all()
    return [row_to_dict(i) for i in items]


@router.get("/types")
def project_types(_=Depends(get_current_user)):
    return PROJECT_TYPES


@router.get("/{pid}")
def get_project(pid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return row_to_dict(p)


@router.post("")
def create_project(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("name"):
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    p = Project(
        name=payload["name"], type=payload.get("type", "其他"),
        owner=payload.get("owner", ""), members=payload.get("members", ""),
    )
    db.add(p)
    db.commit()
    return {"id": p.id}


@router.put("/{pid}")
def update_project(pid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    for k in ("name", "type", "owner", "members"):
        if k in payload:
            setattr(p, k, payload[k])
    db.commit()
    return {"id": pid}


@router.delete("/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    refuse_if_related(db, [
        (Version, {"project_id": pid}, "版本"),
        (Module, {"project_id": pid}, "模块"),
        (Requirement, {"project_id": pid}, "需求"),
        (TestCase, {"project_id": pid}, "用例"),
        (Bug, {"project_id": pid}, "BUG"),
        (TestSuite, {"project_id": pid}, "测试套件"),
        (Handover, {"project_id": pid}, "提测单"),
        (ReviewRecord, {"project_id": pid}, "评审记录"),
        (TestReport, {"project_id": pid}, "测试报告"),
        (FlowInstance, {"project_id": pid}, "测试流程"),
    ])
    db.delete(p)
    db.commit()
    return {"ok": True}
