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


class SyncLog(Base):
    """需求同步日志：每次从 xuqiu 拉取的结果（新增/更新/无变化/源删除/失败）"""
    __tablename__ = "sync_log"
    id = Column(Integer, primary_key=True, index=True)
    trigger = Column(String(16), default="manual")  # manual / schedule
    status = Column(String(16), default="ok")  # ok / failed
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)  # 源已删除（本地保留）
    failed_count = Column(Integer, default=0)
    cases_count = Column(Integer, default=0)  # 本次同步 AI 生成的用例数
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
    review_minutes = Column(Text, default="")  # 需求评审纪要，必填
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
    content = Column(Text, default="")  # 需求内容，长文本/富文本
    product_name = Column(String(64), default="")
    status = Column(String(32), default="待开发")  # 待开发/开发中/待测试/测试中/已验收/已上线
    priority = Column(String(8), default="P2")  # P0/P1/P2/P3
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    attachments = Column(Text, default="[]")  # JSON [{name,url,size}]
    # 需求同步：来源系统标识 + 源系统内的需求 id（xuqiu 的 req_xxx），幂等 upsert 靠它
    source_system = Column(String(32), default="")
    source_id = Column(String(64), default="")
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
    stage_no = Column(Integer, default=5)  # 对应流程环节编号，见 flow_stages.py（人工测试=5）
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
    steps = Column(Text, default="")  # 复现步骤（HTML 富文本）
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
    module_ids = Column(Text, default="[]")  # JSON，报告口径的模块，空=整版本
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
    current_stage = Column(Integer, default=0)  # 环节编号，见 flow_stages.py
    current_round = Column(Integer, default=1)
    status = Column(String(16), default="进行中")  # 进行中/已完成/已挂起
    started_at = Column(DateTime, default=now)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    stages = relationship("FlowStage", lazy="selectin", order_by="FlowStage.id",
                          cascade="all, delete-orphan")


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
    attachments = Column(Text, default="[]")  # JSON [{name,url,size}]


class Handover(Base):
    """开发提测"""
    __tablename__ = "handover"
    id = Column(Integer, primary_key=True, index=True)
    handover_no = Column(String(32), unique=True, default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    requirement_ids = Column(Text, default="[]")  # JSON 数组
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    branch = Column(Text, nullable=False, default="")
    smoke_executed = Column(String(16), default="未执行")  # 已执行/未执行
    suite_id = Column(Integer, ForeignKey("test_suite.id"), nullable=True)
    tester_id = Column(Integer, ForeignKey("sys_user.id"), nullable=True)
    tester_name = Column(String(64), default="")
    remark = Column(Text, default="")
    status = Column(String(16), default="待测试")  # 待测试/测试中/已完成
    submitter = Column(String(64), default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")
    tester = relationship("SysUser", lazy="joined")


class HandoverShare(Base):
    """开发提测公开填写链接（免登录）"""
    __tablename__ = "handover_share"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, nullable=True)
    version_id = Column(Integer, nullable=True)
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime, nullable=True)


class BugShare(Base):
    """BUG 列表分享（公开链接，免登录）"""
    __tablename__ = "bug_share"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), default="")
    bug_ids = Column(Text, default="[]")  # JSON 数组
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime, nullable=True)


class ReviewRecord(Base):
    """需求评审 / 用例评审"""
    __tablename__ = "review_record"
    id = Column(Integer, primary_key=True, index=True)
    review_no = Column(String(32), unique=True, default="")
    review_type = Column(String(16), nullable=False)  # 需求评审 / 用例评审
    title = Column(String(255), default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=True)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    target_ids = Column(Text, default="[]")  # 需求/用例 ID JSON；用例评审时=核心用例
    normal_ids = Column(Text, default="[]")  # 用例评审的常规用例 ID JSON
    reviewer = Column(String(64), default="")
    participants = Column(String(255), default="")
    result = Column(String(16), default="待评审")  # 待评审/通过/有条件通过/不通过
    comment = Column(Text, default="")
    review_date = Column(String(32), default="")
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")


class TestSuite(Base):
    """测试套件：冒烟 / 第一轮功能 / 回归 等"""
    __tablename__ = "test_suite"
    id = Column(Integer, primary_key=True, index=True)
    suite_no = Column(String(32), unique=True, default="")
    name = Column(String(128), nullable=False)
    suite_type = Column(String(32), default="自定义")  # 冒烟/第一轮功能/回归/自定义
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    case_ids = Column(Text, default="[]")
    remark = Column(Text, default="")
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")


class LaunchRequest(Base):
    """上线申请：流程「上线+生产环境验证」环节的卡点"""
    __tablename__ = "launch_request"
    id = Column(Integer, primary_key=True, index=True)
    launch_no = Column(String(32), unique=True, default="")
    title = Column(String(255), default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=True)
    plan_date = Column(String(32), default="")
    content = Column(Text, default="")  # 上线内容 / 变更说明
    applicant = Column(String(64), default="")
    reviewer = Column(String(64), default="")
    status = Column(String(16), default="待审批")  # 待审批/已通过/已驳回
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    module = relationship("Module", lazy="joined")


class ApiConfig(Base):
    """AI / 中转站等 API 配置"""
    __tablename__ = "api_config"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    provider = Column(String(32), default="openai")  # openai / azure / 中转站 / custom
    base_url = Column(String(255), default="")
    api_key = Column(String(255), default="")
    model = Column(String(128), default="")
    enabled = Column(Integer, default=0)
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class AiQaSession(Base):
    """管理员 AI 问质会话"""
    __tablename__ = "ai_qa_session"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False)
    title = Column(String(128), default="")
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    version_id = Column(Integer, ForeignKey("version.id"), nullable=True)
    risk_level = Column(String(16), default="")  # green / yellow / red
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    project = relationship("Project", lazy="joined")
    version = relationship("Version", lazy="joined")
    messages = relationship("AiQaMessage", lazy="selectin", order_by="AiQaMessage.id",
                            cascade="all, delete-orphan")


class AiQaMessage(Base):
    __tablename__ = "ai_qa_message"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ai_qa_session.id"), nullable=False)
    role = Column(String(16), nullable=False)  # user / assistant
    content = Column(Text, default="")
    snapshot = Column(Text, default="")  # 助手消息附带的质量快照 JSON
    created_at = Column(DateTime, default=now)
