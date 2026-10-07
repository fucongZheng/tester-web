"""应用配置"""
from pydantic_settings import BaseSettings


WEAK_SECRET_KEYS = {"change-me-in-production", "please-change-this-secret"}


class Settings(BaseSettings):
    APP_NAME: str = "测试管理系统"
    ENV: str = "development"  # development | production
    # MySQL 连接串
    DATABASE_URL: str = "mysql+pymysql://root:123456@127.0.0.1:3306/tester?charset=utf8mb4"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 天
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI（本期留桩，预留 OpenAI 兼容端点）
    AI_ENABLED: bool = False
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = ""

    # xuqiu 需求系统开放 API（需求同步的事实源）
    XUQIU_BASE_URL: str = "http://127.0.0.1:8000"
    XUQIU_API_KEY: str = "inkproto-open-9f2c1d7a"
    # 同步新增需求后自动调 AI 生成用例（关掉则只同步需求）
    SYNC_AUTO_CASES: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
