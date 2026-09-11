"""附件上传：类型白名单 + 路径限制 + 安全 Content-Type"""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from ..deps import get_current_user

router = APIRouter(tags=["附件"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIZE = 20 * 1024 * 1024
STORED_NAME = re.compile(r"^[a-f0-9]{32}\.[a-z0-9]{1,8}$")

SAFE_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".zip": "application/zip",
}

def _sniff_ext(raw: bytes, claimed: str) -> str:
    claimed = (claimed or "").lower()
    if claimed == ".jpeg":
        claimed = ".jpg"
    head = raw[:16]
    if claimed == ".png" and head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if claimed in (".jpg", ".jpeg") and head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if claimed == ".gif" and (head.startswith(b"GIF87a") or head.startswith(b"GIF89a")):
        return ".gif"
    if claimed == ".webp" and head.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return ".webp"
    if claimed == ".pdf" and head.startswith(b"%PDF"):
        return ".pdf"
    if claimed in (".zip", ".docx", ".xlsx", ".pptx") and head.startswith(b"PK"):
        return claimed
    if claimed in (".doc", ".xls", ".ppt") and head.startswith(b"\xd0\xcf\x11\xe0"):
        return claimed
    if claimed in (".txt", ".csv") and b"\x00" not in raw[:4096]:
        return claimed
    return ""


def _reject_markup(raw: bytes):
    sample = raw[:4096].lstrip().lower()
    if sample.startswith(b"<") or b"<script" in sample or b"<svg" in sample or b"<!doctype" in sample:
        raise HTTPException(status_code=400, detail="不允许上传 HTML / 脚本文件")


def _safe_path(name: str) -> Path:
    name = (name or "").strip()
    if not STORED_NAME.match(name):
        raise HTTPException(status_code=404, detail="文件不存在")
    root = UPLOAD_DIR.resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return path


def _file_response(path: Path):
    ext = path.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    mime = SAFE_EXT.get(ext) or "application/octet-stream"
    inline = mime.startswith("image/") or mime == "application/pdf"
    disp = "inline" if inline else "attachment"
    return FileResponse(
        path,
        media_type=mime,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": f'{disp}; filename="{path.name}"',
        },
    )


@router.post("/api/uploads")
async def upload_file(file: UploadFile = File(...), _=Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    raw = await file.read()
    if len(raw) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件不能超过 20MB")
    claimed = Path(file.filename).suffix.lower()
    if claimed == ".jpeg":
        claimed = ".jpg"
    if claimed not in SAFE_EXT:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    _reject_markup(raw)
    ext = _sniff_ext(raw, claimed)
    if ext != claimed:
        raise HTTPException(status_code=400, detail="文件内容与扩展名不符")
    stored_ext = ext
    mime = SAFE_EXT.get(stored_ext, "application/octet-stream")
    stored = f"{uuid.uuid4().hex}{stored_ext}"
    dest = UPLOAD_DIR / stored
    dest.write_bytes(raw)
    return {
        "name": Path(file.filename).name,
        "url": f"/uploads/{stored}",
        "size": len(raw),
        "content_type": mime,
    }


@router.get("/api/uploads/file/{name}")
def get_file(name: str):
    return _file_response(_safe_path(name))


@router.get("/uploads/{name}")
def public_file(name: str):
    return _file_response(_safe_path(name))
