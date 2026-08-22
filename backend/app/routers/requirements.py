"""需求管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Requirement
from ..deps import get_current_user
from ..helpers import row_to_dict, paginate, gen_code

router = APIRouter(prefix="/api/requirements", tags=["需求"])

REQ_STATUS = ["待开发", "开发中", "待测试", "测试中", "已验收", "已上线"]
REQ_PRIORITY = ["P0", "P1", "P2", "P3"]


@router.get("")
def list_requirements(page: int = 1, size: int = 10, keyword: str = "",
                      project_id: int = 0, version_id: int = 0, status: str = "",
                      db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Requirement)
    if keyword:
        q = q.filter(Requirement.name.like(f"%{keyword}%") | Requirement.req_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(Requirement.project_id == project_id)
    if version_id:
        q = q.filter(Requirement.version_id == version_id)
    if status:
        q = q.filter(Requirement.status == status)
    items, total = paginate(q.order_by(Requirement.id.desc()), page, size)
    data = []
    for r in items:
        d = row_to_dict(r)
        d["project_name"] = r.project.name if r.project else ""
        d["version_name"] = r.version.version_no if r.version else ""
        d["module_name"] = r.module.name if r.module else ""
        data.append(d)
    return {"items": data, "total": total}


@router.get("/options")
def req_options():
    return {"status": REQ_STATUS, "priority": REQ_PRIORITY}


@router.post("")
def create_requirement(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("name") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="需求名称/项目/版本必填")
    r = Requirement(
        name=payload["name"], product_name=payload.get("product_name", ""),
        status=payload.get("status", "待开发"), priority=payload.get("priority", "P2"),
        project_id=payload["project_id"], version_id=payload["version_id"],
        module_id=payload.get("module_id"),
    )
    db.add(r)
    db.flush()
    r.req_no = gen_code("REQ", r.id)
    db.commit()
    return {"id": r.id, "req_no": r.req_no}


@router.put("/{rid}")
def update_requirement(rid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(Requirement).filter(Requirement.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="需求不存在")
    for k in ("name", "product_name", "status", "priority", "project_id", "version_id", "module_id"):
        if k in payload:
            setattr(r, k, payload[k])
    db.commit()
    return {"id": rid}


@router.delete("/{rid}")
def delete_requirement(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(Requirement).filter(Requirement.id == rid).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}
