"""BUG 管理"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Bug, BugShare
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, empty_to_none, strip_id_from_json_column, apply_module_filter

router = APIRouter(prefix="/api/bugs", tags=["BUG"])

SEVERITIES = ["致命", "严重", "一般", "轻微", "建议"]
STATUSES = ["待处理", "处理中", "已修复未发版", "已修复已发版", "不是BUG", "测试验证通过关闭"]
STAGES = ["第一轮测试", "第二轮测试", "回归测试", "线上溢出", "产品提出"]


@router.get("")
def list_bugs(page: int = 1, size: int = 10, keyword: str = "",
              project_id: int = 0, version_id: int = 0, module_id: int = 0,
              severity: str = "", status: str = "", found_stage: str = "",
              assignee: str = "", fixer: str = "",
              db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Bug)
    if keyword:
        q = q.filter(Bug.title.like(f"%{keyword}%") | Bug.bug_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    if severity:
        q = q.filter(Bug.severity == severity)
    if status:
        q = q.filter(Bug.status == status)
    if found_stage:
        q = q.filter(Bug.found_stage == found_stage)
    if assignee:
        q = q.filter(Bug.assignee == assignee)
    if fixer:
        q = q.filter(Bug.fixer == fixer)
    items, total = paginate(q.order_by(Bug.id.desc()), page, size)
    data = []
    for b in items:
        d = row_to_dict(b)
        d["project_name"] = b.project.name if b.project else ""
        d["version_name"] = b.version.version_no if b.version else ""
        d["module_name"] = b.module.name if b.module else ""
        d["requirement_name"] = b.requirement.name if b.requirement else ""
        d["case_title"] = b.case.title if b.case else ""
        data.append(d)
    return {"items": data, "total": total}


@router.get("/options")
def bug_options(_=Depends(get_current_user)):
    return {"severity": SEVERITIES, "status": STATUSES, "stage": STAGES}


@router.post("")
def create_bug(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    if not payload.get("title") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="标题/项目/版本必填")
    b = Bug(
        title=payload["title"], severity=payload.get("severity", "一般"),
        status=payload.get("status", "待处理"), project_id=payload["project_id"],
        version_id=payload["version_id"], module_id=empty_to_none(payload.get("module_id")),
        requirement_id=empty_to_none(payload.get("requirement_id")),
        case_id=empty_to_none(payload.get("case_id")),
        found_stage=payload.get("found_stage", "第一轮测试"),
        submitter=payload.get("submitter") or cur.real_name or cur.username,
        assignee=payload.get("assignee", ""), fixer=payload.get("fixer", ""),
        steps=payload.get("steps", ""),
        remark=payload.get("remark", ""),
    )
    db.add(b)
    db.flush()
    b.bug_no = gen_code("BUG", b.id)
    db.commit()
    return {"id": b.id, "bug_no": b.bug_no}


@router.put("/{bid}")
def update_bug(bid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    b = db.query(Bug).filter(Bug.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="BUG不存在")
    for k in ("title", "severity", "status", "project_id", "version_id", "module_id",
              "requirement_id", "case_id", "found_stage", "submitter", "assignee",
              "fixer", "steps", "remark"):
        if k in payload:
            val = empty_to_none(payload[k]) if k in ("module_id", "requirement_id", "case_id") else payload[k]
            setattr(b, k, val)
    # 状态流转到“测试验证通过关闭”时记录关闭时间
    if payload.get("status") == "测试验证通过关闭" and not b.closed_at:
        b.closed_at = datetime.now()
    db.commit()
    return {"id": bid}


@router.delete("/{bid}")
def delete_bug(bid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    b = db.query(Bug).filter(Bug.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="BUG不存在")
    strip_id_from_json_column(db, BugShare, "bug_ids", bid)
    db.delete(b)
    db.commit()
    return {"ok": True}
