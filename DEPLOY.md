# 测试管理系统 — 服务器部署操作手册

适用架构：**一台 Linux 服务器**，Nginx 对外提供页面，并把 `/api`、`/uploads` 反代到 FastAPI。前端打包成静态文件，不再用 `npm run dev`。

推荐目录：

```
/opt/tester/
├─ backend/          # Python 后端
├─ frontend/         # 前端源码（构建用）
└─ www/              # 前端 dist 发布目录
```

下文以 **Ubuntu 22.04** 为例。域名用 `test.example.com`，请替换成你的域名或服务器 IP。

---

## 一、服务器准备

### 1. 基础软件

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nginx mysql-server git unzip
# Node 20（前端构建）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
python3.11 -V
```

CentOS / 宝塔环境：安装同等版本的 **Python 3.11、Node 20、MySQL 8、Nginx** 即可，命令按面板操作。

### 2. 防火墙

开放 `80`（HTTP）。有 HTTPS 再开 `443`。**不要把 8000 对公网开放**。

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 二、上传代码

任选一种：

```bash
# Git
sudo mkdir -p /opt/tester
sudo chown $USER:$USER /opt/tester
cd /opt/tester
git clone <你的仓库地址> .

# 或本机打包后 scp
# 在开发机：排除 node_modules、__pycache__、uploads
scp -r backend frontend user@服务器IP:/opt/tester/
```

不要把 `frontend/node_modules`、`backend/__pycache__` 传到服务器。

---

## 三、MySQL

```bash
sudo mysql
```

```sql
CREATE DATABASE tester DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tester'@'127.0.0.1' IDENTIFIED BY '请改成强密码';
GRANT ALL ON tester.* TO 'tester'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

记住库名、账号、密码，下一步写进 `.env`。

---

## 四、后端

```bash
cd /opt/tester/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 1. 环境变量

```bash
cp .env.example .env
nano .env
```

生产必须改这些项：

```env
APP_NAME=测试管理系统
ENV=production
DATABASE_URL=mysql+pymysql://tester:请改成强密码@127.0.0.1:3306/tester?charset=utf8mb4
SECRET_KEY=请换成至少 32 位随机字符串
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://test.example.com,https://test.example.com

# 可选：系统管理里也能配 AI，这里留空即可
AI_ENABLED=false
AI_BASE_URL=
AI_API_KEY=
AI_MODEL=
```

生成 `SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> 同源 Nginx 反代时，浏览器请求走 `/api`，一般不跨域。`CORS_ORIGINS` 仍写成实际访问地址更稳妥。

### 2. 首次初始化（建表 + 管理员）

```bash
cd /opt/tester/backend
source .venv/bin/activate
python -c "from app.seed import seed; seed()"
```

成功会打印：`[OK] init done: menus/roles/admin ready (admin / admin123)`

**立刻登录后台改掉 admin 密码。** 新用户密码至少 8 位。`ENV=production` 时未改 `SECRET_KEY` 会拒绝启动；Swagger `/docs` 也会关掉。

附件目录：

```bash
mkdir -p /opt/tester/backend/uploads
chmod 755 /opt/tester/backend/uploads
```

### 3. systemd 常驻

```bash
sudo nano /etc/systemd/system/tester-api.service
```

```ini
[Unit]
Description=Tester FastAPI
After=network.target mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/tester/backend
Environment=PATH=/opt/tester/backend/.venv/bin
EnvironmentFile=/opt/tester/backend/.env
ExecStart=/opt/tester/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

用户要对齐代码目录权限：

```bash
sudo chown -R www-data:www-data /opt/tester/backend
sudo chmod 640 /opt/tester/backend/.env
sudo systemctl daemon-reload
sudo systemctl enable --now tester-api
sudo systemctl status tester-api
curl -s http://127.0.0.1:8000/api/health
# 期望：{"status":"ok"}
```

看日志：`sudo journalctl -u tester-api -f`

---

## 五、前端构建

前端 axios 的 `baseURL` 是 `/api`，生产由 Nginx 反代，**构建时不用改接口地址**。

```bash
cd /opt/tester/frontend
npm ci
npm run build
sudo mkdir -p /opt/tester/www
sudo rsync -a --delete dist/ /opt/tester/www/
sudo chown -R www-data:www-data /opt/tester/www
```

产物在 `frontend/dist/`，发布目录用 `/opt/tester/www`。

---

## 六、Nginx

```bash
sudo nano /etc/nginx/sites-available/tester
```

```nginx
server {
    listen 80;
    server_name test.example.com;   # 没有域名就写服务器公网 IP

    client_max_body_size 20m;       # 与后端上传上限一致

    root /opt/tester/www;
    index index.html;

    # 前端 SPA：刷新 /flow、/handover/share/xxx 等路径不要 404
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;    # AI 生成用例较慢
    }

    # 附件（提测/需求/流程上传）
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        add_header X-Content-Type-Options nosniff always;
    }
}
```

启用并检查：

```bash
sudo ln -sf /etc/nginx/sites-available/tester /etc/nginx/sites-enabled/tester
sudo nginx -t
sudo systemctl reload nginx
```

浏览器访问：`http://服务器IP` 或 `http://test.example.com`  
默认账号：`admin` / `admin123`（登录后立刻改密）

### HTTPS（有域名时）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d test.example.com
```

证书会自动改 Nginx 并续期。

---

## 七、验收清单

| 检查项 | 方法 |
|---|---|
| 后端存活 | `curl http://127.0.0.1:8000/api/health` |
| 页面打开 | 浏览器打开站点首页，能进登录页 |
| 登录 | admin 登录后能进看板 |
| 动态路由 | 刷新 `/flow`、`/case` 不掉到 404 |
| 附件 | 需求/流程上传后能打开 |
| 提测/BUG 分享 | 打开 `/handover/share/xxx`、`/share/xxx` 免登录页能打开；链接 7 天过期 |
| API 文档 | `ENV=production` 时 `/docs` 已关闭。开发环境可看 `http://127.0.0.1:8000/docs` |

---

## 八、日常运维

### 更新代码

```bash
cd /opt/tester
git pull
# 后端
cd backend
source .venv/bin/activate
pip install -r requirements.txt
python -c "from app.seed import seed; seed()"   # 补菜单/缺列，可重复执行
sudo systemctl restart tester-api
# 前端
cd /opt/tester/frontend
npm ci
npm run build
sudo rsync -a --delete dist/ /opt/tester/www/
sudo systemctl reload nginx
```

`seed()` 只补菜单、角色、缺列，**不会清空业务数据**。

### 备份

```bash
# 数据库
mysqldump -u tester -p tester > /opt/backup/tester-$(date +%F).sql
# 附件
tar czf /opt/backup/uploads-$(date +%F).tgz -C /opt/tester/backend uploads
```

建议每天 crontab 备份，并拷到另一台机器。

### 常用命令

```bash
sudo systemctl restart tester-api
sudo systemctl status tester-api
sudo journalctl -u tester-api -n 200 --no-pager
sudo nginx -t && sudo systemctl reload nginx
```

---

## 九、常见问题

**1. 页面能开，登录 500 / 接口失败**  
- `curl 127.0.0.1:8000/api/health` 是否成功  
- `journalctl -u tester-api` 看 MySQL 连不上还是缺包  
- Nginx `error.log` 看有没有反代失败  

**2. 刷新子路由 404**  
Nginx 的 `location /` 必须有 `try_files $uri $uri/ /index.html;`

**3. 附件打不开**  
确认 `/uploads/` 反代到 8000，且 `backend/uploads` 对运行用户可写。

**4. 登录后马上过期**  
`SECRET_KEY` 改过会导致旧 token 全部失效，重新登录即可。多 worker 必须共用同一个 `.env` 里的 `SECRET_KEY`。

**5. AI 生成用例超时**  
Nginx `proxy_read_timeout` 已给 180s；系统管理 → API 管理里要启用一条配置。

**6. Windows 开发机怎么对齐这套架构**  
开发仍用 `python run.py` + `npm run dev`。上线不要在服务器跑 Vite dev。

---

## 十、和开发环境的差异（不要搞混）

| | 开发 | 生产 |
|---|---|---|
| 前端 | `npm run dev` 端口 5173，Vite 代理 `/api` | `npm run build`，Nginx 托管 dist |
| 后端 | `python run.py`（含 seed） | systemd + uvicorn，只监听 127.0.0.1:8000 |
| 数据库 | 本机 MySQL，弱密码仅限本机 | 独立账号、强密码、只允许 127.0.0.1 |
| 密钥 | `change-me-in-production` | 必须换成随机 `SECRET_KEY`，`ENV=production` |
| 管理员 | admin / admin123 | 部署后立刻改密；连续失败会锁定 15 分钟 |

按本手册做完后，用户只访问 80/443，看不到 8000 端口。
