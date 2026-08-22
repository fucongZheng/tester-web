"""FastAPI 应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, SessionLocal
from .models import Base, OperationLog
from .routers import (auth, users, roles, menus, projects, versions, modules,
                      requirements, cases, executions, bugs, flow, reports, dashboard)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

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
    return {"app": settings.APP_NAME, "docs": "/docs", "status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 注册路由
for r in (auth, users, roles, menus, projects, versions, modules,
          requirements, cases, executions, bugs, flow, reports, dashboard):
    app.include_router(r.router)
