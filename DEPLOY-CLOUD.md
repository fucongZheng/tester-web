# 测试管理系统 — 容器云部署记录

记录时间：2026-09-10  
环境：东信容器云 UAT（南宁电信物理机）`nnptcuat`  
命名空间 / 关联项目：`ywzt`（业务中台）  
操作账号：`fucongzheng_d`（郑富聪）

覆盖：代码进 Bitbucket、流水线构建、Deployment / Service。单机 Nginx 部署见 `DEPLOY.md`。

---

## 1. 代码仓库

前后端拆成两个 Bitbucket 仓，默认分支都是 `master`（原先都是空仓）。

| 端 | 浏览 | HTTP clone |
|---|---|---|
| 前端 | http://bitbucket.caih.local/projects/CYZTDSJY/repos/test-manager-frontend/browse | `http://bitbucket.caih.local/scm/cyztdsjy/test-manager-frontend.git` |
| 后端 | http://bitbucket.caih.local/projects/CYZTDSJY/repos/test-manager-backend/browse | `http://bitbucket.caih.local/scm/cyztdsjy/test-manager-backend.git` |

未推：`node_modules/`、`dist/`、`.env`、`__pycache__/`、`uploads/` 实际附件、`.playwright-cli/`。

### 提交

前端：

| commit | 说明 |
|---|---|
| `a365ef0` | feat: 测试管理系统前端初始提交（Vue3 + Vite + Element Plus） |
| `e91fa67` | chore: 增加容器云构建所需 Dockerfile/build.sh/nginx.conf |

后端：

| commit | 说明 |
|---|---|
| `3be8285` | feat: 测试管理系统后端初始提交（FastAPI + SQLAlchemy） |
| `145ada7` | chore: 增加容器云构建所需 Dockerfile/build.sh |

---

## 2. 为流水线补的文件

容器云流水线默认执行 `sh -x ./build.sh`，再按仓库根目录 `Dockerfile` 打镜像。原仓库没有这两样，构建会直接失败，所以补进了 `master`。

### 前端

- `build.sh`：`npm ci` + `npm run build`
- `Dockerfile`：`nginx:1.25-alpine`，拷 `dist/` 和 `nginx.conf`
- `nginx.conf`：SPA `try_files`，刷新子路由不 404

前端镜像 **只托管静态页**，`/api`、`/uploads` 还要在 Ingress / Nginx 反代到后端。当前这份 `nginx.conf` 没有反代，前后端拆开部署后必须另配路由。

### 后端

- `build.sh`：占位（Python 无独立编译步骤）
- `Dockerfile`：`python:3.11-slim`，装 `requirements.txt`，`uvicorn app.main:app --host 0.0.0.0 --port 8000`

后端容器 **没有内置 MySQL**。要跑起来还需要：

- 集群内可达的 MySQL，库名建议 `tester`
- ConfigMap / Secret：`DATABASE_URL`、`SECRET_KEY`（生产至少 32 位随机串）、`ENV=production`、`CORS_ORIGINS`
- 持久卷挂 `uploads/`
- 首次启动执行一次 `python -c "from app.seed import seed; seed()"`（补菜单/角色/admin，不清业务数据）

---

## 3. 容器云流水线

控制台：持续集成/部署 → 流水线  
列表：http://www.caih.docker/cicd/pipeline?cluster=nnptcuat&namespace=ywzt

对照同类项目 `ztgk-web` / `ztgk-service` 建的，配置如下。

### test-manager-frontend

| 项 | 值 |
|---|---|
| 名称 | `test-manager-frontend` |
| 备注 | 测试管理系统-前端 |
| 关联项目 | `ywzt` |
| 代码语言 | Nodejs18 |
| 仓库 | `http://fucongzheng_d@bitbucket.caih.local/scm/cyztdsjy/test-manager-frontend.git` |
| 分支 | `master` |
| Git 用户 | `fucongzheng_d` |
| 清空代码缓存 | 是 |
| 自动触发 | 否 |
| 编译语句 | `sh -x ./build.sh`（平台默认） |
| 制品保存 | 关闭 |
| 镜像构建 | 开，内部仓库 **`dsjy`** |
| 镜像标签 | `${DIR_NAME}:${COMMIT_ID}-${TIMESTAMP}` |
| Dockerfile 目录 | `.` |
| 更新负载 | 关闭 |
| 上线申请镜像准备 | 关闭 |

### test-manager-backend

| 项 | 值 |
|---|---|
| 名称 | `test-manager-backend` |
| 备注 | 测试管理系统-后端 |
| 关联项目 | `ywzt` |
| 代码语言 | Python |
| 仓库 | `http://fucongzheng_d@bitbucket.caih.local/scm/cyztdsjy/test-manager-backend.git` |
| 分支 | `master` |
| Git 用户 | `fucongzheng_d` |
| 镜像仓库 | **`dsjy`** |
| 其余 | 与前端相同（更新负载关闭） |

配置页：

- 后端：http://www.caih.docker/cicd/pipeline/12280/test-manager-backend/2?cluster=nnptcuat&namespace=ywzt

---

## 4. 镜像

流水线已构建成功（2026-09-10 10:45 / 10:46）。Harbor 项目 `dsjy`：

| 镜像 | tag |
|---|---|
| `harbor.caih.local/dsjy/test-manager-frontend_e51410b` | `e91fa67-1789008385372` |
| `harbor.caih.local/dsjy/test-manager-backend_3a2eb6e` | `145ada7-1789008329132` |

---

## 5. Deployment / Service（已建）

命名空间 `ywzt`，对照 `ztgk-web` / `ztgk-service`：Deployment + LoadBalancer，不走 Ingress。

### 部署

| 名称 | 镜像 | 容器端口 | 副本 | 资源 |
|---|---|---|---|---|
| `test-manager-frontend` | 上表前端 tag | 80 | 1 / 1 | CPU 0.1/0.5 核，内存 128/256 Mi |
| `test-manager-backend` | 上表后端 tag | 8000 | 1 / 1 | CPU 0.2/1 核，内存 256/512 Mi |

Selector（绑 Service 用）：

- 前端：`www.caih.com/workloadselector=ywzt-p7kt2AwRyw3zFj9pVLWAQ`
- 后端：`www.caih.com/workloadselector=ywzt-oQa40vxQQ6BVbQWsjPFbo`

创建时平台会提示「GPU 最大值超出限制」（项目 GPU 配额为负），选确定继续即可，没有申请 GPU。

### 服务（LoadBalancer，随机外部 IP）

| 名称 | 集群内 | 外部访问 |
|---|---|---|
| `test-manager-frontend` | `test-manager-frontend.ywzt:80` | **10.96.137.245:80** |
| `test-manager-backend` | `test-manager-backend.ywzt:8000` | **10.96.137.246:8000** |

前端页面：`http://10.96.137.245/`  
后端健康检查：`http://10.96.137.246:8000/api/health`

这两个 IP 在集群 MetalLB 网段 `10.96.128.0/17`，办公网不一定能直接打开，可能要 VPN / 跳板。

---

## 6. 还没做（页面能开、登录会失败）

1. **前端 `/api`、`/uploads` 没有反代到后端。** 当前前端 nginx 只托管静态页。浏览器访问 `10.96.137.245/api/...` 会 404。要嘛改前端镜像加反代，要嘛加 Ingress：`/` → 前端 80，`/api`、`/uploads` → 后端 8000。
2. **后端没有配 MySQL / Secret。** 镜像默认连 `root:123456@127.0.0.1:3306/tester`，容器里没有 MySQL。需要：
   - 集群内可达的 MySQL（或新建实例）
   - Secret：`DATABASE_URL`、`SECRET_KEY`（≥32 位）、`ENV=production`、`CORS_ORIGINS`
   - 首次 `python -c "from app.seed import seed; seed()"`
   - `uploads/` 建议挂 PVC
3. 登录后立刻改掉 `admin / admin123`。

---

## 7. 注意

- Git 拉代码用的是个人账号，密码在流水线里。换人构建或改密后要同步改流水线。
- 前端 axios `baseURL` 是 `/api`，生产必须同源反代，不要让浏览器直连 8000。
- `ENV=production` 时弱 `SECRET_KEY` 会拒绝启动，`/docs` 也会关掉。
- 本机全栈 GitHub 仓 `tester-web` **没有**跟着推；Bitbucket 才是容器云用的源。
