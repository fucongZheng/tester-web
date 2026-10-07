"""评审记录：需求评审 / 用例评审"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReviewRecord, Requirement, TestCase
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, empty_to_none

router = APIRouter(prefix="/api/reviews", tags=["评审记录"])

REVIEW_TYPES = ["需求评审", "用例评审"]
REVIEW_RESULTS = ["待评审", "通过", "有条件通过", "不通过"]


def _parse_ids(raw):
    if isinstance(raw, list):
        return [int(x) for x in raw if x]
    if not raw:
        return []
    try:
        return [int(x) for x in json.loads(raw)]
    except Exception:
        return []


def _resolve_targets(db: Session, review_type: str, ids):
    if not ids:
        return []
    if review_type == "需求评审":
        rows = db.query(Requirement).filter(Requirement.id.in_(ids)).all()
        return [{"id": x.id, "no": x.req_no, "name": x.name} for x in rows]
    rows = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
    return [{"id": x.id, "no": x.case_no, "name": x.title} for x in rows]


def _to_dict(r: ReviewRecord, db: Session):
    d = row_to_dict(r)
    d["project_name"] = r.project.name if r.project else ""
    d["version_name"] = r.version.version_no if r.version else ""
    d["module_name"] = r.module.name if r.module else ""
    ids = _parse_ids(r.target_ids)
    d["target_ids"] = ids
    d["targets"] = _resolve_targets(db, r.review_type, ids)
    if r.review_type == "用例评审":
        normal = _parse_ids(r.normal_ids)
        d["normal_target_ids"] = normal
        d["normal_targets"] = _resolve_targets(db, r.review_type, normal)
    return d


@router.get("")
def list_reviews(page: int = 1, size: int = 10, keyword: str = "",
                 review_type: str = "", project_id: int = 0, version_id: int = 0,
                 module_id: int = 0, result: str = "",
                 db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(ReviewRecord)
    if keyword:
        q = q.filter(ReviewRecord.title.like(f"%{keyword}%") | ReviewRecord.review_no.like(f"%{keyword}%"))
    if review_type:
        q = q.filter(ReviewRecord.review_type == review_type)
    if project_id:
        q = q.filter(ReviewRecord.project_id == project_id)
    if version_id:
        q = q.filter(ReviewRecord.version_id == version_id)
    if module_id:
        q = q.filter(ReviewRecord.module_id == module_id)
    if result:
        q = q.filter(ReviewRecord.result == result)
    items, total = paginate(q.order_by(ReviewRecord.id.desc()), page, size)
    return {"items": [_to_dict(r, db) for r in items], "total": total}


@router.get("/options")
def review_options(_=Depends(get_current_user)):
    return {"types": REVIEW_TYPES, "results": REVIEW_RESULTS}


@router.post("")
def create_review(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    review_type = payload.get("review_type")
    if review_type not in REVIEW_TYPES:
        raise HTTPException(status_code=400, detail="评审类型必须是需求评审或用例评审")
    if not payload.get("project_id"):
        raise HTTPException(status_code=400, detail="项目必选")
    if not (payload.get("title") or "").strip():
        raise HTTPException(status_code=400, detail="评审标题必填")
    ids = _parse_ids(payload.get("target_ids") or [])
    # 核心用例与常规用例互斥，防御性去重
    normal_ids = [i for i in _parse_ids(payload.get("normal_ids") or []) if i not in ids]
    rec = ReviewRecord(
        review_type=review_type,
        title=payload["title"].strip(),
        project_id=payload["project_id"],
        version_id=empty_to_none(payload.get("version_id")),
        module_id=empty_to_none(payload.get("module_id")),
        target_ids=json.dumps(ids),
        normal_ids=json.dumps(normal_ids),
        reviewer=payload.get("reviewer") or (cur.real_name or cur.username),
        participants=payload.get("participants", ""),
        result=payload.get("result", "待评审"),
        comment=payload.get("comment", ""),
        review_date=payload.get("review_date", ""),
        created_by=cur.real_name or cur.username,
    )
    db.add(rec)
    db.flush()
    rec.review_no = gen_code("RV", rec.id)
    db.commit()
    return {"id": rec.id, "review_no": rec.review_no}


@router.put("/{rid}")
def update_review(rid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rec = db.query(ReviewRecord).filter(ReviewRecord.id == rid).first()
    if not rec:
        raise HTTPException(status_code=404, detail="评审记录不存在")
    if "review_type" in payload:
        if payload["review_type"] not in REVIEW_TYPES:
            raise HTTPException(status_code=400, detail="评审类型非法")
        rec.review_type = payload["review_type"]
    for k in ("title", "project_id", "version_id", "module_id", "reviewer", "participants",
              "result", "comment", "review_date"):
        if k in payload:
            if k in ("version_id", "module_id"):
                setattr(rec, k, empty_to_none(payload[k]))
            else:
                setattr(rec, k, payload[k])
    if "target_ids" in payload:
        rec.target_ids = json.dumps(_parse_ids(payload.get("target_ids") or []))
    if "normal_ids" in payload:
        core = set(_parse_ids(rec.target_ids))
        rec.normal_ids = json.dumps([i for i in _parse_ids(payload.get("normal_ids") or []) if i not in core])
    db.commit()
    return {"id": rid}


@router.get("/{rid}/cases")
def review_cases(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """评审用例明细（预览用）：核心用例在前、常规在后，带完整执行步骤等字段。"""
    rec = db.query(ReviewRecord).filter(ReviewRecord.id == rid).first()
    if not rec:
        raise HTTPException(status_code=404, detail="评审记录不存在")
    if rec.review_type != "用例评审":
        raise HTTPException(status_code=400, detail="只有用例评审支持预览用例")
    core_ids = _parse_ids(rec.target_ids)
    normal_ids = [i for i in _parse_ids(rec.normal_ids) if i not in core_ids]
    all_ids = core_ids + normal_ids
    rows = db.query(TestCase).filter(TestCase.id.in_(all_ids or [0])).all() if all_ids else []
    by_id = {c.id: c for c in rows}

    def _detail(c):
        d = row_to_dict(c)
        d["module_name"] = c.module.name if c.module else ""
        d["version_name"] = c.version.version_no if c.version else ""
        return d

    items = []
    for group, group_ids in (("core", core_ids), ("normal", normal_ids)):
        for cid in group_ids:
            c = by_id.get(cid)
            if c:
                items.append({"group": group, "case": _detail(c)})
    return {"title": rec.title, "core_count": len(core_ids), "normal_count": len(normal_ids), "items": items}


@router.delete("/{rid}")
def delete_review(rid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    rec = db.query(ReviewRecord).filter(ReviewRecord.id == rid).first()
    if rec:
        db.delete(rec)
        db.commit()
    return {"ok": True}
