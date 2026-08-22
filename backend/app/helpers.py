"""公共工具：序列化、分页、菜单树"""
from datetime import datetime


def row_to_dict(obj):
    """只取表字段，datetime 转字符串，便于 JSON 序列化。"""
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, datetime):
            v = v.strftime("%Y-%m-%d %H:%M:%S")
        d[c.name] = v
    return d


def paginate(query, page: int = 1, size: int = 10):
    page = max(1, page)
    size = min(max(1, size), 500)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return items, total


def build_menu_tree(menus):
    """把扁平菜单列表转成树（按 sort 排序）。"""
    menus = sorted(menus, key=lambda m: (m.sort or 0, m.id))
    by_id = {m.id: {
        "id": m.id, "parent_id": m.parent_id, "name": m.name, "type": m.type,
        "path": m.path, "component": m.component, "icon": m.icon, "sort": m.sort,
        "permission": m.permission, "visible": m.visible, "children": []
    } for m in menus}
    tree = []
    for m in menus:
        node = by_id[m.id]
        parent = by_id.get(m.parent_id)
        if parent and m.parent_id != 0:
            parent["children"].append(node)
        else:
            tree.append(node)
    return tree


def gen_code(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:04d}"
