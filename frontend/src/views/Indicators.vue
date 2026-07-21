<template>
  <div class="indicators">
    <el-page-header @back="$router.push('/')" content="K线与指标图表">
    </el-page-header>

    <div class="chart-controls">
      <el-form :inline="true">
        <el-form-item label="股票选择">
          <el-select v-model="stockCode" placeholder="请选择股票" filterable style="width: 240px">
            <el-option
              v-for="stock in stockList"
              :key="stock.code"
              :label="`${stock.code} ${stock.name}`"
              :value="stock.code"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadChart">加载图表</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="loading" class="loading-text">图表加载中，请稍候...</div>
    <div v-else-if="errorMsg" class="error-text">{{ errorMsg }}</div>
    <div v-else class="chart-wrapper">
      <div ref="chartRef" class="chart-container"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { getIndicators, getStocks } from '../api/stock'
import { ElMessage } from 'element-plus'

const stockCode = ref('')
const loading = ref(false)
const errorMsg = ref('')
const chartRef = ref(null)
const bokehReady = ref(false)
const stockList = ref([])

async function loadStockData() {
  try {
    const res = await getStocks()
    if (res.data.code === 0) {
      const allStocks = []
      const data = res.data.data
      for (const category in data) {
        if (Array.isArray(data[category])) {
          allStocks.push(...data[category])
        }
      }
      const uniqueMap = new Map()
      allStocks.forEach(s => {
        if (!uniqueMap.has(s.code)) {
          uniqueMap.set(s.code, { code: s.code, name: s.name })
        }
      })
      stockList.value = Array.from(uniqueMap.values())
    }
  } catch (e) {
    console.warn('Failed to load stock list:', e)
  }
}

async function loadChart() {
  if (!stockCode.value) {
    ElMessage.warning('请输入股票代码')
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    // Wait for Bokeh to be ready
    if (!bokehReady.value) {
      await waitForBokeh()
    }

    const res = await getIndicators(stockCode.value)
    if (res.data.code === 0 && res.data.data) {
      const data = res.data.data
      if (data.div && data.script) {
        await nextTick()
        renderBokehChart(data.div, data.script)
      } else {
        errorMsg.value = '图表数据格式错误'
      }
    } else {
      errorMsg.value = res.data.message || '加载失败'
    }
  } catch (e) {
    errorMsg.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

function renderBokehChart(divHtml, scriptJs) {
  const container = chartRef.value
  if (!container) {
    console.error('Chart container not found')
    return
  }

  // Clear previous chart
  container.innerHTML = ''

  // Insert the div HTML
  container.innerHTML = divHtml

  // Execute script
  if (scriptJs) {
    try {
      // Extract script content - remove script tags if present
      let scriptContent = scriptJs.trim()
      const scriptMatch = scriptContent.match(/<script[^>]*>([\s\S]*?)<\/script>/i)
      if (scriptMatch && scriptMatch[1]) {
        scriptContent = scriptMatch[1].trim()
      }

      if (scriptContent) {
        // Execute using Function constructor (safer than eval)
        const fn = new Function(scriptContent)
        fn()
      }
    } catch (e) {
      console.error('Bokeh render error:', e)
      errorMsg.value = '图表渲染失败: ' + e.message
    }
  }
}

function waitForBokeh() {
  return new Promise((resolve) => {
    // Bokeh already loaded
    if (window.Bokeh && window.Bokeh.embed) {
      bokehReady.value = true
      resolve()
      return
    }

    // Check if script is already being loaded
    const existingScript = document.querySelector('script[src*="bokeh"]')
    if (existingScript) {
      existingScript.onload = () => {
        bokehReady.value = true
        resolve()
      }
      return
    }

    // Load Bokeh
    const script = document.createElement('script')
    script.src = '/static/js/bokeh.min.js'
    script.onload = () => {
      bokehReady.value = true
      resolve()
    }
    script.onerror = () => {
      errorMsg.value = 'Bokeh库加载失败，请检查网络连接'
      resolve() // Don't block, but indicate not ready
    }
    document.head.appendChild(script)
  })
}

onMounted(() => {
  // Wait for Bokeh to be ready, but don't auto-load chart
  waitForBokeh()
  loadStockData()
})
</script>

<style scoped>
.indicators {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.chart-controls {
  margin: 20px 0;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.loading-text {
  text-align: center;
  padding: 60px 20px;
  color: #d0d0d0;
  font-size: 16px;
}

.error-text {
  text-align: center;
  padding: 40px 20px;
  color: #f56c6c;
  font-size: 16px;
}

.chart-wrapper {
  background: rgba(30, 30, 50, 0.3);
  border-radius: 8px;
  padding: 10px;
}

.chart-container {
  min-height: 500px;
}
</style>
