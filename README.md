# 测试管理系统

基于 FastAPI + Vue 3 的测试管理系统，覆盖 **项目 → 版本 → 模块 → 需求 → 用例 → 执行 → BUG → 测试流程 → 测试报告 → 看板统计 → 系统管理** 全链路。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + PyJWT |
| 数据库 | MySQL 8.0（库名 `tester`） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + ECharts |

需求闭环与设计说明见 [design.md](design.md)。

## 目录结构

```
web/
├─ backend/            # FastAPI 后端
│  ├─ run.py           # 一键启动（自动建表+种子数据）
│  ├─ app/
│  │  ├─ main.py       # 应用入口
│  │  ├─ models.py     # 数据模型
│  │  ├─ seed.py       # 初始化菜单/角色/管理员
│  │  ├─ templates/report.md.j2  # 测试报告模板
│  │  └─ routers/      # 各业务路由
│  └─ requirements.txt
└─ frontend/           # Vue3 前端
   └─ src/views/       # 各业务页面
```

## 启动步骤

### 1. 准备数据库

```bash
mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS tester DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

> 连接串在 `backend/app/config.py` 或 `backend/.env`（复制 `.env.example` 改）。默认 `root/123456`。

### 2. 启动后端（默认 8000 端口）

```bash
cd backend
python run.py
# 或：python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

首次启动会自动建表并写入种子数据（菜单、角色、管理员）。接口文档：http://127.0.0.1:8000/docs

### 3. 启动前端（默认 5173 端口）

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 默认账号

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 超级管理员 |

## 核心功能

- **项目管理**：类型（产业中台/教育/数建/住建/其他）、负责人、成员
- **版本 / 模块 / 需求**：版本状态、模块树、需求优先级与状态
- **测试用例**：用例定义（前置/步骤/预期）+ 执行记录（结果/实际/轮次）分层
- **BUG**：严重等级、状态、模块、发现阶段、提交人/经办人/修复人
- **测试流程**（6 环节状态机）：AI接口测试 → AI界面测试 → 人工第N轮 → 回归 → 产品验收（可驳回回第3轮）→ 上线+生产验证
- **测试报告**：选项目+版本 → 聚合数据 → 生成 Markdown 报告 → 导出 docx
- **看板统计**：BUG 分布/趋势、用例通过率、流程看板
- **系统管理**：用户 / 角色（菜单权限）/ 菜单（动态路由）

## AI 能力说明

本期 AI 采用「数据聚合 + Jinja2 模板」生成结构化报告，LLM 调用已预留（`app/ai_client.py`）。如需接真实模型润色，在 `.env` 配置：

```
AI_ENABLED=true
AI_BASE_URL=<OpenAI 兼容端点>
AI_API_KEY=<key>
AI_MODEL=<model>
```
