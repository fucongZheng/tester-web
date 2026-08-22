"""版本管理"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Version
from ..deps import get_current_user
from ..helpers import row_to_dict, paginate

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
def version_statuses():
    return VERSION_STATUS


@router.post("")
def create_version(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("version_no") or not payload.get("project_id"):
        raise HTTPException(status_code=400, detail="版本号和所属项目必填")
    v = Version(
        version_no=payload["version_no"], name=payload.get("name", ""),
        start_date=payload.get("start_date", ""), launch_date=payload.get("launch_date", ""),
        status=payload.get("status", "规划中"), remark=payload.get("remark", ""),
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
    for k in ("version_no", "name", "start_date", "launch_date", "status", "remark", "project_id"):
        if k in payload:
            setattr(v, k, payload[k])
    db.commit()
    return {"id": vid}


@router.delete("/{vid}")
def delete_version(vid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    v = db.query(Version).filter(Version.id == vid).first()
    if v:
        db.delete(v)
        db.commit()
    return {"ok": True}
