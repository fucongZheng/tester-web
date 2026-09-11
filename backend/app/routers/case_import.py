"""测试用例 Excel 导入：解析预览 / AI辅助映射 / 模板下载（保存复用 /api/cases/batch）"""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from urllib.parse import quote

from ..ai_client import AIError, chat
from ..deps import get_current_user
from ..excel_parser import (FIELD_PRIORITY, ParseError, auto_map, build_template,
                            detect_header_row, parse_sheet, read_workbook, score_sheet)
from .cases import _extract_json

router = APIRouter(prefix="/api/cases/import", tags=["用例导入"])

MAX_FILE = 20 * 1024 * 1024

AI_MAP_SYSTEM = (
    "你是表格字段映射助手，只输出 JSON，不要 markdown，不要解释。"
    "给定表格表头和样例行，判断每一列对应的测试用例字段。"
    "可用字段名：title(用例标题) precondition(前置条件) steps(测试步骤) expected(预期结果) "
    "module(所属模块) priority(优先级) case_type(用例类型) remark(备注) origin_no(原编号/ID)。"
    '输出格式：{"mapping":{"title":0,"steps":2}}，键为字段名、值为列下标（从0开始），'
    "没有对应列的字段不要输出；title 必须尽量识别。"
)


@router.post("/parse")
async def parse_excel(file: UploadFile = File(...), sheet: str = Form(""),
                      header_row: int = Form(0), mapping: str = Form(""),
                      _=Depends(get_current_user)):
    """解析上传文件（不入库、不落盘）。sheet/header_row/mapping 可选，用于用户修正。"""
    name = file.filename or ""
    raw = await file.read()
    if len(raw) > MAX_FILE:
        raise HTTPException(status_code=400, detail="文件超过 20MB 上限")
    ext = name[name.rfind("."):].lower() if "." in name else ""
    if ext == ".xls":
        raise HTTPException(status_code=400, detail="暂不支持 .xls，请在 Excel 中另存为 .xlsx 或 .csv 后导入")
    if ext not in (".xlsx", ".csv"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .csv 文件")
    if ext == ".xlsx" and not raw.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="文件内容与扩展名不符，请确认为有效的 .xlsx 文件")

    try:
        sheets = read_workbook(raw, ext)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not sheets:
        raise HTTPException(status_code=400, detail="文件中没有数据")

    infos = []
    for sname, rows in sheets.items():
        try:
            hr = detect_header_row(rows)
        except ParseError:
            hr = 0
        infos.append({"name": sname, "row_count": max(0, len(rows) - hr), "score": score_sheet(rows)})

    chosen = ""
    if sheet:
        if sheet not in sheets:
            raise HTTPException(status_code=400, detail=f"Sheet「{sheet}」不存在")
        chosen = sheet
    else:
        candidates = [i for i in infos if i["score"] >= 5]
        if not candidates:
            raise HTTPException(status_code=400, detail="未找到含用例表头的Sheet（需要「标题/用例标题」等表头），请检查文件")
        chosen = max(candidates, key=lambda i: i["score"])["name"]

    rows = sheets[chosen]
    try:
        hr = header_row if header_row > 0 else detect_header_row(rows)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not (0 < hr <= len(rows)):
        raise HTTPException(status_code=400, detail=f"表头行号 {hr} 超出范围")
    headers = rows[hr - 1]

    m = None
    if mapping:
        try:
            parsed_mapping = json.loads(mapping)
        except Exception:
            raise HTTPException(status_code=400, detail="映射 JSON 无效")
        if not isinstance(parsed_mapping, dict):
            raise HTTPException(status_code=400, detail="映射 JSON 无效")
        m = {f: None for f in FIELD_PRIORITY}
        for f, v in parsed_mapping.items():
            if f not in m:
                continue
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v < len(headers)):
                raise HTTPException(status_code=400, detail=f"字段「{f}」的列索引无效")
            m[f] = v
        used = {}
        for f in FIELD_PRIORITY:
            if m[f] is None:
                continue
            if m[f] in used:
                raise HTTPException(status_code=400, detail=f"字段「{f}」与「{used[m[f]]}」选择了同一列")
            used[m[f]] = f
    else:
        m = auto_map(headers)
    if m.get("title") is None:
        raise HTTPException(status_code=400, detail="请先在映射中选择「标题」列")

    parsed, stats = parse_sheet(rows, hr, m)
    return {
        "file": {"name": name, "size": len(raw)},
        "sheets": [{**i, "selected": i["name"] == chosen} for i in infos],
        "sheet": chosen,
        "header_row": hr,
        "headers": headers,
        "mapping": m,
        "rows": parsed,
        "raw_rows": rows[hr:hr + stats["total_rows"]],
        "stats": stats,
    }


@router.post("/ai-map")
def ai_map(payload: dict, _=Depends(get_current_user)):
    """AI 根据表头+样例行推荐列映射；归一化仍由 /parse 在服务端执行。"""
    headers = payload.get("headers") or []
    samples = payload.get("sample_rows") or []
    if not isinstance(headers, list) or not headers:
        raise HTTPException(status_code=400, detail="表头不能为空")
    headers = [str(h) for h in headers]
    if not isinstance(samples, list):
        samples = []

    lines = ["表头（列下标:名称）："]
    lines += [f"{i}: {h}" for i, h in enumerate(headers)]
    for si, r in enumerate(samples[:3], 1):
        if not isinstance(r, list):
            continue
        cells = [f"{i}={str(c)[:50]}" for i, c in enumerate(r)]
        lines.append(f"样例行{si}：" + " | ".join(cells))
    user_prompt = "\n".join(lines) + "\n\n请输出列映射 JSON。"

    try:
        resp = chat(user_prompt, system=AI_MAP_SYSTEM, temperature=0, timeout=60)
    except AIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    data = _extract_json(resp)
    raw_mapping = data.get("mapping") if isinstance(data, dict) else None
    if not isinstance(raw_mapping, dict):
        raise HTTPException(status_code=502, detail="AI 返回的映射无法解析，请手动选择列")

    n = len(headers)
    clean, used = {}, set()
    for f in FIELD_PRIORITY:
        v = raw_mapping.get(f)
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v < n) or v in used:
            continue
        used.add(v)
        clean[f] = v
    if "title" not in clean:
        raise HTTPException(status_code=502, detail="AI 未能识别标题列，请手动选择")
    return {"mapping": clean}


@router.get("/template")
def download_template(_=Depends(get_current_user)):
    filename = quote("测试用例导入模板.xlsx")
    return Response(
        content=build_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
