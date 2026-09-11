"""上线申请"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import LaunchRequest
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, empty_to_none

router = APIRouter(prefix="/api/launches", tags=["上线申请"])

LAUNCH_STATUS = ["待审批", "已通过", "已驳回"]


def _to_dict(r: LaunchRequest):
    d = row_to_dict(r)
    d["project_name"] = r.project.name if r.project else ""
    d["version_name"] = r.version.version_no if r.version else ""
    d["module_name"] = r.module.name if r.module else ""
    return d


@router.get("")
def list_launches(page: int = 1, size: int = 10, keyword: str = "",
                  project_id: int = 0, version_id: int = 0, module_id: int = 0,
                  status: str = "",
                  db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(LaunchRequest)
    if keyword:
        q = q.filter(LaunchRequest.title.like(f"%{keyword}%") | LaunchRequest.launch_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(LaunchRequest.project_id == project_id)
    if version_id:
        q = q.filter(LaunchRequest.version_id == version_id)
    if module_id:
        q = q.filter(LaunchRequest.module_id == module_id)
    if status:
        q = q.filter(LaunchRequest.status == status)
    items, total = paginate(q.order_by(LaunchRequest.id.desc()), page, size)
    return {"items": [_to_dict(r) for r in items], "total": total}


@router.get("/options")
def launch_options(_=Depends(get_current_user)):
    return {"status": LAUNCH_STATUS}


@router.post("")
def create_launch(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    if not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="项目和版本必选")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="上线标题必填")
    r = LaunchRequest(
        title=title,
        project_id=payload["project_id"],
        version_id=payload["version_id"],
        module_id=empty_to_none(payload.get("module_id")),
        plan_date=payload.get("plan_date", ""),
        content=payload.get("content", ""),
        applicant=payload.get("applicant") or (cur.real_name or cur.username),
        reviewer=payload.get("reviewer", ""),
        status=payload.get("status") or "待审批",
        remark=payload.get("remark", ""),
    )
    db.add(r)
    db.flush()
    r.launch_no = gen_code("LN", r.id)
    db.commit()
    return {"id": r.id, "launch_no": r.launch_no}


@router.put("/{lid}")
def update_launch(lid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(LaunchRequest).filter(LaunchRequest.id == lid).first()
    if not r:
        raise HTTPException(status_code=404, detail="上线申请不存在")
    if "status" in payload and payload["status"] not in LAUNCH_STATUS:
        raise HTTPException(status_code=400, detail="状态非法")
    for k in ("title", "project_id", "version_id", "plan_date", "content",
              "applicant", "reviewer", "status", "remark"):
        if k in payload:
            setattr(r, k, payload[k])
    if "module_id" in payload:
        r.module_id = empty_to_none(payload.get("module_id"))
    db.commit()
    return {"id": lid}


@router.delete("/{lid}")
def delete_launch(lid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(LaunchRequest).filter(LaunchRequest.id == lid).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}
