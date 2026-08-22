"""启动脚本：python run.py  (默认先执行种子数据再启动)"""
import uvicorn

from app.seed import seed

if __name__ == "__main__":
    seed()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
