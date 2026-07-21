<template>
  <div class="stock-list">
    <el-page-header @back="$router.push('/')" content="选股结果">
      <template #extra>
        <el-button type="primary" @click="loadStocks" :loading="loading">刷新</el-button>
      </template>
    </el-page-header>

    <el-tabs v-model="activeTab" class="stock-tabs">
      <el-tab-pane label="中长线" name="mid_long">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="!midLongStocks.length" class="empty">暂无数据</div>
        <el-table v-else :data="midLongStocks" stripe style="width: 100%" @row-click="viewDetail">
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="industry" label="行业" width="120" />
          <el-table-column prop="score" label="综合评分" width="100">
            <template #default="scope">
              <el-tag type="success">{{ scope.row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="现价" width="100" />
          <el-table-column prop="change_pct" label="涨跌幅" width="100">
            <template #default="scope">
              <span :class="scope.row.change_pct >= 0 ? 'up' : 'down'">
                {{ scope.row.change_pct >= 0 ? '+' : '' }}{{ scope.row.change_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="回测结果">
            <template #default="scope">
              <template v-if="scope.row.backtest">
                <span>收益: {{ (scope.row.backtest.profit_pct * 100).toFixed(2) }}%</span>
                <el-tag size="small" type="info" style="margin-left: 8px">
                  SQN: {{ scope.row.backtest.sqn?.toFixed(2) }}
                </el-tag>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="primary" @click.stop="viewDetail(scope.row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="超短线激进型" name="short_term_aggressive">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="!shortTermAggressiveStocks.length" class="empty">暂无数据</div>
        <el-table v-else :data="shortTermAggressiveStocks" stripe style="width: 100%" @row-click="viewDetail">
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="score" label="综合评分" width="100">
            <template #default="scope">
              <el-tag type="danger">{{ scope.row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="现价" width="100" />
          <el-table-column prop="change_pct" label="涨跌幅" width="100">
            <template #default="scope">
              <span :class="scope.row.change_pct >= 0 ? 'up' : 'down'">
                {{ scope.row.change_pct >= 0 ? '+' : '' }}{{ scope.row.change_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="回测结果">
            <template #default="scope">
              <template v-if="scope.row.backtest">
                <span>收益: {{ (scope.row.backtest.profit_pct * 100).toFixed(2) }}%</span>
                <el-tag size="small" type="info" style="margin-left: 8px">
                  SQN: {{ scope.row.backtest.sqn?.toFixed(2) }}
                </el-tag>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="primary" @click.stop="viewDetail(scope.row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="超短线稳健型" name="short_term_conservative">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="!shortTermConservativeStocks.length" class="empty">暂无数据</div>
        <el-table v-else :data="shortTermConservativeStocks" stripe style="width: 100%" @row-click="viewDetail">
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="score" label="综合评分" width="100">
            <template #default="scope">
              <el-tag type="warning">{{ scope.row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="现价" width="100" />
          <el-table-column prop="change_pct" label="涨跌幅" width="100">
            <template #default="scope">
              <span :class="scope.row.change_pct >= 0 ? 'up' : 'down'">
                {{ scope.row.change_pct >= 0 ? '+' : '' }}{{ scope.row.change_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="回测结果">
            <template #default="scope">
              <template v-if="scope.row.backtest">
                <span>收益: {{ (scope.row.backtest.profit_pct * 100).toFixed(2) }}%</span>
                <el-tag size="small" type="info" style="margin-left: 8px">
                  SQN: {{ scope.row.backtest.sqn?.toFixed(2) }}
                </el-tag>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="primary" @click.stop="viewDetail(scope.row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="RSRS组合" name="rsrs_kdj_cci">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="!rsrsKdjCciStocks.length" class="empty">暂无数据</div>
        <el-table v-else :data="rsrsKdjCciStocks" stripe style="width: 100%" @row-click="viewDetail">
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="buy_score" label="买入评分" width="100">
            <template #default="scope">
              <el-tag type="success">{{ scope.row.buy_score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sell_score" label="卖出评分" width="100">
            <template #default="scope">
              <el-tag type="danger">{{ scope.row.sell_score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="现价" width="100" />
          <el-table-column prop="change_pct" label="涨跌幅" width="100">
            <template #default="scope">
              <span :class="scope.row.change_pct >= 0 ? 'up' : 'down'">
                {{ scope.row.change_pct >= 0 ? '+' : '' }}{{ scope.row.change_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="primary" @click.stop="viewDetail(scope.row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStocks } from '../api/stock'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const activeTab = ref('mid_long')
const midLongStocks = ref([])
const shortTermAggressiveStocks = ref([])
const shortTermConservativeStocks = ref([])
const rsrsKdjCciStocks = ref([])

async function loadStocks() {
  loading.value = true
  try {
    const res = await getStocks()
    if (res.data.code === 0) {
      const data = res.data.data
      midLongStocks.value = data.mid_long || []
      shortTermAggressiveStocks.value = data.short_term_aggressive || []
      shortTermConservativeStocks.value = data.short_term_conservative || []
      rsrsKdjCciStocks.value = data.rsrs_kdj_cci || []
    } else {
      ElMessage.error(res.data.message || '获取选股结果失败')
    }
  } catch (e) {
    ElMessage.error('获取选股结果失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function viewDetail(row) {
  router.push(`/stock/${row.code}`)
}

onMounted(() => {
  loadStocks()
})
</script>

<style scoped>
.stock-list {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.stock-tabs {
  margin-top: 20px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #d0d0d0;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}

/* Fix el-tag colors in table */
:deep(.el-tag) {
  background-color: rgba(255, 255, 255, 0.15) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
}

:deep(.el-tag--success) {
  background-color: rgba(103, 194, 58, 0.2) !important;
  border-color: rgba(103, 194, 58, 0.4) !important;
  color: #90ee90 !important;
}

:deep(.el-tag--warning) {
  background-color: rgba(230, 162, 60, 0.2) !important;
  border-color: rgba(230, 162, 60, 0.4) !important;
  color: #ffd700 !important;
}

:deep(.el-tag--danger) {
  background-color: rgba(245, 108, 108, 0.2) !important;
  border-color: rgba(245, 108, 108, 0.4) !important;
  color: #ff6b6b !important;
}

:deep(.el-tag--info) {
  background-color: rgba(144, 147, 153, 0.2) !important;
  border-color: rgba(144, 147, 153, 0.4) !important;
  color: #d0d0d0 !important;
}
</style>
