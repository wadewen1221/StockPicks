# 智能A股投资助手 V2 - 生产部署指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
└──────────────────────────┬────────────────────────────────┘
                           │ HTTP/HTTPS
┌──────────────────────────▼────────────────────────────────┐
│                     Nginx (可选)                           │
│                   反向代理 + 静态文件                       │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                  Gunicorn + Tornado                        │
│                   Python WSGI 服务器                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  /api/*  →  Tornado API Handler                      │ │
│  │  /*      →  静态文件 (index.html + assets)            │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────┬────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐    ┌─────────▼────────┐
     │   历史数据目录     │    │   SQLite/JSON     │
     │  historical/*.csv │    │   选股缓存        │
     └───────────────────┘    └──────────────────┘
```

---

## 方式一：一键打包部署（推荐）

### 1. 安装依赖

```bash
cd D:\stock-picks-v2

# 安装 Python 生产依赖
pip install gunicorn

# 安装 Node.js 生产依赖 (如果node_modules已存在可跳过)
cd frontend
npm install
```

### 2. 一键构建 + 打包

```bash
# 在项目根目录执行
python -m pip install -r requirements.txt

# 构建前端
cd frontend
npm run build

# 复制构建产物到后端静态目录
cp -r frontend/dist/* backend/static/

# 或者在 Windows 上
xcopy /E /I frontend\dist backend\static
```

### 3. 启动服务

**开发/测试模式：**
```bash
cd backend
python start_v2.py
```

**生产模式：**
```bash
cd backend
# 设置环境变量
set COOKIE_SECRET=your-strong-random-secret-here
set DEBUG=False
set ALLOWED_ORIGINS=https://your-domain.com

# 使用 Gunicorn 启动
gunicorn -w 4 -b 0.0.0.0:5001 main:app
```

---

## 方式二：手动分步部署

### 前端构建

```bash
cd D:\stock-picks-v2\frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 构建产物在 dist/ 目录
```

### 复制静态文件

```bash
# Windows
xcopy /E /I frontend\dist backend\static

# Linux/Mac
cp -r frontend/dist/* backend/static/
```

### 后端配置

创建生产环境配置文件 `backend/prod.env`：

```bash
# Cookie密钥（必须设置，使用强随机字符串）
COOKIE_SECRET=your-strong-random-secret-here-change-this-in-production

# 生产模式关闭调试
DEBUG=False

# 允许的来源（配置你的域名）
ALLOWED_ORIGINS=https://your-domain.com
```

### 使用 Gunicorn 启动

```bash
cd backend

# 安装 gunicorn
pip install gunicorn

# 启动（4个工作进程，绑定到5001端口）
gunicorn -w 4 -b 0.0.0.0:5001 main:app
```

### 使用 Systemd 管理服务 (Linux)

创建 `/etc/systemd/system/stock-picks-v2.service`：

```ini
[Unit]
Description=Stock Picks V2 Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/stock-picks-v2/backend
Environment="COOKIE_SECRET=your-secret-here"
Environment="DEBUG=False"
Environment="ALLOWED_ORIGINS=https://your-domain.com"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable stock-picks-v2
sudo systemctl start stock-picks-v2
```

---

## 方式三：Docker 部署

### 创建 Dockerfile

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制前端构建产物
COPY frontend/dist ./backend/static/

# 复制后端代码
COPY backend/ ./backend/

WORKDIR /app/backend

# 创建非root用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "main:app"]
```

### 创建 docker-compose.yml

```yaml
version: '3.8'
services:
  stock-picks-v2:
    build: .
    ports:
      - "5001:5001"
    environment:
      - COOKIE_SECRET=your-strong-secret-here
      - DEBUG=False
      - ALLOWED_ORIGINS=https://your-domain.com
    volumes:
      - ./data:/app/backend/data
      - ./logs:/app/backend/logs
    restart: unless-stopped
```

### 启动

```bash
docker-compose up -d
```

---

## Nginx 配置（生产环境推荐）

即使使用 Gunicorn，生产环境仍推荐用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 静态文件缓存
    location /static/ {
        alias /path/to/stock-picks-v2/backend/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Vue Router History 模式
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 生产环境检查清单

### 安全配置
- [ ] `COOKIE_SECRET` 设置为强随机字符串（至少32字符）
- [ ] `DEBUG=False` 关闭调试模式
- [ ] `ALLOWED_ORIGINS` 配置为具体域名，不使用 `*`
- [ ] 启用 HTTPS（使用 Let's Encrypt 免费证书）
- [ ] 配置 Nginx 安全头

### 数据备份
- [ ] 定期备份 `backend/stock_cache.json`
- [ ] 定期备份 `backend/data/` 目录
- [ ] 备份历史数据 `data/historical/*.csv`

### 监控
- [ ] 配置日志文件输出（`backend/logs/`）
- [ ] 监控进程自动重启（Systemd 或 Docker）
- [ ] 配置 disk space 告警

### 性能
- [ ] 使用 Gunicorn 多进程（`-w 4`）
- [ ] Nginx 静态文件缓存
- [ ] 考虑使用 CDN 加速静态资源

---

## 快速启动命令汇总

```bash
# 完整构建流程
cd D:\stock-picks-v2
npm run build --prefix frontend
xcopy /E /I frontend\dist backend\static\

# 生产启动
cd backend
set COOKIE_SECRET=my-production-secret-2026
set DEBUG=False
set ALLOWED_ORIGINS=https://my-domain.com
gunicorn -w 4 -b 0.0.0.0:5001 main:app
```

---

## 故障排查

**端口被占用：**
```bash
# Windows
netstat -ano | findstr :5001
taskkill /F /PID <PID>

# Linux
lsof -i :5001
kill -9 <PID>
```

**静态文件不更新：**
```bash
# 清除浏览器缓存，或强制刷新 Ctrl+F5
# 确认 dist 内容已复制到 static 目录
```

**API 请求失败：**
```bash
# 检查后端日志
# 确认 gunicorn 进程运行中
# 测试 API 端点
curl http://localhost:5001/api/health
```
