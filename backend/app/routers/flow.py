"""测试流程状态机"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (FlowInstance, FlowStage, Version, TestSuite, Execution,
                      TestCase, Handover, TestReport, LaunchRequest)
from ..deps import get_current_user, require_admin
from ..helpers import row_to_dict, parse_json_list, parse_id_list

router = APIRouter(prefix="/api/flow", tags=["测试流程"])

STAGE_NAMES = {
    0: "测试验证开发提测",
    1: "AI接口测试(代码测试)",
    2: "AI界面测试",
    3: "人工测试",        # 展示时拼“人工第N轮测试”
    4: "回归测试",
    5: "产品验收",
    6: "上线+生产环境验证",
}


def stage_label(stage_no: int, round_no: int) -> str:
    if stage_no == 3:
        return f"人工第{round_no}轮测试"
    return STAGE_NAMES.get(stage_no, f"环节{stage_no}")


def _instance_dict(inst: FlowInstance):
    d = row_to_dict(inst)
    d["project_name"] = inst.project.name if inst.project else ""
    d["version_no"] = inst.version.version_no if inst.version else ""
    d["current_stage_label"] = stage_label(inst.current_stage, inst.current_round)
    stages = []
    for s in inst.stages:
        sd = row_to_dict(s)
        sd["attachments"] = parse_json_list(s.attachments)
        stages.append(sd)
    d["stages"] = stages
    return d


@router.get("")
def list_flows(project_id: int = 0, version_id: int = 0,
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(FlowInstance)
    if project_id:
        q = q.filter(FlowInstance.project_id == project_id)
    if version_id:
        q = q.filter(FlowInstance.version_id == version_id)
    items = q.order_by(FlowInstance.id.desc()).all()
    return [_instance_dict(i) for i in items]


def ensure_flow(db: Session, project_id: int, version_id: int, operator: str = "", commit: bool = True):
    """按版本启动或恢复流程，从环节 0（测试验证开发提测）开始。"""
    existing = db.query(FlowInstance).filter(
        FlowInstance.version_id == version_id,
        FlowInstance.status.in_(["进行中", "已挂起"]),
    ).order_by(FlowInstance.id.desc()).first()
    if existing:
        if existing.status == "已挂起":
            existing.status = "进行中"
            existing.current_stage = 0
            db.add(FlowStage(
                instance_id=existing.id, stage_no=0,
                stage_name=stage_label(0, existing.current_round or 1),
                round_no=existing.current_round or 1, status="进行中",
                started_at=datetime.now(), operator=operator,
                remark="开发重新提测",
            ))
            if commit:
                db.commit()
                db.refresh(existing)
        return existing
    inst = FlowInstance(project_id=project_id, version_id=version_id,
                        current_stage=0, current_round=1, status="进行中")
    db.add(inst)
    db.flush()
    db.add(FlowStage(
        instance_id=inst.id, stage_no=0,
        stage_name=stage_label(0, 1), round_no=1,
        status="进行中", started_at=datetime.now(), operator=operator,
    ))
    if commit:
        db.commit()
        db.refresh(inst)
    return inst


def _latest_handover(db, version_id):
    return db.query(Handover).filter(Handover.version_id == version_id).order_by(Handover.id.desc()).first()


@router.post("/start")
def start_flow(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    project_id = payload.get("project_id")
    version_id = payload.get("version_id")
    if not project_id or not version_id:
        raise HTTPException(status_code=400, detail="项目和版本必填")
    inst = ensure_flow(db, project_id, version_id, operator=cur.real_name or cur.username)
    return _instance_dict(inst)


def _current_stage_record(db, inst):
    return db.query(FlowStage).filter(
        FlowStage.instance_id == inst.id,
        FlowStage.stage_no == inst.current_stage,
        FlowStage.round_no == inst.current_round,
        FlowStage.status == "进行中",
    ).order_by(FlowStage.id.desc()).first()


def _ensure_suite_executed(db, inst, suite_type: str):
    """指定类型套件必须存在，且套件内用例全部已执行。"""
    suites = db.query(TestSuite).filter(
        TestSuite.project_id == inst.project_id,
        TestSuite.version_id == inst.version_id,
        TestSuite.suite_type == suite_type,
    ).all()
    if not suites:
        raise HTTPException(
            status_code=400,
            detail=f"当前项目/版本尚未创建「{suite_type}」套件，上一环节未完成，不能进入下一环节",
        )
    pending = []
    empty_suites = []
    for s in suites:
        ids = parse_id_list(s.case_ids)
        if not ids:
            empty_suites.append(s.name)
            continue
        for cid in ids:
            latest = db.query(Execution).filter(Execution.case_id == cid).order_by(Execution.id.desc()).first()
            if not latest or latest.result == "未执行":
                case = db.query(TestCase).filter(TestCase.id == cid).first()
                pending.append(f"{s.name}/{case.case_no or case.title if case else cid}")
    if empty_suites:
        raise HTTPException(
            status_code=400,
            detail=f"套件「{'、'.join(empty_suites)}」尚未选择用例，上一环节未完成",
        )
    if pending:
        sample = "、".join(pending[:8])
        more = f" 等{len(pending)}条" if len(pending) > 8 else ""
        raise HTTPException(
            status_code=400,
            detail=f"「{suite_type}」套件中仍有未执行用例（{sample}{more}），上一环节未完成，不能进入下一环节",
        )


def _ensure_stage_gate(db, inst):
    """上一环节没完成不允许进入下一环节。"""
    stage = inst.current_stage
    if stage == 0:
        h = _latest_handover(db, inst.version_id)
        if not h:
            raise HTTPException(status_code=400, detail="尚未提交开发提测，不能通过提测验证")
        if h.smoke_executed != "已执行":
            raise HTTPException(status_code=400, detail="冒烟用例尚未执行完成，不能进入下一环节")
        if h.suite_id:
            suite = db.query(TestSuite).filter(TestSuite.id == h.suite_id).first()
            if suite:
                ids = parse_id_list(suite.case_ids)
                pending = []
                for cid in ids:
                    latest = db.query(Execution).filter(Execution.case_id == cid).order_by(Execution.id.desc()).first()
                    if not latest or latest.result == "未执行":
                        case = db.query(TestCase).filter(TestCase.id == cid).first()
                        pending.append(case.case_no or case.title if case else str(cid))
                if pending:
                    sample = "、".join(pending[:8])
                    more = f" 等{len(pending)}条" if len(pending) > 8 else ""
                    raise HTTPException(
                        status_code=400,
                        detail=f"冒烟套件仍有未执行用例（{sample}{more}），不能进入下一环节",
                    )
        return
    if stage == 3:
        _ensure_suite_executed(db, inst, "第一轮功能")
        return
    if stage == 4:
        _ensure_suite_executed(db, inst, "回归")
        return
    if stage == 5:
        n = db.query(TestReport).filter(
            TestReport.project_id == inst.project_id,
            TestReport.version_id == inst.version_id,
        ).count()
        if not n:
            raise HTTPException(status_code=400, detail="尚未生成测试报告，产品验收不能通过")
        return
    if stage == 6:
        ok = db.query(LaunchRequest).filter(
            LaunchRequest.project_id == inst.project_id,
            LaunchRequest.version_id == inst.version_id,
            LaunchRequest.status == "已通过",
        ).first()
        if not ok:
            raise HTTPException(status_code=400, detail="尚未有已通过的上线申请，不能完成上线验证")


def _sync_launched_version(db, inst):
    """流程完成时把对应版本标为已上线。"""
    ver = inst.version or db.query(Version).filter(Version.id == inst.version_id).first()
    if ver:
        ver.status = "已上线"


def _finish_current(db, inst, new_status, operator, remark, attachments=None):
    rec = _current_stage_record(db, inst)
    if not rec:
        raise HTTPException(status_code=400, detail="当前环节记录不存在")
    rec.status = new_status
    rec.finished_at = datetime.now()
    if operator:
        rec.operator = operator
    if remark:
        rec.remark = remark
    if attachments is not None:
        import json
        rec.attachments = json.dumps(parse_json_list(attachments), ensure_ascii=False)
    return rec


@router.post("/{fid}/pass")
def pass_stage(fid: int, payload: dict = None, db: Session = Depends(get_db),
               cur=Depends(get_current_user)):
    inst = db.query(FlowInstance).filter(FlowInstance.id == fid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程不存在")
    if inst.status != "进行中":
        raise HTTPException(status_code=400, detail="流程已结束")
    payload = payload or {}
    operator = payload.get("operator") or (cur.real_name or cur.username)
    remark = payload.get("remark", "")

    _ensure_stage_gate(db, inst)

    _finish_current(db, inst, "通过", operator, remark, payload.get("attachments"))
    if inst.current_stage == 0:
        h = _latest_handover(db, inst.version_id)
        if h and h.status in ("待测试", "已驳回"):
            h.status = "测试中"

    if inst.current_stage >= 6:
        inst.status = "已完成"
        inst.finished_at = datetime.now()
        _sync_launched_version(db, inst)
    else:
        inst.current_stage += 1
        db.add(FlowStage(instance_id=inst.id, stage_no=inst.current_stage,
                         stage_name=stage_label(inst.current_stage, inst.current_round),
                         round_no=inst.current_round, status="进行中",
                         started_at=datetime.now()))
    db.commit()
    db.refresh(inst)
    return _instance_dict(inst)


@router.post("/{fid}/reject")
def reject_stage(fid: int, payload: dict = None, db: Session = Depends(get_db),
                 cur=Depends(get_current_user)):
    inst = db.query(FlowInstance).filter(FlowInstance.id == fid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程不存在")
    if inst.status != "进行中":
        raise HTTPException(status_code=400, detail="流程已结束")
    if inst.current_stage not in (0, 5):
        raise HTTPException(status_code=400, detail="当前环节不可驳回")
    payload = payload or {}
    operator = payload.get("operator") or (cur.real_name or cur.username)
    remark = (payload.get("remark") or "").strip()
    if inst.current_stage == 0 and not remark:
        raise HTTPException(status_code=400, detail="驳回提测必须填写备注")

    _finish_current(db, inst, "驳回", operator, remark, payload.get("attachments"))
    if inst.current_stage == 0:
        inst.status = "已挂起"
        h = _latest_handover(db, inst.version_id)
        if h:
            h.status = "已驳回"
            line = f"[提测驳回] {remark}"
            h.remark = (h.remark + "\n" + line) if h.remark else line
    else:
        inst.current_round += 1
        inst.current_stage = 3
        db.add(FlowStage(instance_id=inst.id, stage_no=3,
                         stage_name=stage_label(3, inst.current_round),
                         round_no=inst.current_round, status="进行中",
                         started_at=datetime.now()))
    db.commit()
    db.refresh(inst)
    return _instance_dict(inst)


@router.post("/{fid}/skip")
def skip_stage(fid: int, payload: dict = None, db: Session = Depends(get_db),
               cur=Depends(get_current_user)):
    inst = db.query(FlowInstance).filter(FlowInstance.id == fid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程不存在")
    if inst.status != "进行中":
        raise HTTPException(status_code=400, detail="流程已结束")
    if inst.current_stage not in (1, 2):
        raise HTTPException(status_code=400, detail="当前环节不可跳过（上一环节必须完成）")
    payload = payload or {}
    operator = payload.get("operator") or (cur.real_name or cur.username)
    remark = payload.get("remark", "跳过")

    _finish_current(db, inst, "跳过", operator, remark, payload.get("attachments"))
    inst.current_stage += 1
    db.add(FlowStage(instance_id=inst.id, stage_no=inst.current_stage,
                     stage_name=stage_label(inst.current_stage, inst.current_round),
                     round_no=inst.current_round, status="进行中",
                     started_at=datetime.now()))
    db.commit()
    db.refresh(inst)
    return _instance_dict(inst)


@router.get("/{fid}")
def get_flow(fid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    inst = db.query(FlowInstance).filter(FlowInstance.id == fid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程不存在")
    return _instance_dict(inst)


@router.delete("/{fid}")
def delete_flow(fid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    inst = db.query(FlowInstance).filter(FlowInstance.id == fid).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程不存在")
    db.delete(inst)
    db.commit()
    return {"ok": True}
