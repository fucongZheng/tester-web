"""需求管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Requirement, TestCase, Bug, Handover, ReviewRecord
from ..deps import get_current_user, require_admin
from ..helpers import (row_to_dict, paginate, gen_code, empty_to_none,
                       parse_json_list, dump_json_list, strip_id_from_json_column,
                       apply_module_filter)

router = APIRouter(prefix="/api/requirements", tags=["需求"])

REQ_STATUS = ["待开发", "开发中", "待测试", "测试中", "已验收", "已上线"]
REQ_PRIORITY = ["P0", "P1", "P2", "P3"]


@router.get("")
def list_requirements(page: int = 1, size: int = 10, keyword: str = "",
                      project_id: int = 0, version_id: int = 0, module_id: int = 0, status: str = "",
                      db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Requirement)
    if keyword:
        q = q.filter(Requirement.name.like(f"%{keyword}%") | Requirement.req_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(Requirement.project_id == project_id)
    if version_id:
        q = q.filter(Requirement.version_id == version_id)
    q = apply_module_filter(q, Requirement, module_id)
    if status:
        q = q.filter(Requirement.status == status)
    items, total = paginate(q.order_by(Requirement.id.desc()), page, size)
    data = []
    for r in items:
        d = row_to_dict(r)
        d["project_name"] = r.project.name if r.project else ""
        d["version_name"] = r.version.version_no if r.version else ""
        d["module_name"] = r.module.name if r.module else ""
        d["attachments"] = parse_json_list(r.attachments)
        data.append(d)
    return {"items": data, "total": total}


@router.get("/all")
def all_requirements(project_id: int = 0, version_id: int = 0, module_id: int = 0,
                     db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Requirement)
    if project_id:
        q = q.filter(Requirement.project_id == project_id)
    if version_id:
        q = q.filter(Requirement.version_id == version_id)
    q = apply_module_filter(q, Requirement, module_id)
    items = q.order_by(Requirement.id.desc()).all()
    return [{"id": r.id, "req_no": r.req_no, "name": r.name, "status": r.status,
             "project_id": r.project_id, "version_id": r.version_id, "module_id": r.module_id} for r in items]


@router.get("/options")
def req_options(_=Depends(get_current_user)):
    return {"status": REQ_STATUS, "priority": REQ_PRIORITY}


@router.post("")
def create_requirement(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("name") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="需求名称/项目/版本必填")
    r = Requirement(
        name=payload["name"], content=payload.get("content", ""),
        product_name=payload.get("product_name", ""),
        status=payload.get("status", "待开发"), priority=payload.get("priority", "P2"),
        project_id=payload["project_id"], version_id=payload["version_id"],
        module_id=empty_to_none(payload.get("module_id")),
        attachments=dump_json_list(payload.get("attachments")),
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
    for k in ("name", "content", "product_name", "status", "priority", "project_id", "version_id", "module_id", "attachments"):
        if k in payload:
            if k == "module_id":
                val = empty_to_none(payload[k])
            elif k == "attachments":
                val = dump_json_list(payload[k])
            else:
                val = payload[k]
            setattr(r, k, val)
    db.commit()
    return {"id": rid}


@router.delete("/{rid}")
def delete_requirement(rid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(Requirement).filter(Requirement.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="需求不存在")
    db.query(TestCase).filter(TestCase.requirement_id == rid).update(
        {TestCase.requirement_id: None}, synchronize_session=False)
    db.query(Bug).filter(Bug.requirement_id == rid).update(
        {Bug.requirement_id: None}, synchronize_session=False)
    strip_id_from_json_column(db, Handover, "requirement_ids", rid)
    strip_id_from_json_column(db, ReviewRecord, "target_ids", rid)
    db.delete(r)
    db.commit()
    return {"ok": True}
