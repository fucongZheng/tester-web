"""测试流程状态机"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FlowInstance, FlowStage, Version
from ..deps import get_current_user
from ..helpers import row_to_dict

router = APIRouter(prefix="/api/flow", tags=["测试流程"])

STAGE_NAMES = {
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
    d["stages"] = [row_to_dict(s) for s in inst.stages]
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


@router.post("/start")
def start_flow(payload: dict, db: Session = Depends(get_db), cur=Depends(get_current_user)):
    project_id = payload.get("project_id")
    version_id = payload.get("version_id")
    if not project_id or not version_id:
        raise HTTPException(status_code=400, detail="项目和版本必填")
    existing = db.query(FlowInstance).filter(
        FlowInstance.version_id == version_id, FlowInstance.status == "进行中").first()
    if existing:
        return _instance_dict(existing)
    inst = FlowInstance(project_id=project_id, version_id=version_id,
                        current_stage=1, current_round=1, status="进行中")
    db.add(inst)
    db.flush()
    db.add(FlowStage(instance_id=inst.id, stage_no=1,
                     stage_name=stage_label(1, 1), round_no=1,
                     status="进行中", started_at=datetime.now(),
                     operator=cur.real_name or cur.username))
    db.commit()
    db.refresh(inst)
    return _instance_dict(inst)


def _current_stage_record(db, inst):
    return db.query(FlowStage).filter(
        FlowStage.instance_id == inst.id,
        FlowStage.stage_no == inst.current_stage,
        FlowStage.round_no == inst.current_round,
        FlowStage.status == "进行中",
    ).order_by(FlowStage.id.desc()).first()


def _finish_current(db, inst, new_status, operator, remark):
    rec = _current_stage_record(db, inst)
    if not rec:
        raise HTTPException(status_code=400, detail="当前环节记录不存在")
    rec.status = new_status
    rec.finished_at = datetime.now()
    if operator:
        rec.operator = operator
    if remark:
        rec.remark = remark
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

    _finish_current(db, inst, "通过", operator, remark)

    if inst.current_stage >= 6:
        inst.status = "已完成"
        inst.finished_at = datetime.now()
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
    if inst.current_stage != 5:
        raise HTTPException(status_code=400, detail="只有产品验收环节可驳回")
    payload = payload or {}
    operator = payload.get("operator") or (cur.real_name or cur.username)
    remark = payload.get("remark", "")

    _finish_current(db, inst, "驳回", operator, remark)
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
    if inst.current_stage not in (1, 2, 4):
        raise HTTPException(status_code=400, detail="当前环节不可跳过")
    payload = payload or {}
    operator = payload.get("operator") or (cur.real_name or cur.username)
    remark = payload.get("remark", "跳过")

    _finish_current(db, inst, "跳过", operator, remark)
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
