"""初始化：建表 + 种子数据（菜单/角色/管理员）"""
import json

from .database import Base, engine, SessionLocal
from .models import SysMenu, SysRole, SysUser
from .security import hash_password

# (name, parent_name, type, path, component, icon, sort, permission)
# parent_name=None 表示顶级
MENUS = [
    ("看板统计", None, "menu", "/dashboard", "views/dashboard/index", "DataBoard", 1, ""),
    ("项目管理", None, "dir", "/project", "", "Folder", 2, ""),
    ("项目列表", "项目管理", "menu", "/project", "views/project/index", "List", 1, ""),
    ("版本管理", "项目管理", "menu", "/version", "views/version/index", "Stamp", 2, ""),
    ("模块管理", "项目管理", "menu", "/module", "views/module/index", "Grid", 3, ""),
    ("测试管理", None, "dir", "/test", "", "Tickets", 4, ""),
    ("需求管理", "测试管理", "menu", "/requirement", "views/requirement/index", "Document", 1, ""),
    ("测试用例", "测试管理", "menu", "/case", "views/case/index", "EditPen", 2, ""),
    ("BUG管理", "测试管理", "menu", "/bug", "views/bug/index", "Warning", 3, ""),
    ("测试流程", None, "menu", "/flow", "views/flow/index", "Connection", 5, ""),
    ("测试报告", None, "menu", "/report", "views/report/index", "Files", 6, ""),
    ("系统管理", None, "dir", "/system", "", "Setting", 7, ""),
    ("用户管理", "系统管理", "menu", "/system/user", "views/system/user", "User", 1, ""),
    ("角色管理", "系统管理", "menu", "/system/role", "views/system/role", "Avatar", 2, ""),
    ("菜单管理", "系统管理", "menu", "/system/menu", "views/system/menu", "Menu", 3, ""),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 菜单
        if db.query(SysMenu).count() == 0:
            name_to_id = {}
            for name, parent_name, mtype, path, comp, icon, sort, perm in MENUS:
                parent_id = name_to_id.get(parent_name, 0) if parent_name else 0
                m = SysMenu(name=name, parent_id=parent_id, type=mtype, path=path,
                            component=comp, icon=icon, sort=sort, permission=perm, visible=1)
                db.add(m)
                db.flush()
                name_to_id[name] = m.id

        all_menu_ids = [m.id for m in db.query(SysMenu).all()]

        def ids_of(*names):
            return [m.id for m in db.query(SysMenu).filter(SysMenu.name.in_(names)).all()]

        def add_role(name, code, desc, ids):
            if db.query(SysRole).filter(SysRole.code == code).first():
                return
            db.add(SysRole(name=name, code=code, description=desc,
                           menu_ids=json.dumps(ids), status=1))

        add_role("超级管理员", "admin", "拥有全部权限", all_menu_ids)
        add_role("测试工程师", "tester", "测试相关权限",
                 ids_of("看板统计", "项目管理", "项目列表", "版本管理", "模块管理",
                        "测试管理", "需求管理", "测试用例", "BUG管理", "测试流程", "测试报告"))
        add_role("产品经理", "product", "需求与流程权限",
                 ids_of("看板统计", "项目管理", "项目列表", "版本管理",
                        "测试管理", "需求管理", "测试流程", "测试报告"))
        add_role("开发工程师", "developer", "BUG处理权限",
                 ids_of("看板统计", "项目列表", "BUG管理"))
        db.flush()

        # 管理员
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
