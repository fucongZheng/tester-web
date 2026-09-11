"""初始化：建表 + 种子数据（菜单/角色/管理员）"""
import json

from .database import Base, engine, SessionLocal
from .models import SysMenu, SysRole, SysUser, FlowInstance, Version
from .security import hash_password

# (name, parent_name, type, path, component, icon, sort, permission)
# parent_name=None 表示顶级。按测试主流程排布。
MENUS = [
    ("看板统计", None, "menu", "/dashboard", "views/dashboard/index", "DataBoard", 1, ""),
    ("项目", None, "menu", "/project", "views/project/index", "Folder", 2, ""),
    ("需求", None, "menu", "/requirement", "views/requirement/index", "Document", 3, ""),
    ("版本", None, "menu", "/version", "views/version/index", "Stamp", 4, ""),
    ("模块", None, "menu", "/module", "views/module/index", "Grid", 5, ""),
    ("测试用例", None, "menu", "/case", "views/case/index", "EditPen", 6, ""),
    ("提测", None, "menu", "/handover", "views/handover/index", "Promotion", 7, ""),
    ("冒烟", None, "menu", "/suite", "views/suite/index", "Collection", 8, ""),
    ("BUG管理", None, "menu", "/bug", "views/bug/index", "Warning", 9, ""),
    ("测试流程", None, "menu", "/flow", "views/flow/index", "Connection", 10, ""),
    ("测试报告", None, "menu", "/report", "views/report/index", "Files", 11, ""),
    ("上线申请", None, "menu", "/launch", "views/launch/index", "Upload", 12, ""),
    ("评审记录", None, "menu", "/review", "views/review/index", "ChatLineSquare", 13, ""),
    ("系统管理", None, "dir", "/system", "", "Setting", 20, ""),
    ("用户管理", "系统管理", "menu", "/system/user", "views/system/user", "User", 1, ""),
    ("角色管理", "系统管理", "menu", "/system/role", "views/system/role", "Avatar", 2, ""),
    ("菜单管理", "系统管理", "menu", "/system/menu", "views/system/menu", "Menu", 3, ""),
    ("API管理", "系统管理", "menu", "/system/api", "views/system/api", "Connection", 4, ""),
    ("操作日志", "系统管理", "menu", "/system/log", "views/system/log", "Document", 5, ""),
    ("AI问质", "系统管理", "menu", "/system/aiqa", "views/system/aiqa", "ChatDotRound", 6, ""),
]

# 旧菜单名 → 新菜单名（已有库按名称迁移，避免重复）
MENU_RENAMES = {
    "项目列表": "项目",
    "需求管理": "需求",
    "版本管理": "版本",
    "模块管理": "模块",
    "开发提测": "提测",
    "测试套件": "冒烟",
}

HIDDEN_DIRS = ("项目管理", "测试管理")


def _ensure_columns(db):
    """已有库 create_all 不会加列，这里做增量补齐。"""
    from sqlalchemy import text
    alters = [
        "ALTER TABLE bug ADD COLUMN steps TEXT",
        "ALTER TABLE flow_stage ADD COLUMN attachments TEXT",
        "ALTER TABLE handover ADD COLUMN suite_id INT NULL",
        "ALTER TABLE requirement ADD COLUMN attachments TEXT",
        "ALTER TABLE requirement ADD COLUMN content TEXT",
        "ALTER TABLE handover MODIFY COLUMN branch TEXT",
        "ALTER TABLE version ADD COLUMN review_minutes TEXT",
        "ALTER TABLE handover ADD COLUMN module_id INT NULL",
        "ALTER TABLE test_suite ADD COLUMN module_id INT NULL",
        "ALTER TABLE review_record ADD COLUMN module_id INT NULL",
        "ALTER TABLE bug_share ADD COLUMN expires_at DATETIME NULL",
        "ALTER TABLE handover_share ADD COLUMN expires_at DATETIME NULL",
    ]
    for sql in alters:
        try:
            db.execute(text(sql))
            db.commit()
        except Exception:
            db.rollback()


def _sync_completed_flow_versions(db):
    """历史已完成流程补齐版本状态（加同步逻辑前走完的不会自动改）。"""
    done = db.query(FlowInstance).filter(FlowInstance.status == "已完成").all()
    changed = 0
    for inst in done:
        ver = db.query(Version).filter(Version.id == inst.version_id).first()
        if ver and ver.status != "已上线":
            ver.status = "已上线"
            changed += 1
    if changed:
        db.commit()
        print(f"[OK] synced {changed} version(s) to 已上线 from completed flows")


def _sync_menus(db):
    """按名称增量补齐，并按主流程重排/改名/打平目录。"""
    for old, new in MENU_RENAMES.items():
        row = db.query(SysMenu).filter(SysMenu.name == old).first()
        if row and not db.query(SysMenu).filter(SysMenu.name == new).first():
            row.name = new
        elif row:
            row.visible = 0
    db.flush()

    name_to_id = {m.name: m.id for m in db.query(SysMenu).all()}
    for name, parent_name, mtype, path, comp, icon, sort, perm in MENUS:
        parent_id = name_to_id.get(parent_name, 0) if parent_name else 0
        existing = db.query(SysMenu).filter(SysMenu.name == name).first()
        if existing:
            existing.parent_id = parent_id
            existing.type = mtype
            existing.path = path
            existing.component = comp
            existing.icon = icon
            existing.sort = sort
            existing.permission = perm
            existing.visible = 1
            continue
        m = SysMenu(name=name, parent_id=parent_id, type=mtype, path=path,
                    component=comp, icon=icon, sort=sort, permission=perm, visible=1)
        db.add(m)
        db.flush()
        name_to_id[name] = m.id

    wanted = {name for name, *_ in MENUS}
    for name in HIDDEN_DIRS:
        row = db.query(SysMenu).filter(SysMenu.name == name).first()
        if row:
            row.visible = 0
            row.type = "dir"
            # 子菜单已打平到顶级，目录本身不再展示
            wanted.add(name)

    db.flush()
    return [m.id for m in db.query(SysMenu).filter(SysMenu.visible == 1).all()]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    _ensure_columns(db)
    _sync_completed_flow_versions(db)
    try:
        all_menu_ids = _sync_menus(db)

        def ids_of(*names):
            return [m.id for m in db.query(SysMenu).filter(SysMenu.name.in_(names)).all()]

        def upsert_role(name, code, desc, ids):
            role = db.query(SysRole).filter(SysRole.code == code).first()
            if role:
                role.menu_ids = json.dumps(sorted(set(ids)))
                return
            db.add(SysRole(name=name, code=code, description=desc,
                           menu_ids=json.dumps(ids), status=1))

        upsert_role("超级管理员", "admin", "拥有全部权限", all_menu_ids)
        upsert_role("测试工程师", "tester", "测试相关权限",
                    ids_of("项目", "需求", "版本", "模块", "测试用例", "提测", "冒烟",
                           "BUG管理", "测试流程", "测试报告", "上线申请", "评审记录",
                           "项目列表", "需求管理", "版本管理", "模块管理", "开发提测", "测试套件"))
        upsert_role("产品经理", "product", "需求与流程权限",
                    ids_of("项目", "需求", "版本", "提测", "测试流程", "测试报告",
                           "上线申请", "评审记录",
                           "项目列表", "需求管理", "版本管理", "开发提测"))
        upsert_role("开发工程师", "developer", "BUG处理权限",
                    ids_of("项目", "提测", "BUG管理", "上线申请",
                           "项目列表", "开发提测"))
        db.flush()

        if db.query(SysUser).filter(SysUser.username == "admin").first() is None:
            role = db.query(SysRole).filter(SysRole.code == "admin").first()
            db.add(SysUser(username="admin", password=hash_password("admin123"),
                           real_name="管理员", email="admin@test.com", role_id=role.id, status=1))

        db.commit()
        print("[OK] init done: menus/roles/admin ready (admin / admin123)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
