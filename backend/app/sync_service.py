"""需求同步服务：从 xuqiu 需求系统开放 API 拉取需求，幂等 upsert 到本地。

约定：
- xuqiu 是需求事实源。同步只覆盖 名称/内容/归属(项目/版本)，不碰本地的
  status/priority/module 等测试团队自己维护的字段。
- 项目/版本按名称自动匹配，匹配不上自动建档（xuqiu projectName → Project.name，
  versionCode → Version.version_no）。
- 远端已删除的需求只报告不删本地（本地可能挂着用例/BUG）。
- 幂等：按 (source_system, source_id) 定位；字段值没变就不动，重复执行结果一致。
"""
import json
import urllib.request

from sqlalchemy.orm import Session

from .ai_prompts import MODE_LABELS, build_user_prompt
from .config import settings
from .helpers import gen_code
from .models import Project, Requirement, SyncLog, TestCase, Version
from .routers.cases import _new_case, _persist_cases, generate_cases_for_text

SOURCE = "xuqiu"

# 同步自动生成的模式与顺序：先闭环（主链路放前）再细节（字段级加厚），两份 skill 互补
SYNC_CASE_MODES = ("loop", "detail")

# 本机注册表可能挂着系统代理，会劫持 127.0.0.1 直连请求——显式空代理直连
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get(path: str):
    req = urllib.request.Request(
        settings.XUQIU_BASE_URL.rstrip("/") + path,
        headers={"X-API-Key": settings.XUQIU_API_KEY},
    )
    with _opener.open(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_placement(db: Session, remote: dict, ver_dates: dict) -> tuple[int, int]:
    """项目/版本按名匹配，缺了自动建档；返回 (project_id, version_id)。"""
    proj_name = (remote.get("projectName") or "").strip() or "未归属项目"
    project = db.query(Project).filter(Project.name == proj_name).first()
    if not project:
        project = Project(name=proj_name, owner=(remote.get("author") or "")[:64])
        db.add(project)
        db.flush()
    ver_no = (remote.get("versionCode") or "").strip() or "v1.0.0"
    version = (
        db.query(Version)
        .filter(Version.project_id == project.id, Version.version_no == ver_no)
        .first()
    )
    if not version:
        start, due = ver_dates.get(remote.get("versionId"), ("", ""))
        version = Version(
            version_no=ver_no,
            name=ver_no,
            project_id=project.id,
            start_date=start,
            launch_date=due,
        )
        db.add(version)
        db.flush()
    return project.id, version.id


def _ai_gen_cases(db: Session, req: Requirement) -> tuple[int, str]:
    """对单个需求按双 skill（先闭环后细节）生成用例并直接入库（同步新增时调用一次）。

    返回 (生成条数, 说明)。任一模式 AI 未配置 / 失败只记录原因，不影响另一模式，
    更绝不抛异常——用例生成是同步的增值动作，不能拖垮同步本身。
    """
    content = (req.content or "").strip()
    if not content:
        return 0, "AI 用例未生成（需求内容为空）"
    user_prompt = build_user_prompt(content, [f"关联需求：{req.req_no} {req.name}"])
    exist = {
        (t or "").strip().lower()
        for (t,) in db.query(TestCase.title).filter(
            TestCase.project_id == req.project_id, TestCase.version_id == req.version_id
        ).all()
    }
    rows, notes = [], []
    for mode in SYNC_CASE_MODES:
        try:
            items = generate_cases_for_text(mode, user_prompt)
        except Exception as exc:
            reason = getattr(exc, "detail", None) or str(exc)
            notes.append(f"{MODE_LABELS[mode]}未生成（{reason}）")
            continue
        added = 0
        for it in items:
            key = it["title"].lower()
            if key in exist:
                continue
            exist.add(key)
            rows.append(_new_case({**it, "project_id": req.project_id, "version_id": req.version_id,
                                   "requirement_id": req.id, "module_id": req.module_id, "status": 1}))
            added += 1
        if added:
            notes.append(f"{MODE_LABELS[mode]} {added} 条")
        elif items:
            notes.append(f"{MODE_LABELS[mode]}全部重复未入库")
    if not rows:
        return 0, "AI 用例未生成（" + "；".join(notes) + "）"
    _persist_cases(db, rows)
    db.commit()
    return len(rows), f"AI 生成用例 {len(rows)} 条（{'，'.join(notes)}）"


def run_sync(db: Session, trigger: str = "manual") -> dict:
    stats = {"created_count": 0, "updated_count": 0, "skipped_count": 0,
             "missing_count": 0, "failed_count": 0, "cases_count": 0}
    detail: list[str] = []

    def _finish(status: str) -> dict:
        db.add(SyncLog(trigger=trigger, status=status, detail="\n".join(detail), **stats))
        db.commit()
        out = {"ok": status == "ok", **stats, "detail": detail}
        return out

    try:
        remote = _get("/open/requirements").get("requirements", [])
        ver_dates = {
            v["id"]: ((v.get("startAt") or "")[:10], (v.get("dueAt") or "")[:10])
            for v in _get("/open/projects").get("versions", [])
        }
    except Exception as exc:
        return {**_finish("failed"), "error": f"拉取 xuqiu 失败：{exc}"}

    for r in remote:
        rid = r.get("id") or ""
        name = r.get("name") or "(未命名)"
        try:
            local = (
                db.query(Requirement)
                .filter(Requirement.source_system == SOURCE, Requirement.source_id == rid)
                .first()
            )
            project_id, version_id = _resolve_placement(db, r, ver_dates)
            if local is None:
                local = Requirement(
                    name=name,
                    content=r.get("markdown") or "",
                    status="待开发",
                    priority="P2",
                    project_id=project_id,
                    version_id=version_id,
                    source_system=SOURCE,
                    source_id=rid,
                )
                db.add(local)
                db.flush()
                local.req_no = gen_code("REQ", local.id)
                db.commit()
                stats["created_count"] += 1
                detail.append(f"新增 {local.req_no} {local.name}")
                if settings.SYNC_AUTO_CASES:
                    n, msg = _ai_gen_cases(db, local)
                    stats["cases_count"] += n
                    detail.append(f"　↳ {msg}")
            else:
                changed = []
                if local.name != name:
                    local.name = name
                    changed.append("名称")
                if local.content != (r.get("markdown") or ""):
                    local.content = r.get("markdown") or ""
                    changed.append("内容")
                if (local.project_id, local.version_id) != (project_id, version_id):
                    local.project_id, local.version_id = project_id, version_id
                    changed.append("归属")
                if changed:
                    db.commit()
                    stats["updated_count"] += 1
                    detail.append(f"更新 {local.req_no} {local.name}（{'、'.join(changed)}）")
                else:
                    stats["skipped_count"] += 1
        except Exception as exc:
            db.rollback()
            stats["failed_count"] += 1
            detail.append(f"失败 {name}：{exc}")

    # 对账：本地来自 xuqiu 但远端已没有的，报告（本地保留）
    remote_ids = {r.get("id") for r in remote}
    for local in db.query(Requirement).filter(Requirement.source_system == SOURCE).all():
        if local.source_id and local.source_id not in remote_ids:
            stats["missing_count"] += 1
            detail.append(f"源已删除（本地保留）：{local.req_no} {local.name}")

    return _finish("ok")
