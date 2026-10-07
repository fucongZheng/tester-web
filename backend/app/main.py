"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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
        try:
            db = SessionLocal()
            from .security import decode_token
            username = ""
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                payload = decode_token(auth[7:])
                username = payload.get("username", "") if payload else ""
            db.add(OperationLog(username=username, method=request.method,
                                path=request.url.path))
            db.commit()
            db.close()
        except Exception:
            pass
    return response


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
