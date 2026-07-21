<template>
  <div class="backtest">
    <el-page-header @back="$router.push('/')" content="策略回测">
    </el-page-header>

    <el-card class="config-card">
      <template #header>回测配置</template>
      <el-form :model="config" label-width="120px">
        <el-form-item label="股票分类">
          <el-select v-model="config.category" placeholder="请选择股票分类" @change="onCategoryChange">
            <el-option label="中长线 V2" value="mid_long" />
            <el-option label="超短线激进型" value="short_aggressive" />
            <el-option label="超短线稳健型" value="short_conservative" />
            <el-option label="RSRS组合" value="rsrs_kdj_cci" />
            <el-option label="自选股票" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="股票选择" v-if="config.category !== 'custom'">
          <el-select v-model="config.selectedStock" placeholder="请选择股票" filterable>
            <el-option
              v-for="stock in stockList"
              :key="stock.code"
              :label="`${stock.code} ${stock.name}`"
              :value="stock.code"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="股票代码" v-else>
          <el-input
            v-model="config.customCodes"
            placeholder="输入股票代码，多个用逗号分隔，如: 600519,000858"
          />
        </el-form-item>

        <el-form-item label="开始日期">
          <el-date-picker v-model="config.startDate" type="date" placeholder="选择日期"
            value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="config.endDate" type="date" placeholder="选择日期"
            value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="config.initialCash" :min="10000" :step="100000" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="runBacktest" :loading="running">
            {{ running ? '回测中...' : '运行回测' }}
          </el-button>
          <el-button @click="resetConfig">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="result-card" v-if="result">
      <template #header>回测结果</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="result-item">
            <div class="result-label">最终价值</div>
            <div class="result-value">¥{{ result.final_value?.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-label">收益率</div>
            <div class="result-value" :class="result.profit_pct >= 0 ? 'up' : 'down'">
              {{ (result.profit_pct * 100).toFixed(2) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-label">SQN</div>
            <div class="result-value">{{ result.sqn?.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-label">夏普比率</div>
            <div class="result-value">{{ result.sharpe_ratio?.toFixed(2) || '-' }}</div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="result-item">
            <div class="result-label">初始资金</div>
            <div class="result-value">¥{{ result.initial_cash?.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="result-item">
            <div class="result-label">盈利</div>
            <div class="result-value" :class="result.profit >= 0 ? 'up' : 'down'">
              {{ result.profit >= 0 ? '+' : '' }}¥{{ result.profit?.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="result-item">
            <div class="result-label">最大回撤</div>
            <div class="result-value down">
              {{ result.drawdown?.max?.drawdown?.toFixed(2) || '-' }}%
            </div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <div class="trades-info">
        <h4>交易统计</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="总交易次数">
            {{ result.trades?.total?.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="盈利交易">
            {{ result.trades?.won?.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="亏损交易">
            {{ result.trades?.lost?.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="胜率">
            {{ winRate }}%
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <el-empty v-else-if="!running" description="配置参数后运行回测"></el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { runBacktest as apiBacktest, getStocks } from '../api/stock'
import { ElMessage } from 'element-plus'

const config = ref({
  category: 'mid_long',
  selectedStock: '',
  customCodes: '',
  startDate: '2024-01-01',
  endDate: new Date().toISOString().split('T')[0],
  initialCash: 1000000
})

const running = ref(false)
const result = ref(null)
const stockData = ref(null)
const stockList = ref([])

const categoryMap = {
  'mid_long': 'mid_long',
  'short_aggressive': 'short_term_aggressive',
  'short_conservative': 'short_term_conservative',
  'rsrs_kdj_cci': 'rsrs_kdj_cci',
  'custom': null
}

const categoryLabelMap = {
  'mid_long': '中长线 V2',
  'short_aggressive': '超短线激进型',
  'short_conservative': '超短线稳健型',
  'rsrs_kdj_cci': 'RSRS组合',
  'custom': '自选股票'
}

async function loadStockData() {
  try {
    const res = await getStocks()
    if (res.data.code === 0) {
      stockData.value = res.data.data
      updateStockList()
    }
  } catch (e) {
    console.warn('Failed to load stock data:', e)
  }
}

function updateStockList() {
  const category = categoryMap[config.value.category]
  if (!category || !stockData.value) {
    stockList.value = []
    return
  }

  const stocks = stockData.value[category] || []
  stockList.value = stocks.map(s => ({
    code: s.code,
    name: s.name,
    score: s.score,
    buy_score: s.buy_score,
    sell_score: s.sell_score
  }))

  // Clear selection if current selection not in new list
  if (config.value.selectedStock) {
    const exists = stockList.value.some(s => s.code === config.value.selectedStock)
    if (!exists) {
      config.value.selectedStock = ''
    }
  }
}

function onCategoryChange() {
  updateStockList()
  config.value.selectedStock = ''
  config.value.customCodes = ''
}

const winRate = computed(() => {
  if (!result.value?.trades) return 0
  const total = result.value.trades.won?.total || 0
  const lost = result.value.trades.lost?.total || 0
  const all = total + lost
  return all > 0 ? (total / all * 100).toFixed(2) : 0
})

async function runBacktest() {
  let codes = []

  if (config.value.category === 'custom') {
    // 自选股票：从输入框获取
    if (!config.value.customCodes) {
      ElMessage.warning('请输入股票代码')
      return
    }
    codes = config.value.customCodes.split(',').map(c => c.trim()).filter(c => c)
  } else {
    // 从选股列表选择
    if (!config.value.selectedStock) {
      ElMessage.warning('请选择股票')
      return
    }
    codes = [config.value.selectedStock]
  }

  if (codes.length === 0) {
    ElMessage.warning('请至少选择一只股票')
    return
  }

  running.value = true
  result.value = null

  try {
    const res = await apiBacktest(codes, config.value.startDate, config.value.endDate)

    if (res.data.code === 0) {
      result.value = res.data.data
      ElMessage.success('回测完成')
    } else {
      ElMessage.error(res.data.message || '回测失败')
    }
  } catch (e) {
    ElMessage.error('回测失败: ' + e.message)
  } finally {
    running.value = false
  }
}

function resetConfig() {
  config.value = {
    category: 'mid_long',
    selectedStock: '',
    customCodes: '',
    startDate: '2024-01-01',
    endDate: new Date().toISOString().split('T')[0],
    initialCash: 1000000
  }
  result.value = null
  updateStockList()
}

onMounted(() => {
  loadStockData()
})
</script>

<style scoped>
.backtest {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.config-card {
  margin-top: 20px;
}

.result-card {
  margin-top: 20px;
}

.result-item {
  text-align: center;
  padding: 16px;
}

.result-label {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.result-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #fff;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}

.trades-info {
  margin-top: 20px;
}

.trades-info h4 {
  margin-bottom: 12px;
  color: #fff;
}

:deep(.el-select) {
  width: 100%;
}
</style>
