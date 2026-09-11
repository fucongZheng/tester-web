"""质量快照：把看板/覆盖/流程/BUG 收成一份给 AI 解读的 JSON。"""
from datetime import datetime

from .models import (Project, Version, Requirement, TestCase, Execution, Bug,
                     FlowInstance, Handover, LaunchRequest, ReviewRecord)


def _stage_label(stage_no, round_no):
    names = {
        0: "测试验证开发提测",
        1: "AI接口测试(代码测试)",
        2: "AI界面测试",
        3: f"人工第{round_no or 1}轮测试",
        4: "回归测试",
        5: "产品验收",
        6: "上线+生产环境验证",
    }
    if stage_no == 3:
        return names[3]
    return names.get(stage_no, f"环节{stage_no}")

CLOSED = {"测试验证通过关闭", "不是BUG"}
SEV_ORDER = ["致命", "严重", "一般", "轻微", "建议"]
MAX_LIST = 20


def _pct(n, d):
    return round(n / d * 100, 1) if d else 0.0


def _count(seq, key):
    m = {}
    for x in seq:
        k = key(x) or "未填写"
        m[k] = m.get(k, 0) + 1
    return m


def _link(path, project_id=0, version_id=0, extra=None):
    q = []
    if project_id:
        q.append(f"project_id={int(project_id)}")
    if version_id:
        q.append(f"version_id={int(version_id)}")
    if extra:
        for k, v in extra.items():
            if v is not None and v != "":
                q.append(f"{k}={v}")
    return path + (("?" + "&".join(q)) if q else "")


def _item(kind, no, name, **extra):
    d = {"no": no or "", "name": name or ""}
    d.update({k: v for k, v in extra.items() if v is not None})
    kw = no or name
    path = {"requirement": "/requirement", "case": "/case", "bug": "/bug"}.get(kind, "/")
    d["link"] = _link(path, extra.get("project_id", 0), extra.get("version_id", 0),
                      {"keyword": kw} if kw else None)
    return d


def _days_ago(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    return max(0, (datetime.now() - dt).days)


def _latest_execs(execs):
    latest = {}
    for e in execs:
        prev = latest.get(e.case_id)
        if not prev or (e.id or 0) > (prev.id or 0):
            latest[e.case_id] = e
    return latest


def _bug_open(bugs):
    return [b for b in bugs if b.status not in CLOSED]


def _risk(fatal, severe, overflow, uncovered, pass_rate, stuck_days, case_total):
    reasons = []
    if fatal:
        reasons.append(f"未关闭致命 BUG {fatal} 个")
    if overflow:
        reasons.append(f"线上溢出 {overflow} 个")
    if severe:
        reasons.append(f"未关闭严重 BUG {severe} 个")
    if uncovered:
        reasons.append(f"无用例需求 {uncovered} 个")
    if case_total and pass_rate is not None and pass_rate < 90:
        reasons.append(f"执行通过率 {pass_rate}%")
    if stuck_days is not None and stuck_days >= 7:
        reasons.append(f"流程已停留 {stuck_days} 天")
    if fatal or overflow:
        level = "red"
    elif severe or uncovered or (case_total and pass_rate is not None and pass_rate < 90) or (
            stuck_days is not None and stuck_days >= 7):
        level = "yellow"
    else:
        level = "green"
    if not reasons:
        reasons.append("未发现阻断项")
    return level, reasons


def _resolve_scope(db, project_id, version_id):
    project = version = None
    if version_id:
        version = db.query(Version).filter(Version.id == version_id).first()
        if not version:
            return None, None, "版本不存在"
        if project_id and version.project_id != project_id:
            return None, None, "版本不属于所选项目"
        project_id = version.project_id
    if project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None, None, "项目不存在"
    return project, version, ""


def build_snapshot(db, project_id=0, version_id=0):
    project, version, err = _resolve_scope(db, project_id or 0, version_id or 0)
    if err:
        return None, err
    pid = project.id if project else 0
    vid = version.id if version else 0

    rq = db.query(Requirement)
    cq = db.query(TestCase)
    bq = db.query(Bug)
    if pid:
        rq, cq, bq = rq.filter(Requirement.project_id == pid), cq.filter(TestCase.project_id == pid), bq.filter(Bug.project_id == pid)
    if vid:
        rq, cq, bq = rq.filter(Requirement.version_id == vid), cq.filter(TestCase.version_id == vid), bq.filter(Bug.version_id == vid)
    reqs, cases, bugs = rq.all(), cq.all(), bq.all()

    case_ids = [c.id for c in cases]
    execs = db.query(Execution).filter(Execution.case_id.in_(case_ids)).all() if case_ids else []
    latest = _latest_execs(execs)
    exec_result = {"通过": 0, "失败": 0, "阻塞": 0, "跳过": 0, "未执行": 0}
    for e in latest.values():
        exec_result[e.result] = exec_result.get(e.result, 0) + 1
    not_executed = exec_result.get("未执行", 0) + max(0, len(cases) - len(latest))
    executed_total = len(cases) - not_executed
    pass_count = exec_result.get("通过", 0)
    pass_rate = _pct(pass_count, executed_total)

    cases_by_req = {}
    for c in cases:
        if c.requirement_id:
            cases_by_req.setdefault(c.requirement_id, []).append(c)
    uncovered = [r for r in reqs if r.id not in cases_by_req]
    uncovered_items = [_item("requirement", r.req_no, r.name, id=r.id, priority=r.priority,
                             status=r.status, project_id=pid, version_id=vid)
                       for r in uncovered[:MAX_LIST]]

    unexec_cases = []
    for c in cases:
        e = latest.get(c.id)
        if not e or e.result == "未执行":
            unexec_cases.append(c)
    unexec_items = [_item("case", c.case_no, c.title, id=c.id, priority=c.priority,
                          project_id=pid, version_id=vid)
                    for c in unexec_cases[:MAX_LIST]]

    open_bugs = _bug_open(bugs)
    fatal = [b for b in open_bugs if b.severity == "致命"]
    severe = [b for b in open_bugs if b.severity == "严重"]
    overflow = [b for b in bugs if b.found_stage == "线上溢出"]
    critical = (fatal + severe)[:MAX_LIST]
    critical_items = [_item("bug", b.bug_no, b.title, id=b.id, severity=b.severity,
                            status=b.status, module=b.module.name if b.module else "未分类",
                            project_id=pid, version_id=vid) for b in critical]

    bug_module = {}
    for b in bugs:
        name = b.module.name if b.module else "未分类"
        d = bug_module.setdefault(name, {"name": name, "total": 0, "open": 0})
        d["total"] += 1
        if b.status not in CLOSED:
            d["open"] += 1
    bug_module_list = sorted(bug_module.values(), key=lambda x: (-x["open"], -x["total"]))[:10]

    fq = db.query(FlowInstance)
    if pid:
        fq = fq.filter(FlowInstance.project_id == pid)
    if vid:
        fq = fq.filter(FlowInstance.version_id == vid)
    flows = fq.order_by(FlowInstance.id.desc()).all()
    flow = flows[0] if vid and flows else None
    stuck = []
    reject_n = 0
    for f in flows:
        days = _days_ago(f.updated_at or f.started_at)
        if f.status == "进行中" and days is not None and days >= 7:
            stuck.append({
                "project": f.project.name if f.project else "",
                "version": f.version.version_no if f.version else "",
                "stage": _stage_label(f.current_stage, f.current_round),
                "status": f.status, "stuck_days": days,
                "link": "/flow",
            })
        reject_n += sum(1 for s in (f.stages or []) if s.stage_no == 5 and s.status == "驳回")
    stuck = stuck[:MAX_LIST]

    flow_info = {
        "status": "未启动", "stage": "", "round": 0, "stuck_days": None,
        "acceptance_rejected": reject_n, "link": "/flow",
    }
    if flow:
        flow_info.update({
            "status": flow.status,
            "stage": _stage_label(flow.current_stage, flow.current_round),
            "round": flow.current_round,
            "stuck_days": _days_ago(flow.updated_at or flow.started_at) if flow.status == "进行中" else 0,
            "acceptance_rejected": sum(1 for s in (flow.stages or []) if s.stage_no == 5 and s.status == "驳回"),
        })
    elif not vid:
        running = [f for f in flows if f.status == "进行中"]
        flow_info.update({
            "status": f"进行中 {len(running)} / 共 {len(flows)}",
            "stuck_days": max([s["stuck_days"] for s in stuck], default=0) if stuck else 0,
        })

    hq = db.query(Handover)
    lq = db.query(LaunchRequest)
    rvq = db.query(ReviewRecord)
    if pid:
        hq, lq, rvq = hq.filter(Handover.project_id == pid), lq.filter(LaunchRequest.project_id == pid), rvq.filter(ReviewRecord.project_id == pid)
    if vid:
        hq, lq, rvq = hq.filter(Handover.version_id == vid), lq.filter(LaunchRequest.version_id == vid), rvq.filter(ReviewRecord.version_id == vid)
    handovers, launches, reviews = hq.all(), lq.all(), rvq.all()
    latest_launch = max(launches, key=lambda x: x.id) if launches else None

    compare = None
    if version:
        prev = (db.query(Version).filter(Version.project_id == version.project_id, Version.id < version.id)
                .order_by(Version.id.desc()).first())
        if prev:
            prev_bugs = db.query(Bug).filter(Bug.version_id == prev.id).all()
            prev_reqs = db.query(Requirement).filter(Requirement.version_id == prev.id).all()
            prev_cases = db.query(TestCase).filter(TestCase.version_id == prev.id).all()
            prev_linked = {c.requirement_id for c in prev_cases if c.requirement_id}
            compare = {
                "version_no": prev.version_no,
                "bug_open": len(_bug_open(prev_bugs)),
                "bug_total": len(prev_bugs),
                "req_total": len(prev_reqs),
                "uncovered": sum(1 for r in prev_reqs if r.id not in prev_linked),
                "case_total": len(prev_cases),
            }

    stuck_days = flow_info.get("stuck_days")
    level, reasons = _risk(len(fatal), len(severe), len(overflow), len(uncovered),
                           pass_rate, stuck_days, len(cases))
    bug_sev = _count(bugs, lambda b: b.severity)

    snap = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scope": {
            "project_id": pid or None,
            "project_name": project.name if project else "全库",
            "version_id": vid or None,
            "version_no": version.version_no if version else "",
            "version_name": version.name if version else "",
            "version_status": version.status if version else "",
            "launch_date": version.launch_date if version else "",
        },
        "risk_level": level,
        "risk_reasons": reasons,
        "counts": {
            "requirement": len(reqs),
            "case": len(cases),
            "executed": executed_total,
            "not_executed": not_executed,
            "bug": len(bugs),
            "bug_open": len(open_bugs),
            "bug_fatal_open": len(fatal),
            "bug_severe_open": len(severe),
            "bug_online_overflow": len(overflow),
        },
        "coverage": {
            "req_with_case": len(reqs) - len(uncovered),
            "req_without_case_count": len(uncovered),
            "coverage_rate": _pct(len(reqs) - len(uncovered), len(reqs)),
            "pass_rate": pass_rate,
            "exec_result": exec_result,
            "req_without_case": uncovered_items,
            "case_not_executed": unexec_items,
        },
        "bugs": {
            "by_severity": {k: bug_sev.get(k, 0) for k in SEV_ORDER},
            "by_status": _count(bugs, lambda b: b.status),
            "by_stage": _count(bugs, lambda b: b.found_stage),
            "by_module": bug_module_list,
            "open_critical": critical_items,
        },
        "flow": flow_info,
        "stuck_flows": stuck,
        "handover": {
            "total": len(handovers),
            "by_status": _count(handovers, lambda h: h.status),
        },
        "launch": {
            "total": len(launches),
            "by_status": _count(launches, lambda x: x.status),
            "latest": ({
                "no": latest_launch.launch_no, "title": latest_launch.title,
                "status": latest_launch.status, "plan_date": latest_launch.plan_date,
                "link": "/launch",
            } if latest_launch else None),
        },
        "reviews": {
            "total": len(reviews),
            "by_type": _count(reviews, lambda r: r.review_type),
            "by_result": _count(reviews, lambda r: r.result),
        },
        "compare": compare,
        "links": {
            "requirement": _link("/requirement", pid, vid),
            "case": _link("/case", pid, vid),
            "bug": _link("/bug", pid, vid),
            "bug_open": _link("/bug", pid, vid),
            "flow": "/flow",
            "launch": "/launch",
            "review": _link("/review", pid, vid),
            "report": _link("/report", pid, vid),
        },
    }
    return snap, ""


def fallback_answer(snap, question=""):
    s = snap or {}
    scope = s.get("scope") or {}
    counts = s.get("counts") or {}
    cov = s.get("coverage") or {}
    flow = s.get("flow") or {}
    level_map = {"red": "红（不建议上线）", "yellow": "黄（带风险）", "green": "绿（未见阻断）"}
    level = level_map.get(s.get("risk_level"), s.get("risk_level") or "-")
    where = scope.get("project_name") or "全库"
    if scope.get("version_no"):
        where += f" / {scope['version_no']}"
    reasons = s.get("risk_reasons") or []
    uncovered = cov.get("req_without_case") or []
    critical = (s.get("bugs") or {}).get("open_critical") or []
    lines = [
        f"**结论**：{where} 当前风险 {level}。",
        "",
        "**依据**：",
        f"- 需求 {counts.get('requirement', 0)}，用例 {counts.get('case', 0)}，"
        f"覆盖率 {cov.get('coverage_rate', 0)}%，执行通过率 {cov.get('pass_rate', 0)}%",
        f"- 未关闭 BUG {counts.get('bug_open', 0)}（致命 {counts.get('bug_fatal_open', 0)} /"
        f" 严重 {counts.get('bug_severe_open', 0)}），线上溢出 {counts.get('bug_online_overflow', 0)}",
        f"- 流程：{flow.get('stage') or flow.get('status') or '未启动'}"
        + (f"，已停留 {flow.get('stuck_days')} 天" if flow.get("stuck_days") else ""),
    ]
    for r in reasons[:6]:
        if r not in "".join(lines):
            lines.append(f"- {r}")
    if uncovered:
        names = "、".join((x.get("no") or x.get("name")) for x in uncovered[:5])
        lines.append(f"- 无用例需求：{names}" + ("…" if len(uncovered) > 5 else ""))
    if critical:
        names = "、".join((x.get("no") or x.get("name")) for x in critical[:5])
        lines.append(f"- 未关闭致命/严重：{names}" + ("…" if len(critical) > 5 else ""))
    lines += ["", "**建议**："]
    if s.get("risk_level") == "red":
        lines.append("- 先关闭全部致命 BUG，并核对线上溢出是否已回归，再谈上线。")
    elif s.get("risk_level") == "yellow":
        lines.append("- 补齐无用例需求与未关闭严重缺陷后再提验收；流程停留过久的版本优先推进。")
    else:
        lines.append("- 按现有流程走完回归与产品验收即可，上线前再扫一遍未关闭缺陷。")
    if question:
        lines.append(f"- 以上根据系统数据回答「{question.strip()[:40]}」，未使用的编号请忽略。")
    return "\n".join(lines)


AI_SYSTEM = (
    "你是测试管理系统的质量参谋，只服务管理员做上线与质量判断。"
    "必须只根据用户消息里的【质量快照 JSON】回答，禁止编造编号、数字、模块名。"
    "快照没有的信息就说数据里没有，不要猜测。"
    "用中文 Markdown，严格分三块，不要写开场白："
    "1. **结论**：一句话 + 风险（红/黄/绿）和原因；"
    "2. **依据**：3～6 条，数字必须能在快照里找到；"
    "3. **建议**：管理员下一步可执行动作（不要让 AI 去改数据或关 BUG）。"
    "需要点名时用快照里的 no（如 BUG-0001、REQ-0002）。"
    "不要输出 JSON，不要重复粘贴整份快照。"
)


def build_user_prompt(question, snap, history=None):
    import json
    parts = []
    if history:
        parts.append("【最近对话】")
        for m in history:
            role = "管理员" if m.get("role") == "user" else "参谋"
            parts.append(f"{role}：{(m.get('content') or '')[:500]}")
    parts.append("【质量快照 JSON】")
    parts.append(json.dumps(snap, ensure_ascii=False, default=str))
    parts.append("【管理员问题】")
    parts.append(question.strip())
    return "\n".join(parts)


QUICK_VERSION = [
    "这个版本能不能上线？",
    "未覆盖需求有哪些？",
    "未关闭的致命/严重 BUG",
    "流程卡在哪一环？",
    "哪个模块 BUG 最多？",
    "和上一版本比质量如何？",
]

QUICK_GLOBAL = [
    "当前有哪些版本不适合上线？",
    "全库未关闭的致命/严重 BUG",
    "哪些流程卡住超过一周？",
    "哪个模块 BUG 最多？",
    "近期线上溢出情况如何？",
]
