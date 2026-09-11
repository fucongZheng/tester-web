"""看板统计"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Project, Version, Requirement, TestCase, Execution,
                      Bug, FlowInstance, Module)
from ..deps import require_admin
from ..helpers import row_to_dict, apply_module_filter
from .flow import stage_label

router = APIRouter(prefix="/api/dashboard", tags=["看板"], dependencies=[Depends(require_admin)])

CLOSED = {"测试验证通过关闭", "不是BUG"}
SEV_ORDER = ["致命", "严重", "一般", "轻微", "建议"]


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return {
        "project": db.query(Project).count(),
        "version": db.query(Version).count(),
        "requirement": db.query(Requirement).count(),
        "case": db.query(TestCase).count(),
        "execution": db.query(Execution).count(),
        "bug": db.query(Bug).count(),
        "bug_open": db.query(Bug).filter(~Bug.status.in_(list(CLOSED))).count(),
        "flow": db.query(FlowInstance).filter(FlowInstance.status == "进行中").count(),
    }


def _group(rows, key_fn):
    m = {}
    for r in rows:
        k = key_fn(r)
        m[k] = m.get(k, 0) + 1
    return m


def _named(m, order=None, extra_id=None):
    if order:
        return [{"name": k, "value": m.get(k, 0), **({} if extra_id is None else {})} for k in order]
    return [{"name": k, "value": v} for k, v in m.items()]


@router.get("/bug-severity")
def bug_severity(project_id: int = 0, version_id: int = 0, module_id: int = 0,
                 db: Session = Depends(get_db)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    m = _group(q.all(), lambda b: b.severity)
    return [{"name": k, "value": m.get(k, 0), "filter": {"severity": k}} for k in SEV_ORDER]


@router.get("/bug-status")
def bug_status(project_id: int = 0, version_id: int = 0, module_id: int = 0,
               db: Session = Depends(get_db)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    m = _group(q.all(), lambda b: b.status)
    return [{"name": k, "value": v, "filter": {"status": k}} for k, v in m.items()]


@router.get("/bug-module")
def bug_module(project_id: int = 0, version_id: int = 0,
               db: Session = Depends(get_db)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    bugs = q.all()
    items = []
    m = {}
    for b in bugs:
        mid = b.module_id or 0
        name = b.module.name if b.module else "未分类"
        key = (mid, name)
        m[key] = m.get(key, 0) + 1
    for (mid, name), v in sorted(m.items(), key=lambda x: -x[1]):
        items.append({"name": name, "value": v, "filter": {"module_id": mid if mid else -1}})
    return items


@router.get("/bug-stage")
def bug_stage(project_id: int = 0, version_id: int = 0, module_id: int = 0,
              db: Session = Depends(get_db)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    m = _group(q.all(), lambda b: b.found_stage or "未填写")
    return [{"name": k, "value": v, "filter": {"found_stage": k}} for k, v in m.items()]


@router.get("/bug-project")
def bug_project(db: Session = Depends(get_db)):
    bugs = db.query(Bug).all()
    m = {}
    for b in bugs:
        pid = b.project_id
        name = b.project.name if b.project else "未分类"
        m[(pid, name)] = m.get((pid, name), 0) + 1
    items = []
    for (pid, name), v in sorted(m.items(), key=lambda x: -x[1]):
        items.append({"name": name, "value": v, "filter": {"project_id": pid}})
    return items


@router.get("/bug-version")
def bug_version(project_id: int = 0, db: Session = Depends(get_db)):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    m = {}
    for b in q.all():
        vid = b.version_id
        name = b.version.version_no if b.version else "未分类"
        m[(vid, name)] = m.get((vid, name), 0) + 1
    items = []
    for (vid, name), v in sorted(m.items(), key=lambda x: -x[1]):
        items.append({"name": name, "value": v, "filter": {"version_id": vid}})
    return items


@router.get("/bug-rank")
def bug_rank(project_id: int = 0, version_id: int = 0, module_id: int = 0, limit: int = 20,
             db: Session = Depends(get_db)):
    """各研发 BUG 数（经办人优先，空则修复人），用于考核。"""
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    m = {}
    for b in q.all():
        name = (b.assignee or b.fixer or "").strip() or "未指派"
        m[name] = m.get(name, 0) + 1
    items = sorted(m.items(), key=lambda x: -x[1])[: max(1, min(limit, 50))]
    return [{"name": k, "value": v, "filter": {"assignee": k}} for k, v in items]


@router.get("/bug-trend")
def bug_trend(days: int = 7, project_id: int = 0, version_id: int = 0, module_id: int = 0,
              db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(days=days)
    q = db.query(Bug).filter(Bug.created_at >= since)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    q = apply_module_filter(q, Bug, module_id)
    bugs = q.all()
    closed = [b for b in bugs if b.closed_at]
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
    new_map = _group(bugs, lambda b: b.created_at.strftime("%m-%d") if b.created_at else "")
    closed_map = _group(closed, lambda b: b.closed_at.strftime("%m-%d") if b.closed_at else "")
    return {
        "dates": dates,
        "new": [new_map.get(d, 0) for d in dates],
        "closed": [closed_map.get(d, 0) for d in dates],
    }


@router.get("/case-progress")
def case_progress(db: Session = Depends(get_db)):
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


@router.get("/module-stats")
def module_stats(project_id: int = 0, version_id: int = 0,
                 db: Session = Depends(get_db)):
    """按模块统计需求 / 用例 / BUG。"""
    mq = db.query(Module)
    if project_id:
        mq = mq.filter(Module.project_id == project_id)
    modules = mq.order_by(Module.sort, Module.id).all()

    def _cnt(model, mid):
        q = db.query(model).filter(model.module_id == mid)
        if project_id:
            q = q.filter(model.project_id == project_id)
        if version_id and hasattr(model, "version_id"):
            q = q.filter(model.version_id == version_id)
        return q.count()

    rows = []
    for m in modules:
        rows.append({
            "module_id": m.id,
            "name": m.name,
            "requirement": _cnt(Requirement, m.id),
            "case": _cnt(TestCase, m.id),
            "bug": _cnt(Bug, m.id),
            "filter": {"module_id": m.id, "project_id": m.project_id},
        })
    # 未分类
    def _uncat(model):
        q = db.query(model).filter(model.module_id.is_(None))
        if project_id:
            q = q.filter(model.project_id == project_id)
        if version_id and hasattr(model, "version_id"):
            q = q.filter(model.version_id == version_id)
        return q.count()
    un_req, un_case, un_bug = _uncat(Requirement), _uncat(TestCase), _uncat(Bug)
    if un_req or un_case or un_bug:
        rows.append({
            "module_id": 0, "name": "未分类",
            "requirement": un_req, "case": un_case, "bug": un_bug,
            "filter": {"module_id": -1, "project_id": project_id or None},
        })
    return rows


@router.get("/flow-board")
def flow_board(db: Session = Depends(get_db)):
    items = db.query(FlowInstance).order_by(FlowInstance.id.desc()).all()
    data = []
    for f in items:
        d = row_to_dict(f)
        d["project_name"] = f.project.name if f.project else ""
        d["version_no"] = f.version.version_no if f.version else ""
        d["current_stage_label"] = stage_label(f.current_stage, f.current_round)
        data.append(d)
    return data
