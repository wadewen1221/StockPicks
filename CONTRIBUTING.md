# 贡献指南 (CONTRIBUTING)

感谢您对 Stock Picks V2 项目的关注！🎉

我们欢迎所有形式的贡献，包括但不限于：
- 🐛 Bug 报告和修复
- 💡 新功能建议和实现
- 📖 文档改进
- 🎨 界面优化
- ⚡ 性能提升
- 🧪 测试用例

---

## 📋 行为准则

- 尊重所有贡献者
- 友善对待新手提问
- 建设性反馈，不攻击个人
- 关注问题本身，而非争论谁对谁错

---

## 🚀 提交流程

### 1. Fork 仓库

点击右上角 "Fork" 按钮创建您自己的副本。

### 2. Clone 到本地

```bash
git clone https://github.com/<wadewen1221>/StockPicks.git
cd StockPicks
git remote add upstream https://github.com/<original-owner>/StockPicks.git
```

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或者 fix/bug-name, docs/doc-name, refactor/refactor-name
```

### 4. 开发

```bash
# 后端开发
cd backend
pip install -r ../requirements.txt
python start_v2.py  # 开发模式启动

# 前端开发
cd frontend
npm install
npm run dev  # http://localhost:3001
```

### 5. 提交

提交信息使用约定式：

```bash
git commit -m "feat: 添加新策略 XXX"
git commit -m "fix: 修复 RSRS 斜率计算 bug"
git commit -m "docs: 完善 README"
git commit -m "refactor: 拆分 stock_selector.py"
git commit -m "test: 添加技术指标单元测试"
```

**类型前缀**：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档
- `style:` 格式（不影响代码运行）
- `refactor:` 重构
- `test:` 测试
- `chore:` 杂项（如构建、依赖更新）

### 6. 推送 + 创建 PR

```bash
git push origin feature/your-feature-name
```

在 GitHub 上点击 "Compare & pull request" 创建 PR。

---

## 🐛 报告 Bug

提交 Bug 报告时，请提供：

1. **复现步骤**
2. **预期行为**
3. **实际行为**
4. **截图/日志**（如有）
5. **环境信息**：
   - 操作系统
   - Python 版本
   - Node.js 版本
   - 浏览器

使用 [Bug Report 模板](../../issues/new?template=bug_report.md)。

---

## 💡 提出新功能

在提交 Feature Request 前：

1. 搜索是否已有类似 Issue
2. 描述**问题**（不是"做什么"，而是"为什么需要"）
3. 描述您**期望的解决方案**
4. 列出**备选方案**
5. 添加**附加上下文**（截图、参考链接等）

使用 [Feature Request 模板](../../issues/new?template=feature_request.md)。

---

## 📝 代码规范

### Python

- 遵循 [PEP 8](https://pep8.org/)
- 使用 [Black](https://github.com/psf/black) 格式化
- 类型注解（typing module）
- 文档字符串（docstring）
- 中文注释可接受，但函数/类说明优先英文

```python
def calculate_rsrs(historical_data: list, window: int = 18) -> dict:
    """
    Calculate RSRS (Resistance Support Relative Strength) indicator.

    Args:
        historical_data: List of dicts with keys ['high', 'low', 'close']
        window: Number of periods for regression (default 18)

    Returns:
        dict with keys 'rsrs', 'rsrs_ma', 'slope', 'signal'
    """
```

### JavaScript / Vue

- 遵循 [Vue 3 Style Guide](https://v3.vuejs.org/style-guide/)
- 使用 ESLint + Prettier
- 组件命名：PascalCase（如 `StockDetail.vue`）
- Props 显式声明类型

```vue
<script setup>
defineProps({
  code: {
    type: String,
    required: true
  }
})
</script>
```

---

## 🧪 测试

### 后端

```bash
cd backend
python -m pytest tests/ -v
```

### 前端

```bash
cd frontend
npm run test
```

---

## 📦 依赖管理

### Python

新增依赖时**必须**更新 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

并在 README 中说明用途。

### Node

```bash
npm install <package>
# 然后提交 package.json + package-lock.json
```

---

## 🎯 优先事项

我们当前重点关注：

1. **Bug 修复**（P0：影响核心功能）
2. **跨平台兼容性**（macOS/Linux 路径适配）
3. **测试覆盖率**（目标 60%+）
4. **文档**（API 文档、架构说明）

---

## ❓ 提问

- 一般问题：[Discussions](../../discussions)
- Bug 报告：[Issues](../../issues)
- 安全问题：邮件维护者（不公开 Issue）

---

## 📜 许可

贡献的代码将采用 [MIT License](LICENSE)。

---

再次感谢您的贡献！🙏
