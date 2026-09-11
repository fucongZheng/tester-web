"""操作日志"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import OperationLog
from ..deps import require_admin
from ..helpers import row_to_dict, paginate

router = APIRouter(prefix="/api/logs", tags=["操作日志"])


@router.get("")
def list_logs(page: int = 1, size: int = 10, keyword: str = "",
              db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(OperationLog)
    if keyword:
        q = q.filter(OperationLog.username.like(f"%{keyword}%") | OperationLog.path.like(f"%{keyword}%"))
    items, total = paginate(q.order_by(OperationLog.id.desc()), page, size)
    return {"items": [row_to_dict(i) for i in items], "total": total}
