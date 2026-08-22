"""看板统计"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Project, Version, Requirement, TestCase, Execution,
                      Bug, FlowInstance)
from ..deps import get_current_user
from ..helpers import row_to_dict
from .flow import stage_label

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {
        "project": db.query(Project).count(),
        "version": db.query(Version).count(),
        "requirement": db.query(Requirement).count(),
        "case": db.query(TestCase).count(),
        "execution": db.query(Execution).count(),
        "bug": db.query(Bug).count(),
        "bug_open": db.query(Bug).filter(~Bug.status.in_(
            ["测试验证通过关闭", "不是BUG"])).count(),
        "flow": db.query(FlowInstance).filter(FlowInstance.status == "进行中").count(),
    }


def _group(rows, key_fn):
    m = {}
    for r in rows:
        k = key_fn(r)
        m[k] = m.get(k, 0) + 1
    return m


@router.get("/bug-severity")
def bug_severity(db: Session = Depends(get_db), _=Depends(get_current_user)):
    bugs = db.query(Bug).all()
    m = _group(bugs, lambda b: b.severity)
    order = ["致命", "严重", "一般", "轻微", "建议"]
    return [{"name": k, "value": m.get(k, 0)} for k in order]


@router.get("/bug-status")
def bug_status(db: Session = Depends(get_db), _=Depends(get_current_user)):
    bugs = db.query(Bug).all()
    m = _group(bugs, lambda b: b.status)
    return [{"name": k, "value": v} for k, v in m.items()]


@router.get("/bug-module")
def bug_module(project_id: int = 0, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    bugs = q.all()
    m = _group(bugs, lambda b: b.module.name if b.module else "未分类")
    items = sorted(m.items(), key=lambda x: -x[1])[:10]
    return [{"name": k, "value": v} for k, v in items]


@router.get("/bug-trend")
def bug_trend(days: int = 30, db: Session = Depends(get_db), _=Depends(get_current_user)):
    since = datetime.now() - timedelta(days=days)
    bugs = db.query(Bug).filter(Bug.created_at >= since).all()
    closed = [b for b in bugs if b.closed_at]
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
    new_map = _group(bugs, lambda b: b.created_at.strftime("%m-%d"))
    closed_map = _group(closed, lambda b: b.closed_at.strftime("%m-%d"))
    return {
        "dates": dates,
        "new": [new_map.get(d, 0) for d in dates],
        "closed": [closed_map.get(d, 0) for d in dates],
    }


@router.get("/case-progress")
def case_progress(db: Session = Depends(get_db), _=Depends(get_current_user)):
    cases = db.query(TestCase).all()
    execs = db.query(Execution).all()
    by_version = {}
    for c in cases:
        by_version.setdefault(c.version_id, {"total": 0, "executed": 0, "passed": 0,
                                            "version": c.version.version_no if c.version else "?"})
        by_version[c.version_id]["total"] += 1
    for e in execs:
        if e.case and e.case.version_id in by_version:
            d = by_version[e.case.version_id]
            d["executed"] += 1
            if e.result == "通过":
                d["passed"] += 1
    data = []
    for vid, d in by_version.items():
        rate = f"{d['passed'] / d['executed'] * 100:.1f}" if d["executed"] else "0"
        data.append({"version": d["version"], "total": d["total"],
                     "executed": d["executed"], "passed": d["passed"], "rate": float(rate)})
    return sorted(data, key=lambda x: -x["total"])


@router.get("/flow-board")
def flow_board(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(FlowInstance).order_by(FlowInstance.id.desc()).all()
    data = []
    for f in items:
        d = row_to_dict(f)
        d["project_name"] = f.project.name if f.project else ""
        d["version_no"] = f.version.version_no if f.version else ""
        d["current_stage_label"] = stage_label(f.current_stage, f.current_round)
        data.append(d)
    return data
