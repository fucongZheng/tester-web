"""用例执行记录"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Execution
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict

router = APIRouter(prefix="/api/executions", tags=["执行记录"])

RESULTS = ["通过", "失败", "阻塞", "跳过", "未执行"]


@router.get("")
def list_executions(case_id: int = 0, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Execution)
    if case_id:
        q = q.filter(Execution.case_id == case_id)
    items = q.order_by(Execution.id.desc()).all()
    data = []
    for e in items:
        d = row_to_dict(e)
        d["case_title"] = e.case.title if e.case else ""
        d["case_no"] = e.case.case_no if e.case else ""
        data.append(d)
    return {"items": data, "total": len(data)}


@router.get("/options")
def exec_options(_=Depends(get_current_user)):
    return RESULTS


@router.post("")
def create_execution(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    if not payload.get("case_id"):
        raise HTTPException(status_code=400, detail="case_id 必填")
    e = Execution(
        case_id=payload["case_id"], round_no=payload.get("round_no", 1),
        stage_no=payload.get("stage_no", 3), result=payload.get("result", "未执行"),
        actual=payload.get("actual", ""),
        executor=payload.get("executor") or cur.real_name or cur.username,
        remark=payload.get("remark", ""),
    )
    db.add(e)
    db.commit()
    return {"id": e.id}


@router.put("/{eid}")
def update_execution(eid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    e = db.query(Execution).filter(Execution.id == eid).first()
    if not e:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    for k in ("round_no", "stage_no", "result", "actual", "executor", "remark"):
        if k in payload:
            setattr(e, k, payload[k])
    db.commit()
    return {"id": eid}


@router.delete("/{eid}")
def delete_execution(eid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    e = db.query(Execution).filter(Execution.id == eid).first()
    if e:
        db.delete(e)
        db.commit()
    return {"ok": True}
