<template>
  <div class="stock-detail">
    <el-page-header @back="$router.push('/stocks')" :content="`${code} 股票详情`">
    </el-page-header>

    <div v-if="loading" class="loading-text">加载中...</div>
    <div v-else-if="errorMsg" class="error-text">{{ errorMsg }}</div>
    <template v-else>
      <!-- 基础信息卡片 -->
      <el-row :gutter="20" class="info-row">
        <el-col :span="6">
          <el-card>
            <div class="stock-name">{{ stockData.name || code }}</div>
            <div class="stock-code">{{ code }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="label">最新价</div>
            <div class="value price">{{ stockData.price || '-' }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="label">涨跌幅</div>
            <div class="value" :class="computedChangePct >= 0 ? 'up' : 'down'">
              {{ computedChangePct >= 0 ? '+' : '' }}{{ computedChangePct.toFixed(2) }}%
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="label">数据天数</div>
            <div class="value">{{ stockData.total_days || 0 }}天</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 综合买卖建议卡片 -->
      <el-card class="analysis-card" v-if="analysisData">
        <template #header>
          <span>综合买卖建议</span>
          <el-tag :type="getRecommendationType(analysisData.recommendation)" style="margin-left: 12px;">
            {{ analysisData.recommendation }}
          </el-tag>
        </template>
        <div class="analysis-content">
          <p class="recommendation-desc">{{ analysisData.recommendation_desc }}</p>

          <el-row :gutter="20">
            <el-col :span="8">
              <div class="score-box buy">
                <div class="score-label">买入评分</div>
                <div class="score-value">{{ analysisData.buy_score || 0 }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="score-box sell">
                <div class="score-label">卖出评分</div>
                <div class="score-value">{{ analysisData.sell_score || 0 }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="info-box">
                <div class="score-label">买卖时机</div>
                <div class="timing-value" :class="'timing-' + analysisData.timing_signal">
                  {{ getTimingText(analysisData.timing_signal) }}
                </div>
              </div>
            </el-col>
          </el-row>

          <!-- 新增字段展示 -->
          <el-row :gutter="20" class="new-indicators-row">
            <el-col :span="8">
              <div class="indicator-mini">
                <div class="indicator-label">趋势评分</div>
                <div class="indicator-value">{{ analysisData.trend_score || 0 }}/100</div>
                <el-tag size="small" :type="getTrendType(analysisData.trend_level)">
                  {{ getTrendText(analysisData.trend_level) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="indicator-mini">
                <div class="indicator-label">市场环境</div>
                <div class="indicator-value">{{ getMarketText(analysisData.market_env) }}</div>
                <span class="confidence-text">置信度: {{ analysisData.market_confidence || 0 }}%</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="indicator-mini">
                <div class="indicator-label">当前位置</div>
                <div class="indicator-value" :class="'position-' + analysisData.price_position">
                  {{ getPositionText(analysisData.price_position) }}
                </div>
                <span class="timing-desc-text" v-if="analysisData.timing_desc">{{ analysisData.timing_desc }}</span>
              </div>
            </el-col>
          </el-row>

          <!-- 买入信号列表 -->
          <div v-if="analysisData.buy_signals?.length" class="signals-section">
            <div class="signals-title">买入信号</div>
            <el-tag v-for="(signal, idx) in analysisData.buy_signals" :key="'buy-'+idx"
              type="success" size="small" class="signal-tag">
              {{ signal.indicator }}: {{ signal.signal }} ({{ signal.action }})
            </el-tag>
          </div>

          <!-- 卖出信号列表 -->
          <div v-if="analysisData.sell_signals?.length" class="signals-section">
            <div class="signals-title">卖出信号</div>
            <el-tag v-for="(signal, idx) in analysisData.sell_signals" :key="'sell-'+idx"
              type="danger" size="small" class="signal-tag">
              {{ signal.indicator }}: {{ signal.signal }} ({{ signal.action }})
            </el-tag>
          </div>

          <!-- 数据质量提示 -->
          <div v-if="analysisData.data_quality && !analysisData.data_quality.overall" class="quality-warning">
            <el-icon><Warning /></el-icon>
            <span>部分指标数据计算失败，分析结果仅供参考</span>
          </div>
        </div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>K线与指标图表</span>
        </template>
        <div v-if="chartLoading" class="loading-text">图表加载中...</div>
        <div v-else-if="chartError" class="error-text">{{ chartError }}</div>
        <div v-show="!chartLoading && !chartError" ref="chartRef" class="chart-container"></div>
      </el-card>

      <el-card class="indicators-card">
        <template #header>技术指标</template>
        <el-descriptions :column="3" border v-if="indicators">
          <el-descriptions-item label="KDJ">
            K: {{ formatVal(indicators.kdjk) }} |
            D: {{ formatVal(indicators.kdjd) }} |
            J: {{ formatVal(indicators.kdjj) }}
          </el-descriptions-item>
          <el-descriptions-item label="MACD">
            {{ formatVal(indicators.macd) }} |
            Signal: {{ formatVal(indicators.macds) }}
          </el-descriptions-item>
          <el-descriptions-item label="BOLL">
            {{ formatVal(indicators.boll) }} |
            UB: {{ formatVal(indicators.boll_ub) }} |
            LB: {{ formatVal(indicators.boll_lb) }}
          </el-descriptions-item>
          <el-descriptions-item label="RSI(6)">
            {{ formatVal(indicators.rsi_6) }}
          </el-descriptions-item>
          <el-descriptions-item label="RSI(12)">
            {{ formatVal(indicators.rsi_12) }}
          </el-descriptions-item>
          <el-descriptions-item label="CCI">
            {{ formatVal(indicators.cci) }}
          </el-descriptions-item>
          <el-descriptions-item label="RSRS斜率" :span="3">
            {{ formatVal(indicators.rsrs?.slope) }} (信号: {{ indicators.rsrs?.signal || '-' }})
          </el-descriptions-item>
        </el-descriptions>
        <div v-else class="no-data">暂无指标数据</div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getStock, getIndicators, getStockAnalysis } from '../api/stock'
import { ElMessage, Warning } from 'element-plus'

const route = useRoute()
const code = computed(() => route.params.code)

const loading = ref(false)
const errorMsg = ref('')
const chartLoading = ref(false)
const chartError = ref('')
const stockData = ref({})
const indicators = ref(null)
const analysisData = ref(null)
const chartRef = ref(null)
const chartScript = ref('')

// ‌仍 P0 修复:兑底涨跌幅计算，以前用 (close - open) / open 是错误的
const computedChangePct = computed(() => {
  const v = stockData.value?.change_pct
  if (typeof v === 'number' && isFinite(v)) return v
  // 兑底: 仍按昨收价计计算
  const data = stockData.value?.latest
  if (data && data.close != null && data.prev_close != null) {
    return ((data.close - data.prev_close) / data.prev_close) * 100
  }
  return 0
})

function formatVal(val) {
  if (val === null || val === undefined || isNaN(val)) return '-'
  return typeof val === 'number' ? val.toFixed(2) : val
}

function getRecommendationType(recommendation) {
  if (!recommendation) return 'info'
  if (recommendation.includes('强烈建议买入')) return 'success'
  if (recommendation.includes('建议买入')) return 'success'
  if (recommendation.includes('密切关注') || recommendation.includes('谨慎')) return 'warning'
  if (recommendation.includes('注意风险') || recommendation.includes('建议卖出')) return 'danger'
  return 'info'
}

function getTimingText(signal) {
  const map = { buy: '买入时机', sell: '卖出时机', watch: '密切关注', neutral: '观望' }
  return map[signal] || '观望'
}

function getTrendText(level) {
  const map = { strong_up: '强势向上', up: '向上', neutral: '中性', down: '向下', weak: '弱势' }
  return map[level] || '中性'
}

function getTrendType(level) {
  if (level === 'strong_up' || level === 'up') return 'success'
  if (level === 'down' || level === 'weak') return 'danger'
  return 'info'
}

function getMarketText(env) {
  const map = { uptrend: '上升趋势', downtrend: '下降趋势', volatile: '震荡市' }
  return map[env] || '震荡市'
}

function getPositionText(pos) {
  const map = { high: '高位', middle: '中间位', low: '低位' }
  return map[pos] || '中间位'
}

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  chartLoading.value = true
  chartError.value = ''

  try {
    // Load stock analysis (includes price, change_pct, recommendation)
    try {
      const analyzeRes = await getStockAnalysis(code.value)
      if (analyzeRes.data.code === 0 && analyzeRes.data.data) {
        const data = analyzeRes.data.data
        stockData.value = {
          name: data.name || code.value,
          price: data.price,
          change_pct: data.change_pct,
          total_days: data.indicators ? Object.keys(data.indicators).length * 30 : 0
        }
        analysisData.value = data
        indicators.value = data.indicators
      }
    } catch (e) {
      console.warn('Stock analysis API failed:', e)
    }

    // Load stock basic info if analysis didn't provide it
    if (!stockData.value.name) {
      const stockRes = await getStock(code.value)
      if (stockRes.data.code === 0) {
        stockData.value = {
          ...stockData.value,
          name: stockRes.data.data.name || code.value,
          latest: stockRes.data.data.latest || {},
          total_days: stockRes.data.data.total_days || 0
        }
      }
    }

    // Load chart
    const indRes = await getIndicators(code.value)
    if (indRes.data.code === 0) {
      const data = indRes.data.data
      if (data.indicators && !indicators.value) {
        indicators.value = data.indicators
      }
      if (data.div && data.script) {
        renderChart(data.div, data.script)
      }
    } else {
      chartError.value = indRes.data.message || '图表加载失败'
    }
  } catch (e) {
    errorMsg.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
    chartLoading.value = false
  }
}

function renderChart(divHtml, scriptJs) {
  const container = chartRef.value
  if (!container) return

  container.innerHTML = divHtml

  if (scriptJs) {
    // 提取脚本内容
    const scriptMatch = scriptJs.match(/<script[^>]*>([\s\S]*?)<\/script>/i)
    if (scriptMatch && scriptMatch[1]) {
      try {
        const scriptContent = scriptMatch[1]
        // 使用动态script标签执行，比eval稍快
        const scriptEl = document.createElement('script')
        scriptEl.type = 'text/javascript'
        scriptEl.textContent = scriptContent
        document.body.appendChild(scriptEl)
        // 执行后移除，避免污染DOM
        document.body.removeChild(scriptEl)
      } catch (e) {
        console.error('Chart render error:', e)
        chartError.value = '图表渲染失败'
      }
    }
  }
}

function initBokeh() {
  return new Promise((resolve) => {
    if (window.Bokeh) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = '/static/js/bokeh.min.js'
    script.onload = () => resolve()
    script.onerror = () => {
      chartError.value = 'Bokeh库加载失败'
      resolve()
    }
    document.head.appendChild(script)
  })
}

onMounted(async () => {
  await initBokeh()
  loadData()
})
</script>

<style scoped>
.stock-detail {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.loading-text {
  text-align: center;
  padding: 60px;
  color: #d0d0d0;
}

.error-text {
  text-align: center;
  padding: 40px;
  color: #f56c6c;
}

.info-row {
  margin-top: 20px;
  margin-bottom: 20px;
}

.stock-name {
  font-size: 1.5rem;
  font-weight: bold;
  color: #fff;
}

.stock-code {
  color: #888;
  margin-top: 4px;
}

.label {
  color: #888;
  font-size: 0.9rem;
}

.value {
  font-size: 1.3rem;
  font-weight: bold;
  margin-top: 4px;
}

.price {
  color: #fff;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  min-height: 400px;
  background: rgba(30, 30, 50, 0.3);
  border-radius: 8px;
  padding: 10px;
}

.indicators-card {
  margin-bottom: 20px;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #888;
}

/* 分析卡片样式 */
.analysis-card {
  margin-bottom: 20px;
}

.analysis-content {
  padding: 10px 0;
}

.recommendation-desc {
  font-size: 1rem;
  color: #e0e0e0;
  margin-bottom: 20px;
  line-height: 1.6;
}

.score-box {
  text-align: center;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.score-box.buy {
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.score-box.sell {
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.score-label {
  font-size: 0.9rem;
  color: #888;
  margin-bottom: 8px;
}

.score-value {
  font-size: 2rem;
  font-weight: bold;
}

.score-box.buy .score-value {
  color: #67c23a;
}

.score-box.sell .score-value {
  color: #f56c6c;
}

.signals-section {
  margin-top: 15px;
}

.signals-title {
  font-size: 0.9rem;
  color: #888;
  margin-bottom: 10px;
}

.signal-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.quality-warning {
  margin-top: 15px;
  padding: 10px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 4px;
  color: #e6a23c;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-box {
  text-align: center;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.timing-value {
  font-size: 1.2rem;
  font-weight: bold;
  margin-top: 4px;
}

.timing-buy { color: #67c23a; }
.timing-sell { color: #f56c6c; }
.timing-watch { color: #e6a23c; }
.timing-neutral { color: #909399; }

.new-indicators-row {
  margin-top: 15px;
  padding: 15px;
  background: rgba(30, 30, 50, 0.3);
  border-radius: 8px;
}

.indicator-mini {
  text-align: center;
  padding: 10px;
}

.indicator-label {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 6px;
}

.indicator-value {
  font-size: 1.1rem;
  font-weight: bold;
  color: #fff;
  margin-bottom: 6px;
}

.position-high { color: #f56c6c; }
.position-low { color: #67c23a; }

.confidence-text {
  font-size: 0.75rem;
  color: #666;
}

.timing-desc-text {
  display: block;
  font-size: 0.75rem;
  color: #888;
  margin-top: 4px;
}
</style>
