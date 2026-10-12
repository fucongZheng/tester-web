"""FastAPI 应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask

from .config import WEAK_SECRET_KEYS, settings
from .database import SessionLocal
from .models import OperationLog
from .routers import (auth, users, roles, menus, projects, versions, modules,
                      requirements, cases, case_import, executions, bugs, flow, reports, dashboard,
                      handovers, shares, reviews, apiconfigs, logs, uploads, suites,
                      launches, aiqa, sync)
from .seed import seed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动即同步库表结构与种子数据（建表/补列/迁移，幂等）。
    # 容器镜像里 uvicorn 直起 app.main，不经过 run.py——
    # 不在启动钩子里跑 seed 的话，部署库会缺新列（/api/reports 报 Unknown column）。
    seed()
    yield


_is_prod = (settings.ENV or "").lower() == "production"
if _is_prod and (not settings.SECRET_KEY or settings.SECRET_KEY in WEAK_SECRET_KEYS or len(settings.SECRET_KEY) < 32):
    raise RuntimeError("生产环境必须设置至少 32 位随机 SECRET_KEY，且不能使用默认值")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def op_log(request: Request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "PUT", "DELETE") and request.url.path.startswith("/api"):
        # 写库挪到响应发送后的后台任务（sync 函数自动进线程池），不阻塞事件循环
        response.background = BackgroundTask(
            _write_op_log, request.method, request.url.path,
            request.headers.get("authorization", ""),
        )
    return response


def _write_op_log(method: str, path: str, auth_header: str):
    """落一条操作日志。失败只记日志，不影响主流程。"""
    db = SessionLocal()
    try:
        from .security import decode_token
        username = ""
        if auth_header.startswith("Bearer "):
            payload = decode_token(auth_header[7:])
            username = payload.get("username", "") if payload else ""
        db.add(OperationLog(username=username, method=method, path=path))
        db.commit()
    except Exception:
        logging.exception("操作日志写入失败: %s %s", method, path)
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    out = {"app": settings.APP_NAME, "status": "ok"}
    if not _is_prod:
        out["docs"] = "/docs"
    return out


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 注册路由
for r in (auth, users, roles, menus, projects, versions, modules,
          requirements, cases, case_import, executions, bugs, flow, reports, dashboard,
          handovers, shares, reviews, apiconfigs, logs, uploads, suites,
          launches, aiqa, sync):
    app.include_router(r.router)

# 附件走 /api/uploads/file/{name}，带安全 Content-Type，不再用 StaticFiles 裸挂目录
