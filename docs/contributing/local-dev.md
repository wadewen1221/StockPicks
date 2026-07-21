# 本地开发

本地贡献代码的开发环境搭建。

## 仓库结构

```
StockPicks/
├── backend/                  # 后端 (Python)
│   ├── selector/             # 选股核心模块 (V2.1 拆分后)
│   │   ├── _types.py         # 共享类型别名
│   │   ├── cache.py
│   │   ├── data_fetcher.py
│   │   ├── fiscal.py
│   │   ├── indicators.py
│   │   ├── scorer.py
│   │   ├── strategies.py
│   │   └── __init__.py
│   ├── tests/                # pytest 单元测试
│   ├── handlers/             # HTTP handlers
│   ├── jobs/                 # 定时任务
│   ├── main.py               # 入口
│   ├── config.py             # 配置
│   └── requirements.txt
├── frontend/                 # 前端 (Vue 3)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/                     # MkDocs 文档源文件
├── .github/
│   └── workflows/ci.yml      # GitHub Actions
├── docker-compose.yml
├── Dockerfile                # 后端镜像
├── mkdocs.yml                # 文档站配置
└── README.md
```

## 环境准备

### 1. 克隆 + 装依赖

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks

# 后端
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest + mypy

# 前端
cd ../frontend
npm install
```

### 2. 配置 IDE

推荐 **VS Code** + Python 扩展。

`.vscode/settings.json` (项目根):

```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

## 开发流程

### 1. 拉取最新代码

```bash
git checkout master
git pull upstream master
```

### 2. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 编码

- ✅ 关键函数加类型提示
- ✅ 复杂逻辑加 docstring
- ✅ 新增模块加 `__all__`

### 4. 测试

```bash
cd backend
python -m pytest tests/ -v
mypy selector/ config.py --ignore-missing-imports --no-strict-optional
```

### 5. 提交

```bash
git add .
git commit -m "feat(selector): 添加新的技术指标"
git push origin feature/your-feature-name
```

## 添加新指标示例

假设添加 **BOLL_WIDTH** 指标:

### 1. 在 indicators.py 加函数

```python
def calculate_boll_width(hist_data: HistData) -> Optional[float]:
    """布林带宽度 = (上轨 - 下轨) / 中轨

    反映波动率，高位预示震荡，低位预示趋势。

    Args:
        hist_data: 历史 K 线数据

    Returns:
        布林带宽度 (0-1 浮点), 数据不足返回 None
    """
    close = [d['close'] for d in hist_data]
    if len(close) < 20:
        return None
    boll = calculate_bollinger(close)
    return (boll['upper'] - boll['lower']) / boll['middle']
```

### 2. 加测试

`tests/test_indicators.py`:

```python
def test_calculate_boll_width():
    data = [{'close': 100 + i * 0.5} for i in range(30)]
    width = calculate_boll_width(data)
    assert width is not None
    assert 0 < width < 1  # 合理范围
```

### 3. 在策略中集成

`selector/strategies.py`:

```python
indicators = {
    ...,
    'boll_width': calculate_boll_width(hist_data),
}
```

### 4. 提交

```bash
git add backend/selector/indicators.py backend/tests/test_indicators.py
git commit -m "feat(indicators): 添加 BOLL_WIDTH 布林带宽度指标

- 实现 calculate_boll_width 函数
- 加单元测试
- 集成到综合策略"
git push origin feature/boll-width
```

## 代码风格

### Python

- **PEP 8** 基础
- 类型提示推荐 (mypy 0 错误)
- 行宽 ≤ 120 字符
- docstring 用 Google 风格

### Vue / JavaScript

- **ESLint** 推荐
- Vue 3 Composition API
- 组件命名 PascalCase

### 命名约定

| 类型 | 风格 | 示例 |
| --- | --- | --- |
| 模块 | snake_case | `data_fetcher.py` |
| 类 | PascalCase | `StockSelector` |
| 函数 | snake_case | `calculate_ma` |
| 常量 | UPPER_SNAKE | `STRATEGY_WEIGHTS` |
| 私有函数 | _leading | `_validate_input` |

## 调试技巧

### 后端

```python
# 加断点
import pdb; pdb.set_trace()

# 或用 IDE 的调试器 (推荐)
```

### 前端

```javascript
// 浏览器 DevTools → Sources → 设置断点
// Vue DevTools 扩展
```

### 单元测试调试

```bash
cd backend
pytest tests/test_indicators.py::test_calculate_ma -v -s --pdb
```