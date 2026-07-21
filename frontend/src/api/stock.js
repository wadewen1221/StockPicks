import axios from 'axios'

const API_BASE = 'http://localhost:5001/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

// 选股结果
export function getStocks() {
  return api.get('/stocks')
}

// 股票详情
export function getStock(code) {
  return api.get(`/stock/${code}`)
}

// 技术指标
export function getIndicators(code) {
  return api.get(`/indicators/${code}`)
}

// 股票综合分析（买卖建议）
export function getStockAnalysis(code) {
  return api.get(`/analyze/${code}`)
}

// 指标配置
export function getIndicatorConfig() {
  return api.get('/indicators/config')
}

// 回测
export function runBacktest(codes, startDate, endDate) {
  return api.post('/backtest', {
    codes,
    start_date: startDate,
    end_date: endDate
  })
}

// 健康检查
export function healthCheck() {
  return api.get('/health')
}

export default api
