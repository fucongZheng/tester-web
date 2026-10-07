"""测试套件"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TestSuite, TestCase, Handover, Execution
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, parse_id_list, empty_to_none, apply_module_filter
from ..flow_stages import STAGE_NO, SUITE_TYPE_STAGE

router = APIRouter(prefix="/api/suites", tags=["测试套件"])

SUITE_TYPES = ["冒烟", "第一轮功能", "回归", "自定义"]
EXEC_RESULTS = ["通过", "失败", "阻塞", "跳过"]  # 可提交的执行结果（未执行不算）


def _latest_results(db, case_ids):
    """每个用例最近一次执行结果。"""
    if not case_ids:
        return {}
    rows = db.query(Execution).filter(Execution.case_id.in_(case_ids)).order_by(Execution.id.desc()).all()
    latest = {}
    for e in rows:
        if e.case_id not in latest:
            latest[e.case_id] = e.result
    return latest


def _exec_stats(case_ids, latest):
    total = len(case_ids)
    executed = 0
    passed = 0
    for cid in case_ids:
        r = latest.get(cid)
        if r and r != "未执行":
            executed += 1
            if r == "通过":
                passed += 1
    return {
        "case_count": total,
        "executed_count": executed,
        "pass_count": passed,
        "pass_rate": f"{passed / executed * 100:.1f}%" if executed else "0%",
    }


def _to_dict(s: TestSuite, db: Session, latest=None):
    d = row_to_dict(s)
    d["project_name"] = s.project.name if s.project else ""
    d["version_name"] = s.version.version_no if s.version else ""
    d["module_name"] = s.module.name if s.module else ""
    ids = parse_id_list(s.case_ids)
    d["case_ids"] = ids
    cases = []
    if ids:
        rows = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
        by_id = {c.id: c for c in rows}
        for i in ids:
            c = by_id.get(i)
            if c:
                cases.append({
                    "id": c.id, "case_no": c.case_no, "title": c.title, "case_type": c.case_type,
                    "precondition": c.precondition or "", "steps": c.steps or "", "expected": c.expected or "",
                })
    d["cases"] = cases
    if latest is None:
        latest = _latest_results(db, ids)
    d.update(_exec_stats(ids, latest))
    return d


@router.get("")
def list_suites(page: int = 1, size: int = 10, keyword: str = "",
                project_id: int = 0, version_id: int = 0, module_id: int = 0, suite_type: str = "",
                db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestSuite)
    if keyword:
        q = q.filter(TestSuite.name.like(f"%{keyword}%") | TestSuite.suite_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(TestSuite.project_id == project_id)
    if version_id:
        q = q.filter(TestSuite.version_id == version_id)
    q = apply_module_filter(q, TestSuite, module_id)
    if suite_type:
        q = q.filter(TestSuite.suite_type == suite_type)
    items, total = paginate(q.order_by(TestSuite.id.desc()), page, size)
    all_ids = []
    for s in items:
        all_ids.extend(parse_id_list(s.case_ids))
    latest = _latest_results(db, list(set(all_ids)))
    return {"items": [_to_dict(s, db, latest) for s in items], "total": total}


@router.get("/all")
def all_suites(project_id: int = 0, version_id: int = 0, module_id: int = 0, suite_type: str = "",
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestSuite)
    if project_id:
        q = q.filter(TestSuite.project_id == project_id)
    if version_id:
        q = q.filter(TestSuite.version_id == version_id)
    if module_id:
        q = q.filter((TestSuite.module_id == module_id) | (TestSuite.module_id.is_(None)))
    if suite_type:
        q = q.filter(TestSuite.suite_type == suite_type)
    items = q.order_by(TestSuite.id.desc()).all()
    return [{"id": s.id, "suite_no": s.suite_no, "name": s.name, "suite_type": s.suite_type,
             "project_id": s.project_id, "version_id": s.version_id, "module_id": s.module_id,
             "case_ids": parse_id_list(s.case_ids)} for s in items]


@router.get("/options")
def suite_options(_=Depends(get_current_user)):
    return {"suite_type": SUITE_TYPES}


@router.get("/{sid}")
def get_suite(sid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(TestSuite).filter(TestSuite.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="套件不存在")
    return _to_dict(s, db)


def _suite_or_404(db: Session, sid: int) -> TestSuite:
    s = db.query(TestSuite).filter(TestSuite.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="套件不存在")
    return s


@router.get("/{sid}/executions")
def suite_execution_sheet(sid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """执行弹窗数据：套件内用例（含步骤）+ 各自最近一次执行结果，一次查询。"""
    s = _suite_or_404(db, sid)
    ids = parse_id_list(s.case_ids)
    latest = _latest_results(db, ids)
    rows = db.query(TestCase).filter(TestCase.id.in_(ids or [0])).all() if ids else []
    by_id = {c.id: c for c in rows}
    items = []
    for cid in ids:
        c = by_id.get(cid)
        if c:
            items.append({
                "id": c.id, "case_no": c.case_no, "title": c.title, "case_type": c.case_type,
                "priority": c.priority, "precondition": c.precondition or "",
                "steps": c.steps or "", "expected": c.expected or "",
                "last_result": latest.get(cid, ""),
            })
    return {"id": s.id, "name": s.name, "suite_type": s.suite_type, "items": items}


@router.post("/{sid}/executions")
def submit_suite_executions(sid: int, payload: dict, db: Session = Depends(get_db),
                            cur=Depends(get_current_user)):
    """整套件批量提交执行记录：items=[{case_id,result,actual}]，轮次统一，
    执行记录按套件类型自动归属流程环节（冒烟→提测、第一轮功能→人工、回归→回归）。"""
    s = _suite_or_404(db, sid)
    valid_ids = set(parse_id_list(s.case_ids))
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="套件内没有用例，无可提交的执行记录")
    round_no = int(payload.get("round_no") or 1)
    stage_no = STAGE_NO[SUITE_TYPE_STAGE.get(s.suite_type, "manual")]
    executor = cur.real_name or cur.username
    for it in items:
        if it.get("case_id") not in valid_ids:
            raise HTTPException(status_code=400, detail="存在不属于该套件的用例，请刷新后重试")
        if it.get("result") not in EXEC_RESULTS:
            raise HTTPException(status_code=400,
                                detail=f"用例执行结果必须是 {'/'.join(EXEC_RESULTS)}，不能提交「未执行」")
    for it in items:
        db.add(Execution(
            case_id=it["case_id"], round_no=round_no, stage_no=stage_no,
            result=it["result"], actual=it.get("actual", ""),
            executor=executor, remark=f"套件执行：{s.name}",
        ))
    db.commit()
    latest = _latest_results(db, list(valid_ids))
    return {"created": len(items), **_exec_stats(list(valid_ids), latest)}


@router.post("")
def create_suite(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    if not payload.get("name") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="名称/项目/版本必填")
    ids = parse_id_list(payload.get("case_ids") or [])
    s = TestSuite(
        name=payload["name"].strip(),
        suite_type=payload.get("suite_type") or "自定义",
        project_id=payload["project_id"],
        version_id=payload["version_id"],
        module_id=empty_to_none(payload.get("module_id")),
        case_ids=json.dumps(ids),
        remark=payload.get("remark", ""),
        created_by=cur.real_name or cur.username,
    )
    db.add(s)
    db.flush()
    s.suite_no = gen_code("TS", s.id)
    db.commit()
    return {"id": s.id, "suite_no": s.suite_no}


@router.put("/{sid}")
def update_suite(sid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(TestSuite).filter(TestSuite.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="套件不存在")
    for k in ("name", "suite_type", "project_id", "version_id", "remark"):
        if k in payload:
            setattr(s, k, payload[k])
    if "module_id" in payload:
        s.module_id = empty_to_none(payload.get("module_id"))
    if "case_ids" in payload:
        s.case_ids = json.dumps(parse_id_list(payload.get("case_ids") or []))
    db.commit()
    return {"id": sid}


@router.delete("/{sid}")
def delete_suite(sid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    s = db.query(TestSuite).filter(TestSuite.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="套件不存在")
    db.query(Handover).filter(Handover.suite_id == sid).update(
        {Handover.suite_id: None}, synchronize_session=False)
    db.delete(s)
    db.commit()
    return {"ok": True}
