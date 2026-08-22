"""测试用例管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestCase
from ..deps import get_current_user
from ..helpers import row_to_dict, paginate, gen_code

router = APIRouter(prefix="/api/cases", tags=["测试用例"])

CASE_TYPES = ["功能", "接口", "UI", "性能", "回归"]
CASE_PRIORITY = ["P0", "P1", "P2", "P3"]


@router.get("")
def list_cases(page: int = 1, size: int = 10, keyword: str = "",
               project_id: int = 0, version_id: int = 0, module_id: int = 0,
               requirement_id: int = 0, case_type: str = "",
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestCase)
    if keyword:
        q = q.filter(TestCase.title.like(f"%{keyword}%") | TestCase.case_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(TestCase.project_id == project_id)
    if version_id:
        q = q.filter(TestCase.version_id == version_id)
    if module_id:
        q = q.filter(TestCase.module_id == module_id)
    if requirement_id:
        q = q.filter(TestCase.requirement_id == requirement_id)
    if case_type:
        q = q.filter(TestCase.case_type == case_type)
    items, total = paginate(q.order_by(TestCase.id.desc()), page, size)
    data = []
    for c in items:
        d = row_to_dict(c)
        d["project_name"] = c.project.name if c.project else ""
        d["version_name"] = c.version.version_no if c.version else ""
        d["module_name"] = c.module.name if c.module else ""
        d["requirement_name"] = c.requirement.name if c.requirement else ""
        data.append(d)
    return {"items": data, "total": total}


@router.get("/options")
def case_options():
    return {"case_type": CASE_TYPES, "priority": CASE_PRIORITY}


@router.post("")
def create_case(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("title") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="标题/项目/版本必填")
    c = TestCase(
        title=payload["title"], precondition=payload.get("precondition", ""),
        steps=payload.get("steps", ""), expected=payload.get("expected", ""),
        case_type=payload.get("case_type", "功能"), priority=payload.get("priority", "P2"),
        status=payload.get("status", 1), project_id=payload["project_id"],
        version_id=payload["version_id"], module_id=payload.get("module_id"),
        requirement_id=payload.get("requirement_id"), remark=payload.get("remark", ""),
    )
    db.add(c)
    db.flush()
    c.case_no = gen_code("TC", c.id)
    db.commit()
    return {"id": c.id, "case_no": c.case_no}


@router.put("/{cid}")
def update_case(cid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(TestCase).filter(TestCase.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="用例不存在")
    for k in ("title", "precondition", "steps", "expected", "case_type", "priority",
              "status", "project_id", "version_id", "module_id", "requirement_id", "remark"):
        if k in payload:
            setattr(c, k, payload[k])
    db.commit()
    return {"id": cid}


@router.delete("/{cid}")
def delete_case(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(TestCase).filter(TestCase.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}
