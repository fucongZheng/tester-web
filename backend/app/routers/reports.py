"""测试报告：AI 聚合 + Jinja2 模板生成 + docx 导出"""
import io
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (TestReport, Project, Version, Requirement, TestCase,
                      Execution, Bug, FlowInstance)
from ..deps import get_current_user
from ..helpers import row_to_dict, gen_code
from ..ai_client import generate_text

router = APIRouter(prefix="/api/reports", tags=["测试报告"])

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def _aggregate(db, project_id, version_id):
    project = db.query(Project).filter(Project.id == project_id).first()
    version = db.query(Version).filter(Version.id == version_id).first()
    if not project or not version:
        raise HTTPException(status_code=400, detail="项目或版本不存在")

    reqs = db.query(Requirement).filter(Requirement.version_id == version_id).all()
    cases = db.query(TestCase).filter(TestCase.version_id == version_id).all()
    case_ids = [c.id for c in cases]
    execs = db.query(Execution).filter(Execution.case_id.in_(case_ids)).all() if case_ids else []
    bugs = db.query(Bug).filter(Bug.version_id == version_id).all()

    def count(seq, key):
        m = {}
        for x in seq:
            m[key(x)] = m.get(key(x), 0) + 1
        return m

    req_status = count(reqs, lambda r: r.status)
    bug_severity = count(bugs, lambda b: b.severity)
    bug_status = count(bugs, lambda b: b.status)
    bug_stage = count(bugs, lambda b: b.found_stage)
    bug_module = {}
    for b in bugs:
        name = b.module.name if b.module else "未分类"
        bug_module[name] = bug_module.get(name, 0) + 1

    exec_result = {"通过": 0, "失败": 0, "阻塞": 0, "跳过": 0, "未执行": 0}
    for e in execs:
        exec_result[e.result] = exec_result.get(e.result, 0) + 1
    executed_total = len(execs) - exec_result.get("未执行", 0)
    pass_count = exec_result.get("通过", 0)
    pass_rate = f"{pass_count / executed_total * 100:.1f}%" if executed_total else "0.0%"
    exec_ratio = {}
    for k, v in exec_result.items():
        exec_ratio[k] = f"{v / len(execs) * 100:.1f}%" if execs else "0.0%"

    flow = db.query(FlowInstance).filter(FlowInstance.version_id == version_id).first()
    flow_stage = flow.current_stage if flow else "未启动"
    flow_round = flow.current_round if flow else 1

    return {
        "project": project, "version": version,
        "req_total": len(reqs), "req_status": req_status,
        "case_total": len(cases),
        "executed_total": executed_total,
        "not_executed": exec_result.get("未执行", 0),
        "pass_rate": pass_rate, "exec_result": exec_result, "exec_ratio": exec_ratio,
        "bug_total": len(bugs), "bug_severity": bug_severity, "bug_status": bug_status,
        "bug_module": bug_module, "bug_stage": bug_stage,
        "flow_stage": flow_stage, "flow_round": flow_round,
    }


@router.get("")
def list_reports(page: int = 1, size: int = 10, project_id: int = 0,
                 db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(TestReport)
    if project_id:
        q = q.filter(TestReport.project_id == project_id)
    total = q.count()
    items = q.order_by(TestReport.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        d = row_to_dict(r)
        d["project_name"] = r.project.name if r.project else ""
        d["version_no"] = r.version.version_no if r.version else ""
        d.pop("content", None)
        d.pop("summary", None)
        data.append(d)
    return {"items": data, "total": total}


@router.post("/generate")
def generate_report(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    project_id = payload.get("project_id")
    version_id = payload.get("version_id")
    agg = _aggregate(db, project_id, version_id)
    title = payload.get("title") or f"{agg['project'].name}-{agg['version'].version_no}测试报告"

    ctx = {
        "title": title,
        "project_name": agg["project"].name,
        "version_no": agg["version"].version_no,
        "version_name": agg["version"].name,
        "start_date": agg["version"].start_date or "-",
        "launch_date": agg["version"].launch_date or "-",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "AI",
        "req_total": agg["req_total"], "req_status": agg["req_status"],
        "case_total": agg["case_total"], "executed_total": agg["executed_total"],
        "not_executed": agg["not_executed"], "pass_rate": agg["pass_rate"],
        "exec_result": agg["exec_result"], "exec_ratio": agg["exec_ratio"],
        "bug_total": agg["bug_total"], "bug_severity": agg["bug_severity"],
        "bug_status": agg["bug_status"], "bug_module": agg["bug_module"],
        "bug_stage": agg["bug_stage"],
        "flow_stage": agg["flow_stage"], "flow_round": agg["flow_round"],
    }
    template = _env.get_template("report.md.j2")
    content = template.render(**ctx)

    # 预留：AI 润色（当前 AI_ENABLED=false 时返回空，不影响）
    polish = generate_text("请为以下测试报告补充测试结论章节（保持 Markdown）：\n" + content)
    if polish:
        content = content.replace("> （本节由 AI 或测试负责人填写）", polish)

    r = TestReport(
        title=title, project_id=project_id, version_id=version_id,
        content=content, method="AI",
        generator=cur.real_name or cur.username,
    )
    db.add(r)
    db.flush()
    r.report_no = gen_code("RPT", r.id)
    db.commit()
    d = row_to_dict(r)
    d["project_name"] = r.project.name if r.project else ""
    d["version_no"] = r.version.version_no if r.version else ""
    return d


@router.get("/{rid}")
def get_report(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(TestReport).filter(TestReport.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="报告不存在")
    d = row_to_dict(r)
    d["project_name"] = r.project.name if r.project else ""
    d["version_no"] = r.version.version_no if r.version else ""
    return d


@router.delete("/{rid}")
def delete_report(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(TestReport).filter(TestReport.id == rid).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


@router.get("/{rid}/export")
def export_report(rid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(TestReport).filter(TestReport.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="报告不存在")
    doc_bytes = markdown_to_docx(r.content, r.title)
    filename = f"{r.title or r.report_no}.docx"
    return StreamingResponse(
        io.BytesIO(doc_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def markdown_to_docx(md_text: str, title: str) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.add_heading(title or "测试报告", 0)
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|---"):
            # Markdown 表格
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            table = doc.add_table(rows=1, cols=len(header))
            table.style = "Light Grid Accent 1"
            for j, h in enumerate(header):
                table.rows[0].cells[j].text = h
            i += 2  # 跳过分隔行
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                row = table.add_row()
                for j, c in enumerate(cells[:len(header)]):
                    row.cells[j].text = c
                i += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("> "):
            doc.add_paragraph(line[2:])
        else:
            doc.add_paragraph(line)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
