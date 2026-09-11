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


def empty_to_none(v):
    """前端清空下拉会传 ''，整数外键列不能写空串。"""
    if v == "" or v is None:
        return None
    return v


def apply_module_filter(q, model, module_id):
    """module_id=-1 表示未分类（空模块）。"""
    if not module_id:
        return q
    if int(module_id) == -1:
        return q.filter(model.module_id.is_(None))
    return q.filter(model.module_id == module_id)


def parse_id_list(raw):
    if isinstance(raw, list):
        out = []
        for x in raw:
            if x == "" or x is None:
                continue
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    if not raw:
        return []
    try:
        import json
        return parse_id_list(json.loads(raw))
    except Exception:
        return []


def parse_json_list(raw):
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        import json
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def dump_json_list(raw):
    import json
    return json.dumps(parse_json_list(raw), ensure_ascii=False)


def refuse_if_related(db, checks):
    """checks: [(Model, filter_kwargs, 中文名), ...] 有关联则 400。"""
    from fastapi import HTTPException
    hits = []
    for model, filters, label in checks:
        n = db.query(model).filter_by(**filters).count()
        if n:
            hits.append(f"{label} {n} 条")
    if hits:
        raise HTTPException(status_code=400, detail="存在关联数据，无法删除：" + "、".join(hits))


def strip_id_from_json_column(db, model, column_name, rid):
    """从 JSON 数组字段里摘掉某个 ID（套件用例、提测需求、分享 BUG 等）。"""
    import json
    try:
        rid = int(rid)
    except (TypeError, ValueError):
        return
    for row in db.query(model).all():
        ids = parse_id_list(getattr(row, column_name))
        if rid in ids:
            setattr(row, column_name, json.dumps([x for x in ids if x != rid]))


def parse_datetime(value):
    """兼容日期或精确到秒的时间。"""
    if not value:
        return None
    raw = str(value).strip().replace("T", " ")
    for fmt, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(raw[:n], fmt)
        except Exception:
            continue
    return None


def overtime_text(launch_date, status=None):
    """当前时间超过上线时间时返回超时时长；已上线/已归档停止计算。"""
    if not launch_date or status in ("已上线", "已归档"):
        return ""
    start = parse_datetime(launch_date)
    if not start:
        return ""
    delta = datetime.now() - start
    if delta.total_seconds() <= 0:
        return ""
    days, seconds = delta.days, delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if not parts:
        parts.append("不足1分钟")
    return "".join(parts)
