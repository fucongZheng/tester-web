"""管理员 AI 问质：质量快照 + 会话问答。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai_client import AIError, chat
from ..database import get_db
from ..deps import require_admin
from ..helpers import row_to_dict, paginate
from ..models import AiQaSession, AiQaMessage, SysUser
from ..quality import (AI_SYSTEM, QUICK_GLOBAL, QUICK_VERSION, build_snapshot,
                       build_user_prompt, fallback_answer)

router = APIRouter(prefix="/api/aiqa", tags=["AI问质"], dependencies=[Depends(require_admin)])


def _session_dict(s: AiQaSession, with_messages=False):
    d = row_to_dict(s)
    d["project_name"] = s.project.name if s.project else ""
    d["version_no"] = s.version.version_no if s.version else ""
    if with_messages:
        msgs = []
        for m in s.messages:
            md = row_to_dict(m)
            if md.get("snapshot"):
                try:
                    md["snapshot"] = json.loads(md["snapshot"])
                except Exception:
                    md["snapshot"] = None
            else:
                md["snapshot"] = None
            msgs.append(md)
        d["messages"] = msgs
    return d


def _title_from(question: str):
    t = (question or "").strip().replace("\n", " ")
    return (t[:28] + "…") if len(t) > 28 else (t or "新会话")


@router.get("/quick")
def quick_questions(project_id: int = 0, version_id: int = 0):
    return {"items": QUICK_VERSION if version_id else QUICK_GLOBAL}


@router.get("/snapshot")
def get_snapshot(project_id: int = 0, version_id: int = 0, db: Session = Depends(get_db)):
    snap, err = build_snapshot(db, project_id, version_id)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return snap


@router.get("/sessions")
def list_sessions(page: int = 1, size: int = 20, db: Session = Depends(get_db),
                  user: SysUser = Depends(require_admin)):
    q = db.query(AiQaSession).filter(AiQaSession.user_id == user.id).order_by(AiQaSession.id.desc())
    items, total = paginate(q, page, size)
    return {"items": [_session_dict(s) for s in items], "total": total}


@router.get("/sessions/{sid}")
def get_session(sid: int, db: Session = Depends(get_db), user: SysUser = Depends(require_admin)):
    s = db.query(AiQaSession).filter(AiQaSession.id == sid, AiQaSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _session_dict(s, with_messages=True)


@router.delete("/sessions/{sid}")
def delete_session(sid: int, db: Session = Depends(get_db), user: SysUser = Depends(require_admin)):
    s = db.query(AiQaSession).filter(AiQaSession.id == sid, AiQaSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/ask")
def ask(payload: dict, db: Session = Depends(get_db), user: SysUser = Depends(require_admin)):
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="请输入问题")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="问题过长")
    project_id = int(payload.get("project_id") or 0)
    version_id = int(payload.get("version_id") or 0)
    session_id = int(payload.get("session_id") or 0)

    snap, err = build_snapshot(db, project_id, version_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    sess = None
    history = []
    if session_id:
        sess = db.query(AiQaSession).filter(AiQaSession.id == session_id, AiQaSession.user_id == user.id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        history = [{"role": m.role, "content": m.content} for m in (sess.messages or [])[-6:]]
    else:
        sess = AiQaSession(
            user_id=user.id,
            title=_title_from(question),
            project_id=project_id or None,
            version_id=version_id or None,
        )
        db.add(sess)
        db.flush()

    sess.project_id = project_id or None
    sess.version_id = version_id or None
    sess.risk_level = snap.get("risk_level") or ""
    if not sess.title:
        sess.title = _title_from(question)

    user_msg = AiQaMessage(session_id=sess.id, role="user", content=question)
    db.add(user_msg)
    db.flush()

    ai_used = False
    try:
        answer = chat(build_user_prompt(question, snap, history), system=AI_SYSTEM,
                      temperature=0.2, timeout=90)
        if not (answer or "").strip():
            raise AIError("空回复")
        ai_used = True
    except AIError as e:
        prefix = ""
        if "未配置" in str(e):
            prefix = "> 未配置 AI，以下为系统根据质量快照直接汇总。可在「系统管理 → API管理」启用模型后获得解读。\n\n"
        else:
            prefix = f"> AI 调用失败（{e}），以下为系统根据质量快照直接汇总。\n\n"
        answer = prefix + fallback_answer(snap, question)

    asst = AiQaMessage(
        session_id=sess.id, role="assistant", content=answer,
        snapshot=json.dumps(snap, ensure_ascii=False, default=str),
    )
    db.add(asst)
    db.commit()
    db.refresh(sess)
    return {
        "session_id": sess.id,
        "title": sess.title,
        "risk_level": sess.risk_level,
        "ai_used": ai_used,
        "answer": answer,
        "snapshot": snap,
        "session": _session_dict(sess, with_messages=True),
    }
