<template>
  <div class="indicators-detail">
    <el-page-header @back="$router.push('/')" content="技术指标详解">
    </el-page-header>

    <div class="intro">
      <p>技术指标是通过数学计算对股票价格、成交量等历史数据进行处理得出的量化指标，用于辅助投资者判断市场趋势、超买超卖状态和买卖时机。本系统整合了17种常用技术指标，以下是各指标的详细说明。</p>
    </div>

    <!-- 指标选择按钮 -->
    <div class="indicator-buttons">
      <el-button
        v-for="ind in indicators"
        :key="ind.id"
        :type="selectedId === ind.id ? 'primary' : 'default'"
        @click="selectIndicator(ind.id)"
        class="indicator-btn"
      >
        {{ ind.title }}
      </el-button>
    </div>

    <!-- 指标详细信息 -->
    <div v-if="selected" class="indicator-detail">
      <el-card class="detail-card">
        <template #header>
          <div class="detail-header">
            <span class="detail-icon">{{ getIcon(selected.id) }}</span>
            <span class="detail-title">{{ selected.title }}</span>
          </div>
        </template>

        <div class="detail-section">
          <h3>指标简介</h3>
          <p>{{ selected.desc }}</p>
        </div>

        <div class="detail-section">
          <h3>计算原理</h3>
          <p>{{ selected.calculation }}</p>
        </div>

        <div class="detail-section">
          <h3>参数说明</h3>
          <ul>
            <li v-for="param in selected.params" :key="param.name">
              <strong>{{ param.name }}</strong>: {{ param.desc }}
            </li>
          </ul>
        </div>

        <div class="detail-section">
          <h3>判定标准</h3>
          <div class="criteria-list">
            <div v-for="criteria in selected.criteria" :key="criteria.label" class="criteria-item">
              <span class="criteria-label">{{ criteria.label }}</span>
              <span class="criteria-value">{{ criteria.value }}</span>
              <span class="criteria-desc">{{ criteria.desc }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>交易信号</h3>
          <div class="signals">
            <div class="signal buy">
              <span class="signal-icon">📈</span>
              <span class="signal-title">买入信号</span>
              <p>{{ selected.signals.buy }}</p>
            </div>
            <div class="signal sell">
              <span class="signal-icon">📉</span>
              <span class="signal-title">卖出信号</span>
              <p>{{ selected.signals.sell }}</p>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>应用场景</h3>
          <p>{{ selected.application }}</p>
        </div>

        <div class="detail-section">
          <h3>注意事项</h3>
          <ul class="warnings">
            <li v-for="warn in selected.warnings" :key="warn">{{ warn }}</li>
          </ul>
        </div>
      </el-card>
    </div>

    <!-- 全部指标概览 -->
    <div v-else class="all-indicators">
      <h2>17种技术指标一览</h2>
      <el-row :gutter="20">
        <el-col :span="12" v-for="ind in indicators" :key="ind.id" class="indicator-item">
          <el-card shadow="hover" @click="selectIndicator(ind.id)" class="clickable">
            <template #header>
              <div class="indicator-header">
                <span class="indicator-icon">{{ getIcon(ind.id) }}</span>
                <span class="indicator-title">{{ ind.title }}</span>
              </div>
            </template>
            <p class="indicator-brief">{{ ind.desc }}</p>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const selectedId = ref(null)

const indicators = ref([
  {
    id: 'kdj',
    title: 'KDJ指标',
    desc: '随机指标(KDJ)由K线、D线、J线三条曲线组成，通过特定周期内的最高价、最低价和收盘价计算得出，用于判断市场的超买超卖状态。',
    calculation: 'RSV = (收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) × 100\nK = 2/3 × 前一日K值 + 1/3 × RSV\nD = 2/3 × 前一日D值 + 1/3 × K\nJ = 3K - 2D\n其中N通常取9日。',
    params: [
      { name: 'N', desc: '计算周期，通常为9日' },
      { name: 'M1', desc: 'K值平滑因子，通常为3' },
      { name: 'M2', desc: 'D值平滑因子，通常为3' }
    ],
    criteria: [
      { label: 'K,D值', value: '< 20', desc: '超卖区域' },
      { label: 'K,D值', value: '> 80', desc: '超买区域' },
      { label: 'J值', value: '< 0', desc: '严重超卖' },
      { label: 'J值', value: '> 100', desc: '严重超买' }
    ],
    signals: {
      buy: 'K线从下向上穿越D线，且K、D值均小于20时，形成金叉，为买入信号。J值小于0时也可能表示超卖反弹机会。',
      sell: 'K线从上向下穿越D线，且K、D值均大于80时，形成死叉，为卖出信号。J值大于100时可能表示超买回调风险。'
    },
    application: 'KDJ指标适用于短线交易，特别适合震荡市。在单边上涨或下跌行情中可能会出现钝化现象。结合作量能和其他指标使用效果更佳。',
    warnings: [
      '在强势单边行情中，KDJ可能持续高位或低位钝化',
      'J值波动较大，有时会提前发出信号，需结合K、D值判断',
      '短期交易信号较多，需配合其他指标过滤假信号'
    ]
  },
  {
    id: 'macd',
    title: 'MACD指标',
    desc: '平滑异同移动平均线(MACD)由快线(DIF)、慢线(DEA)和柱状图(MACD柱)组成，用于判断价格趋势的方向和动量变化。',
    calculation: 'EMA12 = 12日指数移动平均\nEMA26 = 26日指数移动平均\nDIF = EMA12 - EMA26\nDEA = DIF的9日指数移动平均\nMACD柱 = 2 × (DIF - DEA)',
    params: [
      { name: '快线周期', desc: '通常为12日' },
      { name: '慢线周期', desc: '通常为26日' },
      { name: '信号线周期', desc: '通常为9日' }
    ],
    criteria: [
      { label: 'DIF', value: '> 0', desc: '多头趋势' },
      { label: 'DIF', value: '< 0', desc: '空头趋势' },
      { label: 'MACD柱', value: '> 0（红色）', desc: '多头动能增强' },
      { label: 'MACD柱', value: '< 0（绿色）', desc: '空头动能增强' }
    ],
    signals: {
      buy: 'DIF线上穿DEA线（金叉）且在零轴上方时买入；MACD柱由负转正时也是买入信号。',
      sell: 'DIF线下穿DEA线（死叉）且在零轴下方时卖出；MACD柱由正转负时也是卖出信号。'
    },
    application: 'MACD适合中线趋势判断，在单边行情中表现较好。可用于判断趋势起始、回调结束和趋势反转。',
    warnings: [
      'MACD是滞后指标，信号可能会有所延迟',
      '在震荡行情中频繁交叉可能产生假信号',
      '建议结合零轴位置和柱状图变化综合判断'
    ]
  },
  {
    id: 'boll',
    title: '布林带指标',
    desc: '布林线(BOLL)由中轨(MA20)和上下两条轨道线组成，价格在上下轨之间波动。用于判断价格通道、超买超卖和趋势转折。',
    calculation: '中轨 = MA(N日收盘价)，通常N=20\n上轨 = 中轨 + 2 × 标准差\n下轨 = 中轨 - 2 × 标准差',
    params: [
      { name: 'N', desc: '中轨计算周期，通常为20日' },
      { name: 'K', desc: '标准差倍数，通常为2' }
    ],
    criteria: [
      { label: '价格触及', value: '下轨', desc: '可能超卖，支撑位' },
      { label: '价格触及', value: '上轨', desc: '可能超买，压力位' },
      { label: '布林带', value: '收窄', desc: '波动率降低，可能突破' },
      { label: '布林带', value: '发散', desc: '波动率增大，趋势加速' }
    ],
    signals: {
      buy: '价格从下轨附近向上穿越中轨，或价格站稳中轨后回踩中轨获得支撑时买入。',
      sell: '价格从上轨附近向下穿越中轨，或价格跌破中轨后反弹受阻时卖出。'
    },
    application: '布林带适用于趋势确认和盘整突破判断。在横盘整理时上下轨收窄后突然发散通常意味着行情启动。',
    warnings: [
      '布林带是波动率指标，不是方向指标',
      '极端行情中价格可能持续沿着上轨或下轨运行',
      '单靠布林带不足以判断趋势，需要结合其他指标'
    ]
  },
  {
    id: 'rsi',
    title: 'RSI指标',
    desc: '相对强弱指数(RSI)通过计算一定周期内价格上涨和下跌幅度的比例，来判断市场的超买超卖状态。取值范围0-100。',
    calculation: 'RS = N日内上涨幅度平均值 / N日内下跌幅度平均值\nRSI = 100 - 100 / (1 + RS)\n通常N取6日或14日',
    params: [
      { name: 'N', desc: '计算周期，短线常用6日，中线用14日' }
    ],
    criteria: [
      { label: 'RSI', value: '< 30', desc: '超卖区域，可能反弹' },
      { label: 'RSI', value: '> 70', desc: '超买区域，可能回调' },
      { label: 'RSI', value: '< 20', desc: '严重超卖' },
      { label: 'RSI', value: '> 80', desc: '严重超买' }
    ],
    signals: {
      buy: 'RSI从超卖区域（30以下）向上反弹时买入；RSI与价格形成底部背离时也是买入信号。',
      sell: 'RSI从超买区域（70以上）向下回落时卖出；RSI与价格形成顶部背离时也是卖出信号。'
    },
    application: 'RSI适用于判断市场的超买超卖，在震荡市中表现较好。特别适合短线交易和反转信号判断。',
    warnings: [
      '在强势趋势中RSI可能长时间维持在超买/超卖区域',
      '不同周期的RSI需要结合使用',
      '背离信号可能滞后，需要其他指标确认'
    ]
  },
  {
    id: 'cci',
    title: 'CCI指标',
    desc: '顺势指标(CCI)衡量价格相对于其统计平均值的偏离程度，用于判断价格的极端波动和趋势强度。',
    calculation: 'TP = (最高价 + 最低价 + 收盘价) / 3\nCCI = (TP - MA) / (0.015 × MD)\n其中MA为TP的N日简单移动平均，MD为平均偏差',
    params: [
      { name: 'N', desc: '计算周期，通常为14日' }
    ],
    criteria: [
      { label: 'CCI', value: '> +100', desc: '多头强势，可能继续上涨' },
      { label: 'CCI', value: '< -100', desc: '空头强势，可能继续下跌' },
      { label: 'CCI', value: '从下向上穿越', desc: '+100买入信号' },
      { label: 'CCI', value: '从上向下穿越', desc: '-100卖出信号' }
    ],
    signals: {
      buy: 'CCI从-100以下向上穿越该线时买入；CCI在+100以上回调后再次上攻也是买入信号。',
      sell: 'CCI从+100以上向下穿越该线时卖出；CCI在-100以下反弹后再次下跌也是卖出信号。'
    },
    application: 'CCI特别适合趋势行情，在单边上涨或下跌行情中表现优异。波动较大的股票效果更明显。',
    warnings: [
      'CCI是无界的，数值可以超出±100范围很多',
      '参数设置不同会影响效果',
      '在横盘震荡时信号可能频繁'
    ]
  },
  {
    id: 'wr',
    title: '威廉指标',
    desc: '威廉指数(WR)通过分析一段时间内价格区间的相对位置来判断超买超卖，取值范围0-100。',
    calculation: 'WR(N) = (Hn - C) / (Hn - Ln) × 100\n其中：H为N日内最高价，L为N日内最低价，C为当日收盘价',
    params: [
      { name: 'N', desc: '计算周期，常用6日、10日' }
    ],
    criteria: [
      { label: 'WR', value: '> 80', desc: '超卖区域，低位反弹机会' },
      { label: 'WR', value: '< 20', desc: '超买区域，高位回落风险' },
      { label: 'WR', value: '触及0', desc: '价格处于周期内最高点' },
      { label: 'WR', value: '触及100', desc: '价格处于周期内最低点' }
    ],
    signals: {
      buy: 'WR从超卖区域（80以上）向下突破50轴线时买入；WR两次触及100后向上突破80时也是买入信号。',
      sell: 'WR从超买区域（20以下）向上突破50轴线时卖出；WR两次触及0后向下突破20时也是卖出信号。'
    },
    application: '威廉指标适合短线交易，特别适合在震荡行情中寻找买卖点。与RSI配合使用效果更好。',
    warnings: [
      'WR波动较为剧烈，信号较多',
      '需要设置合适的周期参数',
      '单边行情中可能持续高位或低位'
    ]
  },
  {
    id: 'atr',
    title: 'ATR指标',
    desc: '均幅指标(ATR)用于衡量市场波动性，是真实波动的移动平均值。ATR值越大表示波动越剧烈。',
    calculation: 'TR = max(当日最高价-当日最低价, |当日最高价-前一日收盘价|, |当日最低价-前一日收盘价|)\nATR = TR的N日移动平均，通常N=14',
    params: [
      { name: 'N', desc: '计算周期，通常为14日' }
    ],
    criteria: [
      { label: 'ATR', value: '逐步上升', desc: '波动加大，趋势可能加速' },
      { label: 'ATR', value: '逐步下降', desc: '波动减小，趋势可能减缓' },
      { label: 'ATR', value: '处于高位', desc: '市场波动剧烈' },
      { label: 'ATR', value: '处于低位', desc: '市场相对平静' }
    ],
    signals: {
      buy: 'ATR本身不产生买卖信号，但ATR突然放大往往预示趋势行情来临，可结合其他指标顺势买入。',
      sell: 'ATR持续下降可能预示盘整结束，此时不宜做空，应等待趋势明确。'
    },
    application: 'ATR主要用于设置止损位和判断市场波动性。交易者可以根据ATR来确定合理的止损幅度。',
    warnings: [
      'ATR是波动率指标，不提供方向信号',
      '不同股票的ATR值差异较大，不宜直接比较',
      '应结合其他趋势指标使用'
    ]
  },
  {
    id: 'trix',
    title: 'TRIX指标',
    desc: '三重指数平滑移动平均线(TRIX)对价格进行三次指数平滑处理，消除噪音干扰，用于判断趋势方向。',
    calculation: 'EMA1 = 收盘价的N日指数移动平均\nEMA2 = EMA1的N日指数移动平均\nEMA3 = EMA2的N日指数移动平均\nTRIX = (EMA3 - 前一日EMA3) / 前一日EMA3 × 100\nTRMA = TRIX的M日移动平均',
    params: [
      { name: 'N', desc: '指数平滑周期，通常为12日' },
      { name: 'M', desc: '信号线周期，通常为9日' }
    ],
    criteria: [
      { label: 'TRIX', value: '> 0', desc: '多头趋势' },
      { label: 'TRIX', value: '< 0', desc: '空头趋势' },
      { label: 'TRIX', value: '向上穿越TRMA', desc: '买入信号' },
      { label: 'TRIX', value: '向下穿越TRMA', desc: '卖出信号' }
    ],
    signals: {
      buy: 'TRIX在零轴上方且向上穿越TRMA时买入；TRIX与价格形成底背离时也是买入信号。',
      sell: 'TRIX向下穿越TRMA时卖出；TRIX在零轴下方时操作应谨慎。'
    },
    application: 'TRIX适合中长线趋势判断，过滤短期噪音。在趋势行情中表现较好。',
    warnings: [
      'TRIX反应较慢，不适合短线交易',
      '在横盘震荡时信号较少且可能失效',
      '建议与动量指标配合使用'
    ]
  },
  {
    id: 'dma',
    title: 'DMA指标',
    desc: '平行线差指标(DMA)通过计算两条不同周期的移动平均线的差值来判断短期趋势。',
    calculation: 'DMA = 短期MA - 长期MA\nAMA = DMA的M日移动平均\n常用参数：短期MA=10日，长期MA=50日，M=10',
    params: [
      { name: '短期MA', desc: '通常为10日' },
      { name: '长期MA', desc: '通常为50日' },
      { name: 'M', desc: '差值平滑周期' }
    ],
    criteria: [
      { label: 'DMA', value: '> 0', desc: '短期均线在长期均线上方，多头' },
      { label: 'DMA', value: '< 0', desc: '短期均线在长期均线下方，空头' },
      { label: 'DMA', value: '向上穿越AMA', desc: '买入信号' },
      { label: 'DMA', value: '向下穿越AMA', desc: '卖出信号' }
    ],
    signals: {
      buy: 'DMA从下向上穿越AMA时买入；DMA与价格底背离时也是买入信号。',
      sell: 'DMA从上向下穿越AMA时卖出；DMA与价格顶背离时也是卖出信号。'
    },
    application: 'DMA适合判断短期趋势，可用于捕捉中期行情。在趋势明确时效果较好。',
    warnings: [
      'DMA是趋势跟随指标，在震荡市中可能来回穿梭',
      '参数设置影响信号频率',
      '建议与超买超卖指标配合'
    ]
  },
  {
    id: 'dmi',
    title: 'DMI指标',
    desc: '动向指数(DMI)包含+DI和-DI两条线，用于判断趋势方向，同时包含ADX判断趋势强度。',
    calculation: '+DI = 上升动向 / 真实波幅 × 100\n-DI = 下降动向 / 真实波幅 × 100\nADX = +DI与-DI差值的N日指数平均\n通常N=14',
    params: [
      { name: 'N', desc: '计算周期，通常为14日' }
    ],
    criteria: [
      { label: '+DI', value: '上穿-DI', desc: '买入信号，趋势向上' },
      { label: '-DI', value: '上穿+DI', desc: '卖出信号，趋势向下' },
      { label: 'ADX', value: '> 25', desc: '趋势明显' },
      { label: 'ADX', value: '< 20', desc: '趋势不明，震荡市' }
    ],
    signals: {
      buy: '+DI向上穿越-DI且ADX处于上升趋势时买入；ADX上升表示趋势正在加强。',
      sell: '-DI向上穿越+DI时卖出；ADX下降表示当前趋势正在减弱。'
    },
    application: 'DMI特别适合判断趋势是否成立和趋势强度。在有明显趋势的行情中表现优异。',
    warnings: [
      '在横盘震荡时ADX可能持续走低',
      'DMI信号产生可能滞后',
      '+DI和-DI频繁交叉表示市场无趋势'
    ]
  },
  {
    id: 'adxr',
    title: 'ADXR指标',
    desc: '平均趋向指数的平滑版本(ADXR)，是ADX的平滑平均，用于判断趋势强度。',
    calculation: 'ADXR = (当日ADX + N日前ADX) / 2\n通常N=14，即ADXR是ADX的10日平均',
    params: [
      { name: 'N', desc: 'ADX计算周期' },
      { name: 'M', desc: 'ADXR平滑周期' }
    ],
    criteria: [
      { label: 'ADXR', value: '> 25', desc: '趋势明显且持续' },
      { label: 'ADXR', value: '< 20', desc: '趋势较弱或无趋势' },
      { label: 'ADXR上升', value: '与ADX配合', desc: '趋势正在加强' },
      { label: 'ADXR下降', value: '与ADX配合', desc: '趋势正在减弱' }
    ],
    signals: {
      buy: 'ADXR与ADX同时上升，且+DI在-DI上方时买入。',
      sell: 'ADXR与ADX同时下降，或-DI上穿+DI时卖出。'
    },
    application: 'ADXR适合与DMI配合使用，用于确认趋势的可靠性。在中期趋势判断中效果较好。',
    warnings: [
      'ADXR是趋势强度指标，不提供方向信号',
      '需要结合+DI和-DI判断方向',
      '在震荡行情中信号可靠性下降'
    ]
  },
  {
    id: 'vr',
    title: 'VR指标',
    desc: '成交量变异率(VR)通过分析成交量增减比例来判断市场的量能变化，用于验证价格走势的可靠性。',
    calculation: 'VR = (N日内上涨日成交量之和 + N/2日内平盘日成交量之和) / (N日内下跌日成交量之和 + N/2日内平盘日成交量之和) × 100\n通常N=26',
    params: [
      { name: 'N', desc: '计算周期，通常为26日' }
    ],
    criteria: [
      { label: 'VR', value: '< 40', desc: '超卖区域，可能反弹' },
      { label: 'VR', value: '> 250', desc: '超买区域，可能回调' },
      { label: 'VR', value: '40-250', desc: '正常波动范围' },
      { label: 'VR上升', value: '配合价格上涨', desc: '量价配合，上涨可靠' }
    ],
    signals: {
      buy: 'VR从低位的40以下向上攀升，且价格开始反弹时买入；VR与价格底背离时也是买入信号。',
      sell: 'VR从高位250以上回落，且价格开始下跌时卖出。'
    },
    application: 'VR主要用于验证量价配合关系。在判断顶部和底部时特别有效。',
    warnings: [
      '不同市场的VR参考值可能有差异',
      'VR应与价格走势配合使用',
      '单靠VR不足以判断买卖点'
    ]
  },
  {
    id: 'ppo',
    title: 'PPO指标',
    desc: '价格动量振荡器(PPO)是MACD的变体，以百分比形式显示两条移动平均线的差值，便于不同股票间的比较。',
    calculation: 'EMA12 = 12日指数移动平均\nEMA26 = 26日指数移动平均\nPPO = (EMA12 - EMA26) / EMA26 × 100\nPPO信号线 = PPO的9日指数移动平均\nPPO柱 = PPO - PPO信号线',
    params: [
      { name: '快线周期', desc: '通常为12日' },
      { name: '慢线周期', desc: '通常为26日' },
      { name: '信号线周期', desc: '通常为9日' }
    ],
    criteria: [
      { label: 'PPO', value: '> 0', desc: '多头趋势' },
      { label: 'PPO', value: '< 0', desc: '空头趋势' },
      { label: 'PPO', value: '上穿信号线', desc: '买入信号' },
      { label: 'PPO', value: '下穿信号线', desc: '卖出信号' }
    ],
    signals: {
      buy: 'PPO从下向上穿越信号线且在零轴上方时买入；零轴上方金叉信号更强。',
      sell: 'PPO从上向下穿越信号线且在零轴下方时卖出。'
    },
    application: 'PPO与MACD使用方法相似，但以百分比计算便于比较不同价格的股票。',
    warnings: [
      'PPO是MACD的变体，信号特性类似',
      '在横盘震荡时可能频繁交叉',
      '参数设置影响信号频率'
    ]
  },
  {
    id: 'cr',
    title: 'CR指标',
    desc: '能量潮指标(CR)通过将中间价与最高价、最低价的关系来衡量市场能量，用于判断资金流向。',
    calculation: 'CR = N日内 (最高价 - 中间价)之和 / N日内 (中间价 - 最低价)之和 × 100\n中间价 = (最高价 + 最低价 + 收盘价) / 3\nCR通常计算4条辅助线：CR的5、10、20、60日均线',
    params: [
      { name: 'N', desc: '计算周期，通常为26日' }
    ],
    criteria: [
      { label: 'CR', value: '> 300', desc: '能量过强，可能调整' },
      { label: 'CR', value: '< 40', desc: '能量不足，可能反弹' },
      { label: 'CR上穿', value: '辅助均线', desc: '买入信号' },
      { label: 'CR下穿', value: '辅助均线', desc: '卖出信号' }
    ],
    signals: {
      buy: 'CR由低位向上突破四条辅助均线时买入；CR在均线之上回踩均线获得支撑时买入。',
      sell: 'CR由高位向下突破四条辅助均线时卖出。'
    },
    application: 'CR指标特别关注均线系统的配合。在判断资金进出和主力动向方面有一定参考价值。',
    warnings: [
      'CR计算相对复杂，信号可能滞后',
      '参数设置影响辅助线数量和位置',
      '需要与价格走势配合判断'
    ]
  },
  {
    id: 'mfi',
    title: 'MFI指标',
    desc: '资金流量指标(MFI)将成交量和价格结合，是RSI的成交量版本，用于判断资金流入流出的强度。',
    calculation: 'TP = (最高价 + 最低价 + 收盘价) / 3\nMF = TP × 当日成交量\n正资金流量 = 今日TP > 昨日TP的各日MF之和\n负资金流量 = 今日TP < 昨日TP的各日MF之和\nMFI = 100 - 100 / (1 + MR)\n其中MR = 正资金流量 / 负资金流量，通常周期N=14',
    params: [
      { name: 'N', desc: '计算周期，通常为14日' }
    ],
    criteria: [
      { label: 'MFI', value: '> 80', desc: '超买区域，资金流入过多' },
      { label: 'MFI', value: '< 20', desc: '超卖区域，资金流出过多' },
      { label: 'MFI与价格', value: '顶背离', desc: '卖出信号' },
      { label: 'MFI与价格', value: '底背离', desc: '买入信号' }
    ],
    signals: {
      buy: 'MFI从超卖区域（20以下）向上反弹且与价格形成底背离时买入。',
      sell: 'MFI从超买区域（80以上）向下回落且与价格形成顶背离时卖出。'
    },
    application: 'MFI适合结合RSI一起使用，RSI反映价格动量，MFI反映资金流向。两者共振信号更可靠。',
    warnings: [
      'MFI与RSI类似，在单边行情中可能持续超买超卖',
      '参数N的大小影响指标敏感度',
      '需要结合量价关系综合判断'
    ]
  },
  {
    id: 'tema',
    title: 'TEMA指标',
    desc: '三重指数移动平均线(TEMA)通过三重指数平滑减少移动平均的滞后性，更快速地反映价格趋势。',
    calculation: 'EMA1 = N日指数移动平均\nEMA2 = EMA1的N日指数移动平均\nEMA3 = EMA2的N日指数移动平均\nTEMA = 3 × EMA1 - 3 × EMA2 + EMA3',
    params: [
      { name: 'N', desc: '指数平滑周期，通常为12日或20日' }
    ],
    criteria: [
      { label: 'TEMA', value: '> 价格', desc: '多头趋势' },
      { label: 'TEMA', value: '< 价格', desc: '空头趋势' },
      { label: 'TEMA', value: '向上倾斜', desc: '上升趋势' },
      { label: 'TEMA', value: '向下倾斜', desc: '下降趋势' }
    ],
    signals: {
      buy: '价格从下向上穿越TEMA时买入；TEMA处于上升趋势中回踩TEMA时买入。',
      sell: '价格从上向下穿越TEMA时卖出。'
    },
    application: 'TEMA比普通EMA响应更快，适合短线交易者。在趋势行情中使用效果更好。',
    warnings: [
      'TEMA反应较快，信号可能更频繁',
      '在震荡行情中可能产生更多假信号',
      '建议与趋势确认指标配合'
    ]
  },
  {
    id: 'kama',
    title: 'KAMA指标',
    desc: '考夫曼自适应移动平均线(KAMA)能根据市场波动性自动调整平滑系数，在趋势明确时敏感度高，在震荡时平滑度高。',
    calculation: '效率比率(ER) = 价格变化方向 / 波动性\n波动性 = Σ |价格变化|\n平滑系数 = ER × (快速SC - 慢速SC) + 慢速SC\nKAMA = 前一日KAMA + 平滑系数 × (当日价格 - 前一日KAMA)\n其中快速SC=2/(2+10)，慢速SC=2/(2+30)',
    params: [
      { name: '快速SC周期', desc: '通常为10日' },
      { name: '慢速SC周期', desc: '通常为30日' }
    ],
    criteria: [
      { label: 'KAMA', value: '上升趋势中', desc: '市场波动大，KAMA更敏感' },
      { label: 'KAMA', value: '横盘震荡中', desc: '市场波动小，KAMA更平滑' },
      { label: '价格上穿', value: 'KAMA', desc: '买入信号' },
      { label: '价格下穿', value: 'KAMA', desc: '卖出信号' }
    ],
    signals: {
      buy: '价格从下向上穿越KAMA且KAMA处于上升趋势时买入。',
      sell: '价格从上向下穿越KAMA且KAMA处于下降趋势时卖出。'
    },
    application: 'KAMA特别适合在趋势和震荡交替的市场中使用，能自动适应市场状态。适合中短线投资者。',
    warnings: [
      'KAMA参数设置较为复杂',
      '在极端行情中自适应调整可能滞后',
      '建议与其他指标配合确认信号'
    ]
  }
])

const selected = computed(() => {
  if (!selectedId.value) return null
  return indicators.value.find(ind => ind.id === selectedId.value)
})

function selectIndicator(id) {
  selectedId.value = id
}

function getIcon(id) {
  const icons = {
    kdj: '📊', macd: '📈', boll: '🎯', rsi: '📉', cci: '⚡',
    wr: '🔄', atr: '📊', trix: '📈', dma: '📊', dmi: '🎯',
    adxr: '🎯', vr: '📊', ppo: '📈', cr: '💰', mfi: '💵',
    tema: '📈', kama: '📊'
  }
  return icons[id] || '📊'
}
</script>

<style scoped>
.indicators-detail {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.intro {
  margin-top: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  color: #d0d0d0;
  line-height: 1.6;
}

.indicator-buttons {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.indicator-btn {
  min-width: 100px;
  color: #ffffff !important;
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
}

.indicator-btn:hover {
  background-color: rgba(255, 255, 255, 0.2) !important;
}

.detail-card {
  margin-top: 24px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-icon {
  font-size: 28px;
}

.detail-title {
  font-size: 1.4rem;
  font-weight: bold;
  color: #fff;
}

.detail-section {
  margin-top: 24px;
}

.detail-section h3 {
  color: #00d4ff;
  font-size: 1.1rem;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.detail-section p {
  color: #e0e0e0;
  line-height: 1.8;
  white-space: pre-wrap;
}

.detail-section ul {
  list-style: none;
  padding: 0;
}

.detail-section ul li {
  color: #e0e0e0;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.detail-section ul li strong {
  color: #00d4ff;
  margin-right: 8px;
}

.criteria-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.criteria-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.criteria-label {
  color: #d0d0d0;
  min-width: 120px;
}

.criteria-value {
  color: #00d4ff;
  font-weight: bold;
  min-width: 150px;
}

.criteria-desc {
  color: #e0e0e0;
}

.signals {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.signal {
  padding: 16px;
  border-radius: 8px;
}

.signal.buy {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.signal.sell {
  background: rgba(255, 82, 82, 0.1);
  border: 1px solid rgba(255, 82, 82, 0.3);
}

.signal-icon {
  font-size: 24px;
}

.signal-title {
  display: block;
  font-weight: bold;
  margin: 8px 0;
}

.signal.buy .signal-title {
  color: #00ff88;
}

.signal.sell .signal-title {
  color: #ff5252;
}

.signal p {
  color: #e0e0e0;
  font-size: 0.9rem;
  line-height: 1.6;
  margin: 0;
}

.warnings {
  padding-left: 20px;
}

.warnings li {
  color: #ff9800;
  padding: 6px 0;
}

.all-indicators {
  margin-top: 24px;
}

.all-indicators h2 {
  color: #fff;
  margin-bottom: 20px;
}

.indicator-item {
  margin-bottom: 16px;
}

.indicator-item .el-card {
  cursor: pointer;
  transition: all 0.3s;
}

.indicator-item .el-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.indicator-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.indicator-icon {
  font-size: 20px;
}

.indicator-title {
  font-weight: bold;
  color: #fff;
}

.indicator-brief {
  color: #c0c0c0;
  font-size: 0.9rem;
  margin: 0;
}
</style>
