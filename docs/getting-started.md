# 快速上手

5 分钟跑通 A股智能投资助手 V2。

## 🎯 三种使用方式

### 方式一：Docker Compose (零依赖推荐)

**前置条件**: Docker Desktop

```bash
# 1. 克隆项目
git clone https://github.com/your-username/stock-picks-v2.git
cd stock-picks-v2

# 2. 一键启动 (后端 + 前端)
docker-compose up -d

# 3. 查看状态
docker-compose ps

# 4. 浏览器访问
# 前端: http://localhost:8080
# 后端: http://localhost:5001/api/health
```

**常用命令**:

```bash
docker-compose logs -f backend    # 实时日志
docker-compose down              # 停止并清理
docker-compose restart backend   # 重启后端
```

### 方式二：本地开发模式

**前置条件**: Python 3.11+, Node 18+

```bash
# 后端
cd backend
pip install -r requirements.txt
python start_v2.py               # http://localhost:5001

# 前端 (另一个终端)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

### 方式三：仅使用后端 API

```bash
cd backend
pip install -r requirements.txt
python -c "
from selector import StockSelector
selector = StockSelector()
picks = selector.run_comprehensive_strategy()
print(picks[:5])
"
```

## 🔧 环境变量配置

复制 `.env.example` 为 `.env` 并修改:

```bash
# 后端 .env
STOCK_PICKS_DATA=D:/stock-picks/data
STOCK_PICKS_FISCAL=D:/stock-picks/data/fiscal
API_PORT=5001
DEBUG_MODE=false
COOKIE_SECRET=your-secret-here-min-32-chars
```

!!! tip "Windows 用户"

    `D:/stock-picks/data` 是 Windows 软链接位置，存放 1500+ 股票历史 JSON。

!!! warning "Linux / macOS 用户"

    需要先下载历史数据 (参考 [数据更新](deployment/data.md))。

## ✅ 验证安装

```bash
# 后端健康检查
curl http://localhost:5001/api/health

# 应返回
{"status": "ok", "data_files": 1500, "timestamp": "..."}
```

## 🚨 常见问题

### Q1. 启动报 "ModuleNotFoundError: No module named 'xxx'"

```bash
pip install -r requirements.txt
# 或单独安装
pip install xxx
```

### Q2. 端口 5001 被占用

修改 `.env`:
```
API_PORT=5500
```

或查找占用进程:
```powershell
# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

### Q3. 历史数据加载慢

- 检查 `D:/stock-picks/data/historical` 是否为软链接
- 1500+ 股票首次加载 ~30 秒属正常

## 📚 下一步

- 📖 阅读 [选股策略](strategies/overview.md) 了解 4 套策略逻辑
- 🐳 学习 [Docker 部署](deployment/docker.md) 进阶用法
- 🧪 跑 [测试套件](contributing/testing.md) 验证功能