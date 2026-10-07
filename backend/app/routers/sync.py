"""需求同步：对接 xuqiu 需求系统开放 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..helpers import paginate, row_to_dict
from ..models import SyncLog
from ..sync_service import run_sync

router = APIRouter(prefix="/api/sync", tags=["需求同步"])


@router.post("/run")
def trigger_sync(db: Session = Depends(get_db), _=Depends(get_current_user)):
    result = run_sync(db, trigger="manual")
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "同步失败"))
    return result


@router.get("/logs")
def list_sync_logs(page: int = 1, size: int = 10,
                   db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(SyncLog).order_by(SyncLog.id.desc())
    items, total = paginate(q, page, size)
    return {"items": [row_to_dict(i) for i in items], "total": total}
