"""数据模型（SQLAlchemy ORM）"""
from datetime import datetime

from sqlalchemy import (Column, Integer, String, Text, DateTime, ForeignKey,
                        Boolean, func)
from sqlalchemy.orm import relationship

from .database import Base


def now():
    return datetime.now()


class SysUser(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    real_name = Column(String(64), default="")
    email = Column(String(128), default="")
    phone = Column(String(32), default="")
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=True)
    status = Column(Integer, default=1)  # 1 启用 0 禁用
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    role = relationship("SysRole", lazy="joined")


class SysRole(Base):
    __tablename__ = "sys_role"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    code = Column(String(64), unique=True, nullable=False)
    description = Column(String(255), default="")
    menu_ids = Column(Text, default="[]")  # JSON 数组
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class SysMenu(Base):
    __tablename__ = "sys_menu"
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, default=0)
    name = Column(String(64), nullable=False)
    type = Column(String(16), default="menu")  # dir / menu / button
    path = Column(String(128), default="")
    component = Column(String(128), default="")
    icon = Column(String(64), default="")
    sort = Column(Integer, default=0)
    permission = Column(String(128), default="")  # 按钮权限标识
    visible = Column(Integer, default=1)


class OperationLog(Base):
    __tablename__ = "operation_log"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), default="")
    action = Column(String(128), default="")
    method = Column(String(16), default="")
    path = Column(String(255), default="")
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=now)


class Project(Base):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), default="其他")  # 产业中台/教育/数建/住建/其他
    owner = Column(String(64), default="")
    members = Column(Text, default="")  # 逗号分隔
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Version(Base):
    __tablename__ = "version"
    id = Column(Integer, primary_key=True, index=True)
    version_no = Column(String(64), nullable=False)
    name = Column(String(128), default="")
    start_date = Column(String(32), default="")
    launch_date = Column(String(32), default="")
    status = Column(String(32), default="规划中")
    remark = Column(Text, default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")


class Module(Base):
    __tablename__ = "module"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    parent_id = Column(Integer, default=0)
    sort = Column(Integer, default=0)
    remark = Column(String(255), default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    created_at = Column(DateTime, default=now)

    project = relationship("Project", lazy="joined")


class Requirement(Base):
    __tablename__ = "requirement"
    id = Column(Integer, primary_key=True, index=True)
    req_no = Column(String(32), unique=True, default="")
    name = Column(String(255), nullable=False)
    product_name = Column(String(64), default="")
    status = Column(String(32), default="待开发")  # 待开发/开发中/待测试/测试中/已验收/已上线
    priority = Column(String(8), default="P2")  # P0/P1/P2/P3
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")


class TestCase(Base):
    __tablename__ = "test_case"
    id = Column(Integer, primary_key=True, index=True)
    case_no = Column(String(32), unique=True, default="")
    title = Column(String(255), nullable=False)
    precondition = Column(Text, default="")
    steps = Column(Text, default="")
    expected = Column(Text, default="")
    case_type = Column(String(32), default="功能")  # 功能/接口/UI/性能/回归
    priority = Column(String(8), default="P2")
    status = Column(Integer, default=1)  # 1 启用 0 停用
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    requirement_id = Column(Integer, ForeignKey("requirement.id"), nullable=True)
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")
    requirement = relationship("Requirement", lazy="joined")


class Execution(Base):
    __tablename__ = "execution"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_case.id"), nullable=False)
    round_no = Column(Integer, default=1)
    stage_no = Column(Integer, default=3)  # 对应流程环节，人工测试=3
    result = Column(String(16), default="未执行")  # 通过/失败/阻塞/跳过/未执行
    actual = Column(Text, default="")
    executor = Column(String(64), default="")
    executed_at = Column(DateTime, default=now)
    remark = Column(String(255), default="")

    case = relationship("TestCase", lazy="joined")


class Bug(Base):
    __tablename__ = "bug"
    id = Column(Integer, primary_key=True, index=True)
    bug_no = Column(String(32), unique=True, default="")
    title = Column(String(255), nullable=False)
    severity = Column(String(16), default="一般")  # 致命/严重/一般/轻微/建议
    status = Column(String(32), default="待处理")  # 待处理/处理中/已修复未发版/已修复已发版/不是BUG/测试验证通过关闭
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    requirement_id = Column(Integer, ForeignKey("requirement.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("test_case.id"), nullable=True)
    found_stage = Column(String(32), default="第一轮测试")  # 第一轮测试/第二轮测试/回归测试/线上溢出/产品提出
    submitter = Column(String(64), default="")
    assignee = Column(String(64), default="")
    fixer = Column(String(64), default="")
    closed_at = Column(DateTime, nullable=True)
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")
    requirement = relationship("Requirement", lazy="joined")
    case = relationship("TestCase", lazy="joined")


class TestReport(Base):
    __tablename__ = "test_report"
    id = Column(Integer, primary_key=True, index=True)
    report_no = Column(String(32), unique=True, default="")
    title = Column(String(255), default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    content = Column(Text, default="")  # Markdown
    summary = Column(Text, default="{}")  # JSON 聚合摘要
    generator = Column(String(64), default="")
    method = Column(String(16), default="AI")  # AI/手动
    created_at = Column(DateTime, default=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")


class FlowInstance(Base):
    __tablename__ = "flow_instance"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    current_stage = Column(Integer, default=1)
    current_round = Column(Integer, default=1)
    status = Column(String(16), default="进行中")  # 进行中/已完成/已挂起
    started_at = Column(DateTime, default=now)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    stages = relationship("FlowStage", lazy="selectin", order_by="FlowStage.id")


class FlowStage(Base):
    __tablename__ = "flow_stage"
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("flow_instance.id"), nullable=False)
    stage_no = Column(Integer, nullable=False)
    stage_name = Column(String(64), nullable=False)
    round_no = Column(Integer, default=1)
    status = Column(String(16), default="待开始")  # 待开始/进行中/通过/驳回/跳过
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    operator = Column(String(64), default="")
    remark = Column(String(255), default="")
