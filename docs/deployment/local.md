# 本地部署

不依赖 Docker 的本地开发部署方式。

## 环境要求

| 软件 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.11 / 3.12 | 后端 |
| Node.js | 18 / 20 / 22 | 前端构建 |
| Tornado | 6.x | 后端 Web 框架 |
| Vue | 3.5+ | 前端框架 |

## 后端启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`:

```bash
# Linux/macOS
cp .env.example .env

# Windows
copy .env.example .env
```

修改关键配置:

```ini
STOCK_PICKS_DATA=D:/stock-picks/data
STOCK_PICKS_FISCAL=D:/stock-picks/data/fiscal
API_PORT=5001
DEBUG_MODE=true
COOKIE_SECRET=please-change-me-min-32-chars-long-secret
```

### 3. 启动服务

```bash
# 方式一: 开发模式 (热重载)
python start_v2.py

# 方式二: 生产模式 (Gunicorn)
gunicorn main:app --bind 0.0.0.0:5001 --workers 4

# 方式三: Windows 一键
start_prod.bat
```

### 4. 验证

```bash
curl http://localhost:5001/api/health
# 应返回: {"status": "ok", "data_files": 1500, ...}
```

## 前端启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
# 访问 http://localhost:5173
```

### 3. 生产构建

```bash
npm run build
# 产物在 frontend/dist/
```

### 4. 预览构建产物

```bash
npm run preview
```

## 数据准备

需要 1500+ 股票历史数据 (约 1.5 GB):

```bash
# 方式一: 使用项目数据软链接 (Windows)
# 确保 D:/stock-picks/data 是有效 junction
# 默认配置已指向此位置

# 方式二: 下载数据
python -m jobs.data_job --download

# 方式三: 自定义路径 (在 .env 设置)
STOCK_PICKS_DATA=/your/custom/path
```

## 定时任务

`backend/scheduler.py` 默认启用定时任务:

| 任务 | 频率 | 功能 |
| --- | --- | --- |
| 数据更新 | 交易日 17:30 | 拉取当日行情 |
| 选股计算 | 交易日 18:30 | 运行三步法选股 + 回测 |
| 新闻更新 | 每日 07:00 | 抓取早间资讯 |

> 注：财务更新（季度财报拉取）和周日周报任务已取消，不再调度。
> 所有任务时区为 `Asia/Shanghai`，使用 `apscheduler` `BackgroundScheduler`。

关闭定时任务: 设置环境变量 `ENABLE_SCHEDULER=false`

## 调试技巧

```python
# 后端日志位置
backend/logs/app.log

# 选股结果缓存
backend/stock_cache.json

# 前端 console
# 浏览器 DevTools → Console → 看 Network / Vue
```

## 常见问题

### 端口被占用

```powershell
# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

```bash
# Linux/macOS
lsof -i :5001
kill -9 <PID>
```

### 数据加载慢

- 检查 `D:/stock-picks/data` 软链接是否正常
- 首次启动加载 1500+ 股票需 ~30 秒

### 定时任务不工作

- Windows: 用 `pythonw.exe scheduler.py` 而非 `python.exe`
- Linux: 用 systemd / supervisor / cron