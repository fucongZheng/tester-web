"""测试用例管理"""
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai_client import AIError, chat
from ..database import get_db
from ..models import (Module, Project, Requirement, TestCase, Version,
                      Execution, Bug, TestSuite, ReviewRecord)
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, paginate, gen_code, empty_to_none, strip_id_from_json_column, apply_module_filter

router = APIRouter(prefix="/api/cases", tags=["测试用例"])

CASE_TYPES = ["功能", "接口", "UI", "性能", "回归"]
CASE_PRIORITY = ["P0", "P1", "P2", "P3"]
BATCH_MAX = 200
AI_CASE_MAX = 50

AI_SYSTEM = (
    "你是资深测试工程师，只输出 JSON，不要 markdown，不要解释。"
    "输出格式：{\"cases\":[{\"title\":\"\",\"precondition\":\"\",\"steps\":\"\",\"expected\":\"\","
    "\"case_type\":\"功能\",\"priority\":\"P2\",\"remark\":\"\"}]}"
    "case_type 只能是 功能/接口/UI/性能/回归 之一；priority 只能是 P0/P1/P2/P3。"
    "steps 用换行分隔的编号步骤，例如：1. xxx\\n2. xxx"
)


@router.get("")
def list_cases(page: int = 1, size: int = 10, keyword: str = "",
               project_id: int = 0, version_id: int = 0, module_id: int = 0,
               requirement_id: int = 0, case_type: str = "", suite_id: int = 0,
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestCase)
    if suite_id:
        from ..models import TestSuite
        from ..helpers import parse_id_list
        suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
        ids = parse_id_list(suite.case_ids) if suite else []
        q = q.filter(TestCase.id.in_(ids or [0]))
    if keyword:
        q = q.filter(TestCase.title.like(f"%{keyword}%") | TestCase.case_no.like(f"%{keyword}%"))
    if project_id:
        q = q.filter(TestCase.project_id == project_id)
    if version_id:
        q = q.filter(TestCase.version_id == version_id)
    q = apply_module_filter(q, TestCase, module_id)
    if requirement_id:
        q = q.filter(TestCase.requirement_id == requirement_id)
    if case_type:
        q = q.filter(TestCase.case_type == case_type)
    items, total = paginate(q.order_by(TestCase.id.desc()), page, size)
    data = []
    for c in items:
        d = row_to_dict(c)
        d["project_name"] = c.project.name if c.project else ""
        d["version_name"] = c.version.version_no if c.version else ""
        d["module_name"] = c.module.name if c.module else ""
        d["requirement_name"] = c.requirement.name if c.requirement else ""
        data.append(d)
    return {"items": data, "total": total}


@router.get("/all")
def all_cases(project_id: int = 0, version_id: int = 0, module_id: int = 0,
              db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestCase)
    if project_id:
        q = q.filter(TestCase.project_id == project_id)
    if version_id:
        q = q.filter(TestCase.version_id == version_id)
    q = apply_module_filter(q, TestCase, module_id)
    items = q.order_by(TestCase.id.desc()).all()
    return [{
        "id": c.id, "case_no": c.case_no, "title": c.title, "case_type": c.case_type,
        "priority": c.priority, "module_id": c.module_id,
        "module_name": c.module.name if c.module else "",
        "project_id": c.project_id, "version_id": c.version_id,
    } for c in items]


@router.get("/options")
def case_options(_=Depends(get_current_user)):
    return {"case_type": CASE_TYPES, "priority": CASE_PRIORITY}


def _norm_type(v):
    return v if v in CASE_TYPES else "功能"


def _norm_priority(v):
    return v if v in CASE_PRIORITY else "P2"


def _as_text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        lines = []
        for i, item in enumerate(v, 1):
            s = str(item).strip()
            if not s:
                continue
            if re.match(r"^\d+[\.、\)]\s*", s):
                lines.append(s)
            else:
                lines.append(f"{i}. {s}")
        return "\n".join(lines)
    return str(v).strip()


def _extract_json(text: str):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise HTTPException(status_code=502, detail="AI 返回内容无法解析为用例 JSON")


def _normalize_ai_cases(data):
    if isinstance(data, dict):
        items = data.get("cases") or data.get("items") or data.get("data") or []
        if isinstance(items, dict):
            items = [items]
    elif isinstance(data, list):
        items = data
    else:
        items = []
    out = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "title": title[:255],
            "precondition": _as_text(item.get("precondition") or item.get("preconditions")),
            "steps": _as_text(item.get("steps") or item.get("step")),
            "expected": _as_text(item.get("expected") or item.get("expected_result")),
            "case_type": _norm_type(item.get("case_type") or item.get("type")),
            "priority": _norm_priority(item.get("priority")),
            "remark": _as_text(item.get("remark")),
        })
        if len(out) >= AI_CASE_MAX:
            break
    return out


def _new_case(payload: dict) -> TestCase:
    return TestCase(
        title=str(payload.get("title") or "").strip(),
        precondition=payload.get("precondition") or "",
        steps=payload.get("steps") or "",
        expected=payload.get("expected") or "",
        case_type=_norm_type(payload.get("case_type")),
        priority=_norm_priority(payload.get("priority")),
        status=payload.get("status", 1),
        project_id=int(payload["project_id"]),
        version_id=int(payload["version_id"]),
        module_id=empty_to_none(payload.get("module_id")),
        requirement_id=empty_to_none(payload.get("requirement_id")),
        remark=payload.get("remark") or "",
    )


def _persist_cases(db: Session, rows: list[TestCase]):
    """逐条 flush 再编号：case_no 唯一且默认空串，批量 insert 会撞 Duplicate entry ''。"""
    for c in rows:
        db.add(c)
        db.flush()
        if not c.case_no:
            c.case_no = gen_code("TC", c.id)


@router.post("/ai-generate")
def ai_generate(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """只生成预览，不入库。"""
    requirement = (payload.get("requirement") or "").strip()
    prompt = (payload.get("prompt") or "").strip()
    if not requirement:
        raise HTTPException(status_code=400, detail="需求内容必填")
    if not prompt:
        raise HTTPException(status_code=400, detail="提示词必填")

    context_lines = []
    project_id = empty_to_none(payload.get("project_id"))
    version_id = empty_to_none(payload.get("version_id"))
    module_id = empty_to_none(payload.get("module_id"))
    requirement_id = empty_to_none(payload.get("requirement_id"))
    if project_id:
        p = db.query(Project).filter(Project.id == project_id).first()
        if p:
            context_lines.append(f"所属项目：{p.name}")
    if version_id:
        v = db.query(Version).filter(Version.id == version_id).first()
        if v:
            context_lines.append(f"所属版本：{v.version_no} {v.name or ''}".strip())
    if module_id:
        m = db.query(Module).filter(Module.id == module_id).first()
        if m:
            context_lines.append(f"所属模块：{m.name}")
    if requirement_id:
        r = db.query(Requirement).filter(Requirement.id == requirement_id).first()
        if r:
            context_lines.append(f"关联需求：{r.req_no} {r.name}")

    user_prompt = (
        f"{prompt}\n\n"
        + (("上下文：\n" + "\n".join(context_lines) + "\n\n") if context_lines else "")
        + f"需求内容：\n{requirement}\n"
    )
    try:
        raw = chat(user_prompt, system=AI_SYSTEM, temperature=0.2, timeout=120)
    except AIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    cases = _normalize_ai_cases(_extract_json(raw))
    if not cases:
        raise HTTPException(status_code=502, detail="AI 未生成有效用例，请调整需求内容或提示词后重试")
    return {"items": cases, "total": len(cases)}


@router.post("/batch")
def batch_create(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """批量保存勾选用例。单次最多 200 条，同项目+版本下标题重复则跳过。"""
    project_id = empty_to_none(payload.get("project_id"))
    version_id = empty_to_none(payload.get("version_id"))
    if not project_id or not version_id:
        raise HTTPException(status_code=400, detail="项目/版本必填")
    if not db.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(status_code=400, detail="项目不存在")
    if not db.query(Version).filter(Version.id == version_id, Version.project_id == project_id).first():
        raise HTTPException(status_code=400, detail="版本不存在或不属于该项目")

    module_id = empty_to_none(payload.get("module_id"))
    requirement_id = empty_to_none(payload.get("requirement_id"))
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="请至少选择一条用例")
    if len(items) > BATCH_MAX:
        raise HTTPException(status_code=400, detail=f"单次最多保存 {BATCH_MAX} 条")

    exist_titles = {
        (t or "").strip().lower()
        for (t,) in db.query(TestCase.title).filter(
            TestCase.project_id == project_id, TestCase.version_id == version_id
        ).all()
    }

    created, skipped, errors = [], [], []
    pending, seen = [], set()
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append({"index": i, "reason": "格式无效"})
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            errors.append({"index": i, "reason": "标题为空"})
            continue
        key = title.lower()
        if key in exist_titles or key in seen:
            skipped.append(title)
            continue
        seen.add(key)
        row = {
            **item,
            "title": title[:255],
            "project_id": project_id,
            "version_id": version_id,
            "module_id": empty_to_none(item.get("module_id")) or module_id,
            "requirement_id": empty_to_none(item.get("requirement_id")) or requirement_id,
            "status": 1,
        }
        pending.append(_new_case(row))

    if pending:
        _persist_cases(db, pending)
        db.commit()
        created = [{"id": c.id, "case_no": c.case_no, "title": c.title} for c in pending]
    else:
        db.rollback()

    return {
        "created": created,
        "created_count": len(created),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "errors": errors,
    }


@router.post("")
def create_case(payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not payload.get("title") or not payload.get("project_id") or not payload.get("version_id"):
        raise HTTPException(status_code=400, detail="标题/项目/版本必填")
    c = _new_case(payload)
    _persist_cases(db, [c])
    db.commit()
    return {"id": c.id, "case_no": c.case_no}


@router.put("/{cid}")
def update_case(cid: int, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(TestCase).filter(TestCase.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="用例不存在")
    for k in ("title", "precondition", "steps", "expected", "case_type", "priority",
              "status", "project_id", "version_id", "module_id", "requirement_id", "remark"):
        if k in payload:
            val = empty_to_none(payload[k]) if k in ("module_id", "requirement_id") else payload[k]
            setattr(c, k, val)
    db.commit()
    return {"id": cid}


@router.delete("/{cid}")
def delete_case(cid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(TestCase).filter(TestCase.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="用例不存在")
    db.query(Execution).filter(Execution.case_id == cid).delete(synchronize_session=False)
    db.query(Bug).filter(Bug.case_id == cid).update({Bug.case_id: None}, synchronize_session=False)
    strip_id_from_json_column(db, TestSuite, "case_ids", cid)
    strip_id_from_json_column(db, ReviewRecord, "target_ids", cid)
    db.delete(c)
    db.commit()
    return {"ok": True}
