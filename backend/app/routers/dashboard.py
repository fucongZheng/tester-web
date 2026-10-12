"""看板统计"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Project, Version, Requirement, TestCase, Execution,
                      Bug, FlowInstance, Module)
from ..deps import require_admin
from ..helpers import row_to_dict, apply_module_filter
from ..flow_stages import stage_label

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


def _bug_q(db, project_id, version_id, module_id, *cols):
    """按项目/版本/模块过滤的 Bug 查询；传 cols 时为聚合查询（不回表）。"""
    q = db.query(*cols) if cols else db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    return apply_module_filter(q, Bug, module_id)


def _count_by(q, col):
    """GROUP BY 聚合成 {key: count}。"""
    return dict(q.group_by(col).all())


@router.get("/bug-severity")
def bug_severity(project_id: int = 0, version_id: int = 0, module_id: int = 0,
                 db: Session = Depends(get_db)):
    q = _bug_q(db, project_id, version_id, module_id, Bug.severity, func.count())
    m = _count_by(q, Bug.severity)
    return [{"name": k, "value": m.get(k, 0), "filter": {"severity": k}} for k in SEV_ORDER]


@router.get("/bug-status")
def bug_status(project_id: int = 0, version_id: int = 0, module_id: int = 0,
               db: Session = Depends(get_db)):
    q = _bug_q(db, project_id, version_id, module_id, Bug.status, func.count())
    m = _count_by(q, Bug.status)
    return [{"name": k, "value": v, "filter": {"status": k}} for k, v in m.items()]


@router.get("/bug-module")
def bug_module(project_id: int = 0, version_id: int = 0,
               db: Session = Depends(get_db)):
    q = db.query(Bug.module_id, func.count())
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if version_id:
        q = q.filter(Bug.version_id == version_id)
    m = _count_by(q, Bug.module_id)
    names = {mo.id: mo.name for mo in db.query(Module).all()}
    items = []
    for mid, v in sorted(m.items(), key=lambda x: -x[1]):
        name = names.get(mid, "未分类") if mid else "未分类"
        items.append({"name": name, "value": v, "filter": {"module_id": mid if mid else -1}})
    return items


@router.get("/bug-stage")
def bug_stage(project_id: int = 0, version_id: int = 0, module_id: int = 0,
              db: Session = Depends(get_db)):
    stage = func.coalesce(Bug.found_stage, "未填写")
    q = _bug_q(db, project_id, version_id, module_id, stage, func.count())
    m = _count_by(q, stage)
    return [{"name": k or "未填写", "value": v, "filter": {"found_stage": k or "未填写"}}
            for k, v in m.items()]


@router.get("/bug-project")
def bug_project(db: Session = Depends(get_db)):
    m = _count_by(db.query(Bug.project_id, func.count()), Bug.project_id)
    names = {p.id: p.name for p in db.query(Project).all()}
    items = []
    for pid, v in sorted(m.items(), key=lambda x: -x[1]):
        items.append({"name": names.get(pid, "未分类"), "value": v, "filter": {"project_id": pid}})
    return items


@router.get("/bug-version")
def bug_version(project_id: int = 0, db: Session = Depends(get_db)):
    q = db.query(Bug.version_id, func.count())
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    m = _count_by(q, Bug.version_id)
    names = {v.id: v.version_no for v in db.query(Version).all()}
    items = []
    for vid, v in sorted(m.items(), key=lambda x: -x[1]):
        items.append({"name": names.get(vid, "未分类"), "value": v, "filter": {"version_id": vid}})
    return items


@router.get("/bug-rank")
def bug_rank(project_id: int = 0, version_id: int = 0, module_id: int = 0, limit: int = 20,
             db: Session = Depends(get_db)):
    """各研发 BUG 数（经办人优先，空则修复人），用于考核。"""
    name = func.coalesce(func.nullif(func.trim(Bug.assignee), ""),
                         func.nullif(func.trim(Bug.fixer), ""), "未指派")
    q = _bug_q(db, project_id, version_id, module_id, name, func.count())
    m = _count_by(q, name)
    items = sorted(m.items(), key=lambda x: -x[1])[: max(1, min(limit, 50))]
    return [{"name": k, "value": v, "filter": {"assignee": k}} for k, v in items]


@router.get("/bug-trend")
def bug_trend(days: int = 7, project_id: int = 0, version_id: int = 0, module_id: int = 0,
              db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(days=days)
    new_day = func.date(Bug.created_at)
    closed_day = func.date(Bug.closed_at)
    new_map = {str(d)[5:10].replace("/", "-"): c for d, c in _count_by(
        _bug_q(db, project_id, version_id, module_id, new_day, func.count())
        .filter(Bug.created_at >= since), new_day).items()}
    closed_map = {str(d)[5:10].replace("/", "-"): c for d, c in _count_by(
        _bug_q(db, project_id, version_id, module_id, closed_day, func.count())
        .filter(Bug.closed_at.isnot(None)), closed_day).items()}
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m-%d") for i in range(days - 1, -1, -1)]
    return {
        "dates": dates,
        "new": [new_map.get(d, 0) for d in dates],
        "closed": [closed_map.get(d, 0) for d in dates],
    }


@router.get("/case-progress")
def case_progress(db: Session = Depends(get_db)):
    # DB 聚合替代全表加载：按版本统计用例总数与执行/通过数
    totals = _count_by(db.query(TestCase.version_id, func.count()), TestCase.version_id)
    exec_q = (db.query(TestCase.version_id, Execution.result, func.count())
              .join(Execution, Execution.case_id == TestCase.id)
              .group_by(TestCase.version_id, Execution.result))
    exec_map = {}
    for vid, result, cnt in exec_q.all():
        d = exec_map.setdefault(vid, {"executed": 0, "passed": 0})
        d["executed"] += cnt
        if result == "通过":
            d["passed"] += cnt
    version_names = {v.id: v.version_no for v in db.query(Version).all()}
    data = []
    for vid, total in totals.items():
        d = exec_map.get(vid, {"executed": 0, "passed": 0})
        rate = f"{d['passed'] / d['executed'] * 100:.1f}" if d["executed"] else "0"
        data.append({"version": version_names.get(vid, "?"), "total": total,
                     "executed": d["executed"], "passed": d["passed"], "rate": float(rate)})
    return sorted(data, key=lambda x: -x["total"])


@router.get("/module-stats")
def module_stats(project_id: int = 0, version_id: int = 0,
                 db: Session = Depends(get_db)):
    """按模块统计需求 / 用例 / BUG（三条 GROUP BY，替代逐模块 COUNT 的 N+1）。"""
    mq = db.query(Module)
    if project_id:
        mq = mq.filter(Module.project_id == project_id)
    modules = mq.order_by(Module.sort, Module.id).all()

    def _by_module(model):
        q = db.query(model.module_id, func.count())
        if project_id:
            q = q.filter(model.project_id == project_id)
        if version_id and hasattr(model, "version_id"):
            q = q.filter(model.version_id == version_id)
        return _count_by(q, model.module_id)

    req_map, case_map, bug_map = _by_module(Requirement), _by_module(TestCase), _by_module(Bug)
    rows = []
    for m in modules:
        rows.append({
            "module_id": m.id,
            "name": m.name,
            "requirement": req_map.get(m.id, 0),
            "case": case_map.get(m.id, 0),
            "bug": bug_map.get(m.id, 0),
            "filter": {"module_id": m.id, "project_id": m.project_id},
        })
    un_req, un_case, un_bug = (req_map.get(None, 0), case_map.get(None, 0), bug_map.get(None, 0))
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
