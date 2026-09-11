"""模块管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Module, Requirement, TestCase, Bug, Handover, TestSuite, ReviewRecord, LaunchRequest
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict

router = APIRouter(prefix="/api/modules", tags=["模块"])


def _tree(modules, parent_id=0):
    result = []
    for m in modules:
        if m.parent_id == parent_id:
            d = row_to_dict(m)
            d["project_name"] = m.project.name if m.project else ""
            d["children"] = _tree(modules, m.id)
            result.append(d)
    return result


@router.get("")
def list_modules(project_id: int = 0, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Module)
    if project_id:
        q = q.filter(Module.project_id == project_id)
    modules = q.order_by(Module.sort, Module.id).all()
    return _tree(modules)


@router.get("/all")
def all_modules(project_id: int = 0, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Module)
    if project_id:
        q = q.filter(Module.project_id == project_id)
    return [row_to_dict(m) for m in q.order_by(Module.sort, Module.id).all()]


@router.post("")
def create_module(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("name") or not payload.get("project_id"):
        raise HTTPException(status_code=400, detail="模块名称和所属项目必填")
    m = Module(
        name=payload["name"], parent_id=payload.get("parent_id", 0),
        sort=payload.get("sort", 0), remark=payload.get("remark", ""),
        project_id=payload["project_id"],
    )
    db.add(m)
    db.commit()
    return {"id": m.id}


@router.put("/{mid}")
def update_module(mid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    m = db.query(Module).filter(Module.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="模块不存在")
    for k in ("name", "parent_id", "sort", "remark", "project_id"):
        if k in payload:
            setattr(m, k, payload[k])
    db.commit()
    return {"id": mid}


@router.delete("/{mid}")
def delete_module(mid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Module).filter(Module.parent_id == mid).first():
        raise HTTPException(status_code=400, detail="请先删除子模块")
    m = db.query(Module).filter(Module.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="模块不存在")
    db.query(Requirement).filter(Requirement.module_id == mid).update(
        {Requirement.module_id: None}, synchronize_session=False)
    db.query(TestCase).filter(TestCase.module_id == mid).update(
        {TestCase.module_id: None}, synchronize_session=False)
    db.query(Bug).filter(Bug.module_id == mid).update(
        {Bug.module_id: None}, synchronize_session=False)
    db.query(Handover).filter(Handover.module_id == mid).update(
        {Handover.module_id: None}, synchronize_session=False)
    db.query(TestSuite).filter(TestSuite.module_id == mid).update(
        {TestSuite.module_id: None}, synchronize_session=False)
    db.query(ReviewRecord).filter(ReviewRecord.module_id == mid).update(
        {ReviewRecord.module_id: None}, synchronize_session=False)
    db.query(LaunchRequest).filter(LaunchRequest.module_id == mid).update(
        {LaunchRequest.module_id: None}, synchronize_session=False)
    db.delete(m)
    db.commit()
    return {"ok": True}
