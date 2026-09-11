"""开发提测"""
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Handover, HandoverShare, Project, Requirement, SysUser,
                      TestCase, TestSuite, Version, Execution, Module)
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, empty_to_none, parse_id_list, apply_module_filter
from ..ratelimit import guard_public_write

SHARE_TTL_DAYS = 7

router = APIRouter(prefix="/api/handovers", tags=["开发提测"])

SMOKE_STATUS = ["未执行", "已执行"]
HANDOVER_STATUS = ["待测试", "测试中", "已完成", "已驳回"]
EXEC_RESULTS = ["通过", "失败", "阻塞", "跳过", "未执行"]


def _parse_ids(raw):
    if isinstance(raw, list):
        return [int(x) for x in raw if x]
    if not raw:
        return []
    try:
        return [int(x) for x in json.loads(raw)]
    except Exception:
        return []


def _to_dict(h: Handover, db: Session):
    d = row_to_dict(h)
    d["project_name"] = h.project.name if h.project else ""
    d["version_name"] = h.version.version_no if h.version else ""
    d["module_name"] = h.module.name if h.module else ""
    d["tester_name"] = (h.tester.real_name or h.tester.username) if h.tester else (h.tester_name or "")
    ids = _parse_ids(h.requirement_ids)
    d["requirement_ids"] = ids
    reqs = []
    if ids:
        rows = db.query(Requirement).filter(Requirement.id.in_(ids)).all()
        reqs = [{"id": r.id, "req_no": r.req_no, "name": r.name, "status": r.status} for r in rows]
    d["requirements"] = reqs
    d["suite_id"] = h.suite_id
    suite = db.query(TestSuite).filter(TestSuite.id == h.suite_id).first() if h.suite_id else None
    d["suite_name"] = suite.name if suite else ""
    d["suite_type"] = suite.suite_type if suite else ""
    return d


@router.get("")
def list_handovers(page: int = 1, size: int = 10, keyword: str = "",
                   project_id: int = 0, version_id: int = 0, module_id: int = 0, status: str = "",
                   db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Handover)
    if keyword:
        q = q.filter(Handover.handover_no.like(f"%{keyword}%") | Handover.branch.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(Handover.project_id == project_id)
    if version_id:
        q = q.filter(Handover.version_id == version_id)
    q = apply_module_filter(q, Handover, module_id)
    if status:
        q = q.filter(Handover.status == status)
    items, total = paginate(q.order_by(Handover.id.desc()), page, size)
    return {"items": [_to_dict(h, db) for h in items], "total": total}


@router.get("/options")
def handover_options(_=Depends(get_current_user)):
    return {"smoke": SMOKE_STATUS, "status": HANDOVER_STATUS}


def _share_or_404(db, token: str) -> HandoverShare:
    s = db.query(HandoverShare).filter(HandoverShare.token == token).first()
    if not s:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    if s.expires_at and s.expires_at < datetime.now():
        raise HTTPException(status_code=410, detail="分享链接已过期，请联系测试重新分享")
    return s


def _create_handover(payload: dict, db: Session, submitter: str):
    submitter = (submitter or "").strip()
    if not submitter:
        raise HTTPException(status_code=400, detail="提交人必填")
    if not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="项目和版本必选")
    if not (payload.get("branch") or "").strip():
        raise HTTPException(status_code=400, detail="提测分支必填")
    if not payload.get("tester_id"):
        raise HTTPException(status_code=400, detail="测试人员必选")
    tester = db.query(SysUser).filter(SysUser.id == payload["tester_id"]).first()
    if not tester:
        raise HTTPException(status_code=400, detail="测试人员不存在")
    req_ids = _parse_ids(payload.get("requirement_ids") or [])
    h = Handover(
        project_id=payload["project_id"],
        version_id=payload["version_id"],
        module_id=empty_to_none(payload.get("module_id")),
        requirement_ids=json.dumps(req_ids),
        branch=(payload.get("branch") or "").strip(),
        smoke_executed=payload.get("smoke_executed", "未执行"),
        suite_id=empty_to_none(payload.get("suite_id")),
        tester_id=tester.id,
        tester_name=tester.real_name or tester.username,
        remark=payload.get("remark", ""),
        status=payload.get("status", "待测试"),
        submitter=submitter,
    )
    db.add(h)
    db.flush()
    h.handover_no = gen_code("HT", h.id)
    from .flow import ensure_flow
    ensure_flow(db, h.project_id, h.version_id, operator=submitter, commit=False)
    db.commit()
    return {"id": h.id, "handover_no": h.handover_no}


@router.post("")
def create_handover(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    return _create_handover(payload, db, cur.real_name or cur.username)


def _share_expires_at(s: HandoverShare):
    return s.expires_at.strftime("%Y-%m-%d %H:%M:%S") if s.expires_at else ""


@router.post("/share")
def create_handover_share(payload: dict = None, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    payload = payload or {}
    project_id = empty_to_none(payload.get("project_id"))
    if not project_id:
        raise HTTPException(status_code=400, detail="请先选择项目再分享")
    token = secrets.token_urlsafe(24)
    s = HandoverShare(
        token=token,
        project_id=project_id,
        version_id=empty_to_none(payload.get("version_id")),
        created_by=cur.real_name or cur.username,
        expires_at=datetime.now() + timedelta(days=SHARE_TTL_DAYS),
    )
    db.add(s)
    db.commit()
    return {
        "token": token,
        "expires_at": s.expires_at.strftime("%Y-%m-%d %H:%M:%S") if s.expires_at else "",
    }


@router.get("/public/{token}")
def public_handover_form(token: str, project_id: int = 0, version_id: int = 0, module_id: int = 0,
                         db: Session = Depends(get_db)):
    s = _share_or_404(db, token)
    pid = s.project_id or project_id or 0
    if s.project_id and project_id and project_id != s.project_id:
        raise HTTPException(status_code=403, detail="该分享仅限指定项目")
    vid = s.version_id or version_id or 0
    if s.version_id and version_id and version_id != s.version_id:
        raise HTTPException(status_code=403, detail="该分享仅限指定版本")
    if s.version_id:
        vid = s.version_id
    mid = module_id or 0
    if s.project_id:
        projects = db.query(Project).filter(Project.id == s.project_id).all()
    else:
        projects = db.query(Project).order_by(Project.id.desc()).all()
    testers = db.query(SysUser).filter(SysUser.status == 1).order_by(SysUser.id).all()
    versions, reqs, suites, modules = [], [], [], []
    if pid:
        vq = db.query(Version).filter(Version.project_id == pid)
        if s.version_id:
            vq = vq.filter(Version.id == s.version_id)
        versions = vq.order_by(Version.id.desc()).all()
        modules = db.query(Module).filter(Module.project_id == pid).order_by(Module.sort, Module.id).all()
    if pid and vid:
        rq = db.query(Requirement).filter(Requirement.project_id == pid, Requirement.version_id == vid)
        sq = db.query(TestSuite).filter(
            TestSuite.project_id == pid, TestSuite.version_id == vid, TestSuite.suite_type == "冒烟"
        )
        if mid:
            rq = rq.filter(Requirement.module_id == mid)
            sq = sq.filter((TestSuite.module_id == mid) | (TestSuite.module_id.is_(None)))
        reqs = rq.order_by(Requirement.id.desc()).all()
        suites = sq.order_by(TestSuite.id.desc()).all()
    return {
        "created_by": s.created_by,
        "project_id": pid or None,
        "version_id": vid or None,
        "expires_at": _share_expires_at(s),
        "projects": [{"id": p.id, "name": p.name} for p in projects],
        "testers": [{"id": u.id, "real_name": u.real_name or u.username} for u in testers],
        "versions": [{"id": v.id, "version_no": v.version_no, "name": v.name, "project_id": v.project_id} for v in versions],
        "modules": [{"id": m.id, "name": m.name} for m in modules],
        "requirements": [{"id": r.id, "req_no": r.req_no, "name": r.name, "module_id": r.module_id} for r in reqs],
        "suites": [{"id": t.id, "name": t.name, "case_ids": parse_id_list(t.case_ids), "module_id": t.module_id} for t in suites],
        "options": {"smoke": SMOKE_STATUS, "status": HANDOVER_STATUS, "exec_results": EXEC_RESULTS},
    }


def _public_suite(db, token: str, sid: int) -> TestSuite:
    s = _share_or_404(db, token)
    suite = db.query(TestSuite).filter(TestSuite.id == sid).first()
    if not suite or suite.suite_type != "冒烟":
        raise HTTPException(status_code=404, detail="冒烟套件不存在")
    if s.project_id and suite.project_id != s.project_id:
        raise HTTPException(status_code=403, detail="该套件不在本次分享范围内")
    if s.version_id and suite.version_id != s.version_id:
        raise HTTPException(status_code=403, detail="该套件不在本次分享范围内")
    return suite


def _case_public(c: TestCase, last_result=""):
    return {
        "id": c.id, "case_no": c.case_no, "title": c.title, "case_type": c.case_type,
        "precondition": c.precondition or "", "steps": c.steps or "", "expected": c.expected or "",
        "last_result": last_result,
    }


@router.get("/public/{token}/suites/{sid}")
def public_suite_cases(token: str, sid: int, db: Session = Depends(get_db)):
    """分享页查看冒烟套件用例，免登录。"""
    suite = _public_suite(db, token, sid)
    ids = parse_id_list(suite.case_ids)
    cases = []
    if ids:
        rows = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
        by_id = {c.id: c for c in rows}
        for cid in ids:
            c = by_id.get(cid)
            if not c:
                continue
            latest = db.query(Execution).filter(Execution.case_id == c.id).order_by(Execution.id.desc()).first()
            cases.append(_case_public(c, latest.result if latest else ""))
    return {"id": suite.id, "name": suite.name, "cases": cases}


@router.get("/public/{token}/cases/{cid}/executions")
def public_case_executions(token: str, cid: int, suite_id: int = 0, db: Session = Depends(get_db)):
    _share_or_404(db, token)
    if not suite_id:
        raise HTTPException(status_code=400, detail="套件必选")
    suite = _public_suite(db, token, suite_id)
    if cid not in parse_id_list(suite.case_ids):
        raise HTTPException(status_code=403, detail="该用例不在所选冒烟套件中")
    items = db.query(Execution).filter(Execution.case_id == cid).order_by(Execution.id.desc()).all()
    return {"items": [row_to_dict(e) for e in items]}


@router.post("/public/{token}/executions")
def public_create_execution(token: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    """分享页提交冒烟执行结果。"""
    _share_or_404(db, token)
    guard_public_write(request, token)
    case_id = empty_to_none(payload.get("case_id"))
    suite_id = empty_to_none(payload.get("suite_id"))
    if not case_id or not suite_id:
        raise HTTPException(status_code=400, detail="套件和用例必选")
    suite = _public_suite(db, token, suite_id)
    if case_id not in parse_id_list(suite.case_ids):
        raise HTTPException(status_code=403, detail="该用例不在所选冒烟套件中")
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    result = payload.get("result") or "未执行"
    if result not in EXEC_RESULTS:
        raise HTTPException(status_code=400, detail="非法执行结果")
    executor = (payload.get("executor") or "").strip()
    sid = empty_to_none(payload.get("submitter_id"))
    if sid:
        user = db.query(SysUser).filter(SysUser.id == sid, SysUser.status == 1).first()
        if user:
            executor = user.real_name or user.username
    if not executor:
        raise HTTPException(status_code=400, detail="请先选择提交人，再执行冒烟用例")
    e = Execution(
        case_id=case_id,
        round_no=payload.get("round_no", 1),
        stage_no=payload.get("stage_no", 1),
        result=result,
        actual=payload.get("actual", ""),
        executor=executor,
        remark=payload.get("remark", "") or "提测分享页冒烟",
    )
    db.add(e)
    db.commit()
    latest = db.query(Execution).filter(Execution.case_id == case_id).order_by(Execution.id.desc()).first()
    return {"id": e.id, "last_result": latest.result if latest else result}


@router.post("/public/{token}")
def public_create_handover(token: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    s = _share_or_404(db, token)
    guard_public_write(request, token)
    if s.project_id:
        payload["project_id"] = s.project_id
    if s.version_id:
        payload["version_id"] = s.version_id
    sid = empty_to_none(payload.get("submitter_id"))
    if not sid:
        raise HTTPException(status_code=400, detail="提交人必填")
    user = db.query(SysUser).filter(SysUser.id == sid, SysUser.status == 1).first()
    if not user:
        raise HTTPException(status_code=400, detail="提交人不是系统用户")
    return _create_handover(payload, db, user.real_name or user.username)


@router.put("/{hid}")
def update_handover(hid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    h = db.query(Handover).filter(Handover.id == hid).first()
    if not h:
        raise HTTPException(status_code=404, detail="提测单不存在")
    if "project_id" in payload:
        h.project_id = payload["project_id"]
    if "version_id" in payload:
        h.version_id = payload["version_id"]
    if "module_id" in payload:
        h.module_id = empty_to_none(payload.get("module_id"))
    if "requirement_ids" in payload:
        h.requirement_ids = json.dumps(_parse_ids(payload.get("requirement_ids") or []))
    if "branch" in payload:
        if not (payload.get("branch") or "").strip():
            raise HTTPException(status_code=400, detail="提测分支必填")
        h.branch = payload["branch"].strip()
    if "smoke_executed" in payload:
        h.smoke_executed = payload["smoke_executed"]
    if "suite_id" in payload:
        h.suite_id = empty_to_none(payload.get("suite_id"))
    if "tester_id" in payload:
        if not payload.get("tester_id"):
            raise HTTPException(status_code=400, detail="测试人员必选")
        tester = db.query(SysUser).filter(SysUser.id == payload["tester_id"]).first()
        if not tester:
            raise HTTPException(status_code=400, detail="测试人员不存在")
        h.tester_id = tester.id
        h.tester_name = tester.real_name or tester.username
    if "remark" in payload:
        h.remark = payload["remark"]
    if "status" in payload:
        h.status = payload["status"]
    db.commit()
    return {"id": hid}


@router.delete("/{hid}")
def delete_handover(hid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    h = db.query(Handover).filter(Handover.id == hid).first()
    if h:
        db.delete(h)
        db.commit()
    return {"ok": True}
