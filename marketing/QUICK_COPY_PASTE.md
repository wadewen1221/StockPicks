# 🚀 项目发布工具包 (Stock Picks V2)

> ⚠️ 浏览器自动化在国内网络环境不可达(V2EX 等平台连接超时)
> ✅ 已为你准备好 5 平台的完整文案 + README 优化版,**直接复制粘贴即可发布**

---

## 📂 已生成的文件清单

| 文件 | 用途 | 状态 |
|---|---|---|
| `marketing/01_v2ex_share.md` | V2EX 分享创造完整帖 | ✅ 已生成 |
| `marketing/02_juejin_article.md` | 掘金技术长文 | ✅ 已生成 |
| `marketing/03_zhihu_answer.md` | 知乎回答/专栏 | ✅ 已生成 |
| `marketing/04_okjike_post.md` | 即刻动态 | ✅ 已生成 |
| `marketing/05_hirey_listing.md` | Hi listing 配置 | ✅ 已生成 |
| `README.md` | **双语版,带 badges,GitHub 优化** | ✅ 已重写 |
| `marketing/QUICK_COPY_PASTE.md` | 本文件 | ✅ |

---

## 🎯 一键发布流程

### Step 1: README 推送 (5 分钟)

```powershell
cd D:\stock-picks-v2
git add README.md
git commit -m "docs(readme): 双语 + badges + Star History 钩子"
git push origin master
```

### Step 2: V2EX 发帖 (10 分钟)

1. 打开 `marketing/01_v2ex_share.md`
2. 标题和正文都按"代码块"标识的来
3. 登录 v2ex.com → 进入 https://www.v2ex.com/newpost?node=create
4. 选择节点: **`create`** (分享创造)
5. 粘贴标题 + 正文
6. 发布!

### Step 3: 掘金发长文 (20 分钟)

1. 打开 `marketing/02_juejin_article.md`
2. juejin.cn → 发布沸点/文章
3. 选择文章类型,粘贴正文
4. 加标签: `Python` `量化` `选股` `A股` `Backtrader` `开源`
5. 发布!

### Step 4: 知乎发回答 (10 分钟)

1. 打开 `marketing/03_zhihu_answer.md`
2. 找一个合适问题(如"如何用 Python 进行 A 股量化投资?") → 写回答
3. 或者新建专栏文章
4. 发布!

### Step 5: 即发动态 (5 分钟)

1. 打开 `marketing/04_okjike_post.md`
2. 复制主内容
3. okjike.com → 发动态 → 粘贴
4. 配 README 截图作为图片附件

### Step 6: Hirey listing (5 分钟,可选)

1. 打开 `marketing/05_hirey_listing.md`
2. 把内容填入 `agent_listings.upsert` 调用
3. 自动推送 Hi 平台

---

## 💡 发布顺序建议

| 时间 | 平台 | 理由 |
|---|---|---|
| Day 0 | README push + Hi listing | 让 GitHub 看着 professional |
| Day 1 | V2EX | 程序员/投资圈,流量最快 |
| Day 2 | 掘金 | 长尾流量,沉淀技术读者 |
| Day 3 | 知乎 | SEO 友好,被动流量 |
| Day 4 | 即刻 | 投资圈二次曝光 |

**Day 1-3 是关键引流期**,同步在多个地方铺开。

---

## 📸 建议配图

| 图 | 截图位置 |
|---|---|
| README 头图 | Pages 首页 https://wadewen1221.github.io/StockPicks/ |
| Bokeh K 线 | 启动 web 后访问 /api/indicators/000001 |
| 选股结果列表 | 启动 web 后访问 /api/stocks |
| Docker 启动截图 | 跑完 `docker-compose up` 后 |

---

## 🌐 国外平台(可选)

如果之后访问稳定了,可以考虑:

| 平台 | 文案 |
|---|---|
| Hacker News (Show HN) | 简化版 V2EX 文案,英文 |
| Reddit r/algotrading | 翻译 V2EX |
| Dev.to | 翻译掘金长文 |
| Product Hunt | 上架产品页 |

---

## ❓ FAQ

### Q: README 改了会不会影响 Pages?
A: 不会。Pages 由 `mkdocs.yml` 构建,跟 README 独立。README 是 GitHub 主页显示。

### Q: Hi listing 推什么合适?
A: `recruiting` 类型不太合适(不是真招人),建议 type=`other` 或新建 type。可考虑改成 `social_or_friendship` 类型找共同兴趣的开发者一起贡献。

### Q: 浏览器自动化为什么失败?
A: 国内网络环境 V2EX 直接 `ERR_CONNECTION_TIMED_OUT`,GitHub 都得绕道。你在任何能访问 v2ex.com 的环境粘贴 `01_v2ex_share.md` 内容即可。

### Q: 文案太长,需要简化吗?
A: 各平台已分别优化过长度。V2EX/即刻偏短,掘金/知乎偏长。按平台调好的不用改。

---

**老板,所有物料齐了,你直接复制粘贴就行!** 🚀