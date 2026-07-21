# 提 PR 流程

> 完整的 Pull Request 提交指南 — 从 fork 到合并

## 📚 完整 DOCX 手册

如果你不熟悉 PR 流程，可以下载我们的 [PR 操作手册 (DOCX, 8 页)](https://github.com/wadewen1221/StockPicks/releases) 手把手教学。

## 5 分钟提 PR 流程

### 1. Fork 项目

访问 https://github.com/wadewen1221/StockPicks
点击右上角 **Fork** → 你的账号下就有了 `wadewen1221/StockPicks`

### 2. Clone 到本地

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
git remote add upstream https://github.com/wadewen1221/StockPicks.git
```

### 3. 创建功能分支

```bash
git checkout -b feature/add-new-indicator
```

### 4. 修改代码

编辑代码，确保:

- ✅ 新增函数加类型提示
- ✅ 关键函数加单元测试
- ✅ 跑 `pytest tests/` 全绿
- ✅ 跑 `mypy selector/ config.py --ignore-missing-imports --no-strict-optional` 0 错误

### 5. 提交

```bash
git add .
git commit -m "feat(indicators): 添加布林带宽度指标 BOLL_WIDTH"
git push origin feature/add-new-indicator
```

### 6. 提 PR

访问你 fork 的 GitHub 页面，会看到:

> **Compare & pull request** 按钮

点击 → 填写:

- **Title**: 简洁描述 (例: `feat(indicators): 添加 BOLL_WIDTH`)
- **Description**: 关联 issue、说明改动、贴测试结果
- **Reviewers**: 选择 `@maintainer`

提交后 CI 会自动跑测试，绿色 ✅ 即可等待 review。

## Commit 规范

参考 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 取值

| Type | 用途 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 仅文档改动 |
| `style` | 格式调整 (无逻辑影响) |
| `refactor` | 重构 (既非 feat 也非 fix) |
| `test` | 加测试 |
| `chore` | 杂项 (依赖更新、CI 调整) |

### 示例

```bash
git commit -m "feat(indicators): 添加 KDJ 钝化检测"
git commit -m "fix(data_fetcher): 修复除权日数据缺失"
git commit -m "docs(readme): 更新 Docker 部署章节"
git commit -m "test(scorer): 加 RSRS 阈值回归测试"
```

## CI 检查

提 PR 后 GitHub Actions 自动跑 5 个 job:

| Job | 作用 |
| --- | --- |
| `test-backend` | pytest 87 用例 × 4 平台组合 |
| `test-frontend` | npm build × 6 平台组合 |
| `typecheck` | mypy 0 错误检查 |
| `lint` | flake8 + pyflakes (best-effort) |
| `docs` | MkDocs 文档站构建 (仅 master) |

**只有全部绿色 ✅ 才能合并。**

## Review 流程

PR 提交流程:

1. **作者**: 提 PR → 等 CI
2. **Reviewer**: 看 diff → 评论 / approve / request changes
3. **作者**: 根据评论修改 → push 新 commit
4. **Reviewer**: re-review → approve
5. **Maintainer**: squash merge 到 master

详细评审要点见 GitHub PR Review 官方文档。

## 常见问题

### Q1. 提 PR 后 CI 红了

```bash
# 本地复现
cd backend
python -m pytest tests/ -v

# 修复后
git commit -m "fix: 修复测试失败"
git push
# PR 会自动更新
```

### Q2. 需要同步上游最新代码

```bash
git fetch upstream
git checkout master
git merge upstream/master
git checkout feature/your-branch
git rebase master
git push origin feature/your-branch --force-with-lease
```

### Q3. 想撤回 PR

```bash
# 关闭 PR
gh pr close <PR_NUMBER>

# 或在 GitHub 网页 → "Close pull request" 按钮
```

### Q4. Commit 历史想合并

```bash
git rebase -i HEAD~3
# 把后面的 pick 改成 squash
```

!!! warning "Rebase 风险"

    不要在已经推过的共享分支上 rebase，会破坏他人协作。在自己的 feature branch 上可以。

## 🐛 Issue 提交

发现 bug 或想提建议:

1. 访问 https://github.com/wadewen1221/StockPicks/issues
2. 点击 **New issue**
3. 选择模板:
   - 🐛 **Bug Report** — 报告 bug
   - ✨ **Feature Request** — 提建议
   - 📖 **Documentation** — 文档改进
4. 填写模板字段，提交

## 💬 讨论

- GitHub Discussions: 通用讨论
- GitHub Issues: 具体 bug / 功能

欢迎贡献！🎉