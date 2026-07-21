<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>智能A股投资助手</h1>
      <p class="subtitle">基于人工智能的股票筛选与量化分析系统</p>
      <span class="version-badge">V2.0</span>
    </header>

    <!-- 早间资讯模块 -->
    <div class="news-section" v-if="newsData || newsLoading">
      <h2 class="section-title">早间财经资讯</h2>
      <div class="news-grid">
        <el-card class="news-card market-overview" shadow="hover">
          <template #header>
            <div class="news-card-header">
              <span class="news-icon">📊</span>
              <span>市场概览</span>
            </div>
          </template>
          <div class="market-data" v-if="newsData?.market_overview">
            <div class="market-item">
              <span class="market-label">上证指数</span>
              <span class="market-value" :class="getChangeClass(newsData.market_overview.shanghai?.change)">
                {{ newsData.market_overview.shanghai?.close?.toFixed(2) || '--' }}
                <span class="change-tag" :class="getChangeClass(newsData.market_overview.shanghai?.change)">
                  {{ formatChange(newsData.market_overview.shanghai?.change) }}
                </span>
              </span>
            </div>
            <div class="market-item">
              <span class="market-label">深证成指</span>
              <span class="market-value" :class="getChangeClass(newsData.market_overview.shenzhen?.change)">
                {{ newsData.market_overview.shenzhen?.close?.toFixed(2) || '--' }}
                <span class="change-tag" :class="getChangeClass(newsData.market_overview.shenzhen?.change)">
                  {{ formatChange(newsData.market_overview.shenzhen?.change) }}
                </span>
              </span>
            </div>
          </div>
          <div v-else class="no-data">暂无数据</div>
          <div class="news-time" v-if="newsData?.update_time">
            更新时间: {{ newsData.update_time }}
          </div>
        </el-card>

        <el-card class="news-card hot-sectors" shadow="hover">
          <template #header>
            <div class="news-card-header">
              <span class="news-icon">🔥</span>
              <span>热门板块</span>
            </div>
          </template>
          <div class="sectors-list" v-if="newsData?.hot_sectors?.length">
            <div class="sector-item" v-for="(sector, index) in newsData.hot_sectors" :key="index">
              <span class="sector-name">{{ sector['板块名称'] }}</span>
              <span class="sector-change" :class="getChangeClass(sector['涨跌幅'])">
                {{ formatChange(sector['涨跌幅']) }}
              </span>
            </div>
          </div>
          <div v-else class="no-data">暂无数据</div>
        </el-card>
      </div>
    </div>

    <!-- 无资讯提示 -->
    <el-alert
      v-else-if="!newsLoading && newsError"
      :title="newsError"
      type="warning"
      show-icon
      :closable="false"
      class="news-alert"
    />

    <!-- 第一行：查看选股、查看示例、策略回测 -->
    <div class="cards-grid row-1">
      <el-card class="card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-icon stocks">📈</span>
            <span>选股结果</span>
          </div>
        </template>
        <p>查看当前中长线和超短线选股结果，支持按行业、评分等多维度筛选</p>
        <template #footer>
          <el-button type="primary" @click="$router.push('/stocks')">查看选股</el-button>
        </template>
      </el-card>

      <el-card class="card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-icon chart">📉</span>
            <span>图表示例</span>
          </div>
        </template>
        <p>交互式Bokeh图表展示股票K线和技术指标，支持缩放、平移等操作</p>
        <template #footer>
          <el-button type="primary" @click="$router.push('/indicators')">查看示例</el-button>
        </template>
      </el-card>

      <el-card class="card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-icon backtest">🎯</span>
            <span>策略回测</span>
          </div>
        </template>
        <p>基于Backtrader引擎，对选股策略进行历史回测，验证策略有效性，包含SQN、SharpeRatio等指标</p>
        <template #footer>
          <el-button type="primary" @click="$router.push('/backtest')">运行回测</el-button>
        </template>
      </el-card>
    </div>

    <!-- 第二行：智能股票分析、技术指标详解 -->
    <div class="cards-grid row-2">
      <el-card class="card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-icon analysis">🧠</span>
            <span>智能股票分析</span>
          </div>
        </template>
        <p>输入股票代码，获取基于RSRS、KDJ、RSI、CCI等技术指标的综合买卖建议分析</p>
        <template #footer>
          <el-button type="primary" @click="goToAnalysis">开始分析</el-button>
        </template>
      </el-card>

      <el-card class="card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-icon indicators">📊</span>
            <span>技术指标详解</span>
          </div>
        </template>
        <p>详细了解17种技术指标的原理、计算方式和判定标准，包含KDJ、MACD、BOLL、RSI等</p>
        <template #footer>
          <el-button type="primary" @click="$router.push('/indicators-detail')">查看详情</el-button>
        </template>
      </el-card>
    </div>

    <div class="features">
      <h2>核心功能</h2>
      <div class="feature-tags">
        <el-tag type="info" effect="dark" class="feature-tag">stockstats指标</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">finta指标库</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">Backtrader回测</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">Bokeh可视化</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">KDJ分析</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">MACD分析</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">BOLL布林带</el-tag>
        <el-tag type="info" effect="dark" class="feature-tag">RSI分析</el-tag>
      </div>
    </div>

    <div class="api-section">
      <h3>API接口</h3>
      <el-table :data="apiList" stripe>
        <el-table-column prop="method" label="方法" width="80">
          <template #default="scope">
            <el-tag :type="scope.row.method === 'GET' ? 'success' : 'warning'" size="small">
              {{ scope.row.method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" />
        <el-table-column prop="desc" label="描述" />
      </el-table>
    </div>

    <!-- 智能股票分析对话框 -->
    <el-dialog v-model="analysisDialogVisible" title="智能股票分析" width="500px">
      <el-form @submit.prevent="startAnalysis">
        <el-form-item label="股票代码">
          <el-input v-model="analysisCode" placeholder="如: 600519" @keyup.enter="startAnalysis" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="analysisDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startAnalysis">分析</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()

// 早间资讯数据
const newsData = ref(null)
const newsLoading = ref(false)
const newsError = ref('')

function fetchNews() {
  newsLoading.value = true
  newsError.value = ''
  axios.get('/api/news')
    .then(res => {
      if (res.data.code === 0 && res.data.data) {
        newsData.value = res.data.data
      } else {
        newsError.value = res.data.message || '暂无早间资讯'
      }
    })
    .catch(err => {
      newsError.value = '获取早间资讯失败'
      console.error(err)
    })
    .finally(() => {
      newsLoading.value = false
    })
}

function getChangeClass(change) {
  if (change === null || change === undefined) return ''
  return change >= 0 ? 'positive' : 'negative'
}

function formatChange(change) {
  if (change === null || change === undefined) return '--'
  const sign = change >= 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}%`
}

onMounted(() => {
  fetchNews()
})

const apiList = ref([
  { method: 'GET', path: '/api/health', desc: '健康检查' },
  { method: 'GET', path: '/api/news', desc: '早间财经资讯' },
  { method: 'GET', path: '/api/stocks', desc: '获取选股结果' },
  { method: 'GET', path: '/api/indicators/{code}', desc: '获取股票指标图表' },
  { method: 'GET', path: '/api/indicators/config', desc: '获取指标配置' },
  { method: 'POST', path: '/api/backtest', desc: '运行回测' }
])

const analysisDialogVisible = ref(false)
const analysisCode = ref('')

function goToAnalysis() {
  analysisDialogVisible.value = true
}

function startAnalysis() {
  if (!analysisCode.value) {
    ElMessage.warning('请输入股票代码')
    return
  }
  analysisDialogVisible.value = false
  router.push(`/stock/${analysisCode.value}`)
}
</script>

<style scoped>
.dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  text-align: center;
  padding: 40px 0;
}

.dashboard-header h1 {
  font-size: 2.5rem;
  background: linear-gradient(90deg, #00d4ff, #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 10px;
}

/* 早间资讯样式 */
.news-section {
  margin-top: 30px;
}

.section-title {
  color: #fff;
  font-size: 1.3rem;
  margin-bottom: 16px;
}

.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.news-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.news-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
}

.news-icon {
  font-size: 20px;
}

.news-time {
  margin-top: 12px;
  font-size: 0.85rem;
  color: #888;
  text-align: right;
}

.market-data {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.market-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.market-label {
  color: #a0a0a0;
  font-size: 0.95rem;
}

.market-value {
  font-size: 1.1rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}

.change-tag {
  font-size: 0.85rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.positive {
  color: #f56c6c;
}

.negative {
  color: #67c23a;
}

.change-tag.positive {
  background: rgba(245, 108, 108, 0.2);
  color: #f56c6c;
}

.change-tag.negative {
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}

.sectors-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sector-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sector-item:last-child {
  border-bottom: none;
}

.sector-name {
  color: #c0c0c0;
}

.sector-change {
  font-weight: bold;
}

.no-data {
  color: #666;
  text-align: center;
  padding: 20px 0;
}

.news-alert {
  margin-top: 20px;
}

.subtitle {
  color: #b0b0b0;
  font-size: 1.1rem;
}

.version-badge {
  display: inline-block;
  background: linear-gradient(90deg, #00d4ff, #7c3aed);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  margin-top: 10px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-top: 20px;
}

.cards-grid.row-1 {
  margin-top: 40px;
}

.cards-grid.row-2 {
  margin-top: 24px;
}

.card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

:deep(.el-card__body) {
  color: #c0c0c0;
}

:deep(.el-card__header) {
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.2rem;
  font-weight: bold;
}

.card-icon {
  font-size: 24px;
}

.features {
  margin-top: 60px;
  text-align: center;
}

.features h2 {
  font-size: 1.8rem;
  color: #fff;
  margin-bottom: 30px;
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

:deep(.feature-tag) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  color: #e0e0e0 !important;
}

.api-section {
  margin-top: 60px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 24px;
}

.api-section h3 {
  color: #fff;
  margin-bottom: 16px;
}
</style>
