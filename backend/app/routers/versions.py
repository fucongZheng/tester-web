"""版本管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Version, Requirement, TestCase, Bug, TestReport,
                      FlowInstance, Handover, ReviewRecord, TestSuite, LaunchRequest)
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, overtime_text, refuse_if_related

router = APIRouter(prefix="/api/versions", tags=["版本"])

VERSION_STATUS = ["规划中", "开发中", "测试中", "已上线", "已归档"]


@router.get("")
def list_versions(page: int = 1, size: int = 10, keyword: str = "", project_id: int = 0,
                  db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Version)
    if keyword:
        q = q.filter(Version.name.like(f"%{keyword}%") | Version.version_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(Version.project_id == project_id)
    items, total = paginate(q.order_by(Version.id.desc()), page, size)
    data = []
    for v in items:
        d = row_to_dict(v)
        d["project_name"] = v.project.name if v.project else ""
        d["overtime"] = overtime_text(v.launch_date, v.status)
        data.append(d)
    return {"items": data, "total": total}


@router.get("/all")
def all_versions(project_id: int = 0, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Version)
    if project_id:
        q = q.filter(Version.project_id == project_id)
    items = q.order_by(Version.id.desc()).all()
    return [{"id": v.id, "version_no": v.version_no, "name": v.name,
             "project_id": v.project_id, "status": v.status} for v in items]


@router.get("/statuses")
def version_statuses(_=Depends(get_current_user)):
    return VERSION_STATUS


@router.post("")
def create_version(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("version_no") or not payload.get("project_id"):
        raise HTTPException(status_code=400, detail="版本号和所属项目必填")
    if not payload.get("launch_date"):
        raise HTTPException(status_code=400, detail="上线时间必填")
    minutes = (payload.get("review_minutes") or "").strip()
    if not minutes:
        raise HTTPException(status_code=400, detail="需求评审纪要必填")
    v = Version(
        version_no=payload["version_no"], name=payload.get("name", ""),
        start_date=payload.get("start_date", ""), launch_date=payload.get("launch_date", ""),
        status=payload.get("status", "规划中"), remark=payload.get("remark", ""),
        review_minutes=minutes,
        project_id=payload["project_id"],
    )
    db.add(v)
    db.commit()
    return {"id": v.id}


@router.put("/{vid}")
def update_version(vid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    v = db.query(Version).filter(Version.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    if "launch_date" in payload and not payload.get("launch_date"):
        raise HTTPException(status_code=400, detail="上线时间必填")
    if "review_minutes" in payload and not (payload.get("review_minutes") or "").strip():
        raise HTTPException(status_code=400, detail="需求评审纪要必填")
    for k in ("version_no", "name", "start_date", "launch_date", "status", "remark",
              "review_minutes", "project_id"):
        if k in payload:
            setattr(v, k, payload[k])
    db.commit()
    return {"id": vid}


@router.delete("/{vid}")
def delete_version(vid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    v = db.query(Version).filter(Version.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    refuse_if_related(db, [
        (Requirement, {"version_id": vid}, "需求"),
        (TestCase, {"version_id": vid}, "用例"),
        (Bug, {"version_id": vid}, "BUG"),
        (TestSuite, {"version_id": vid}, "测试套件"),
        (Handover, {"version_id": vid}, "提测单"),
        (ReviewRecord, {"version_id": vid}, "评审记录"),
        (TestReport, {"version_id": vid}, "测试报告"),
        (FlowInstance, {"version_id": vid}, "测试流程"),
        (LaunchRequest, {"version_id": vid}, "上线申请"),
    ])
    db.delete(v)
    db.commit()
    return {"ok": True}


@router.get("/{vid}/review-minutes-draft")
def review_minutes_draft(vid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """用该版本下已通过的需求评审记录拼一份纪要草稿。"""
    v = db.query(Version).filter(Version.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    rows = db.query(ReviewRecord).filter(
        ReviewRecord.version_id == vid,
        ReviewRecord.review_type == "需求评审",
        ReviewRecord.result.in_(["通过", "有条件通过"]),
    ).order_by(ReviewRecord.id).all()
    if not rows:
        raise HTTPException(status_code=400, detail="该版本还没有通过的需求评审记录，请先在评审记录里录入")
    parts = []
    for r in rows:
        date = r.review_date or (r.created_at.strftime("%Y-%m-%d") if r.created_at else "")
        header = f"【{r.review_no or ''} {r.title}】{date} 主审：{r.reviewer or '-'} 结论：{r.result}"
        body = (r.comment or "").strip() or "（无评审意见）"
        parts.append(header + "\n" + body)
    return {"review_minutes": "\n\n".join(parts)}
